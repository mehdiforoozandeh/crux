#!/usr/bin/env python3
"""Frozen scorer: validation loss of nanoGPT's char-level Shakespeare model under a fixed
training-FLOP budget, on one CUDA GPU.

    python3 score.py CANDIDATE        # explicit path
    CRUX_CANDIDATE=CANDIDATE python3 score.py
    python3 score.py                  # under crux auto: CANDIDATE is the cwd (CRUX_WORKSPACE set)

CANDIDATE is a nanoGPT checkout. Only CANDIDATE/config/train_shakespeare_char.py is read from
it, and it is PARSED (Python `ast`), never executed. Every other file -- model.py, the training
loop below, the data and its split, the tokenizer, the evaluation, the budget -- is frozen and
comes from work/frozen/ or from this file.

Output (crux `run_scorer` contract): stdout is exactly one JSON object. On success, exit 0 and
the objective is the leaf `val_loss` ({"value": median over SEEDS training runs of the mean
cross-entropy, in nats per character, on the first half of the val split}); LOWER IS BETTER,
so the plan uses `address:: val_loss` and `direction:: min`. `holdout_loss` is the same
measurement on the second half of the val split; it is reported, never the objective.
On a wrong candidate, exit 1; stdout is {"passed": false, "reason": ...} with no `val_loss`
leaf, and the reason is also on stderr.

The parent (this file, stdlib only, any python3) never imports or executes the candidate. It
parses the config, checks every key, and runs SEEDS worker processes in work/venv, one after
another. Each worker builds the frozen model.py GPT from the checked numbers, trains it
for the step count the FLOP budget allows, and measures the loss itself.

Measurement-only flags (never used by crux; they exist to produce the README's numbers):
    --seeds N   run N seeds instead of SEEDS       --seed-base B   first seed (default 0)
    --parallel     all seeds at once                --nondeterministic   default CUDA kernels
    --train-cap S  raise the per-seed wall-time cap (to time slow GPUs)
"""
import ast, hashlib, json, math, os, signal, statistics, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
FROZEN = os.path.join(WORK, "frozen")                  # model.py + data/ (see setup.sh)
VENV_PY = os.path.join(WORK, "venv", "bin", "python")
CONFIG_REL = os.path.join("config", "train_shakespeare_char.py")
TRAIN_BIN = os.path.join(FROZEN, "data", "train.bin")
VAL_BIN = os.path.join(FROZEN, "data", "val.bin")
PINNED_COMMIT = "3adf61e154c3fe3fca428ad6bc3818b27a3b8291"
WORKLOAD = "nanogpt-shakespeare-char-fixed-flops"
VOCAB = 65

# The budget: the training FLOPs of the upstream config (config/train_shakespeare_char.py at
# the pinned commit) for its 5000 iterations, counted with nanoGPT's own per-token formula
# (model.py estimate_mfu: 6N + 12 L H Q T). A candidate gets floor(BUDGET / flops_per_iter)
# optimizer steps, so a bigger model or batch buys fewer steps, not a free win.
BASE = dict(n_layer=6, n_head=6, n_embd=384, block_size=256, batch_size=64,
            gradient_accumulation_steps=1, bias=False)
BASE_ITERS = 5000
SEEDS = 2                 # training runs per scorer call; the median is the score (README: noise)
TIMEOUT = 300             # seconds, whole scorer
TRAIN_CAP_S = 130         # seconds of training per seed: the wall-time backstop (README)
MAX_PARAMS = 40_000_000   # size backstop (~4x the baseline's 10.65M)
MAX_TOKENS_PER_MICRO = 65536   # batch_size * block_size: memory backstop (4x baseline)
MAX_BLOCK = 1024

# Keys the candidate may set, with their type and allowed range. Unset keys take nanoGPT
# train.py's defaults (DEFAULTS).
EDITABLE = {
    "learning_rate": (float, 1e-6, 1.0), "min_lr": (float, 0.0, 1.0),
    "warmup_iters": (int, 0, 10**7), "lr_decay_iters": (int, 1, 10**7),
    "decay_lr": (bool,), "weight_decay": (float, 0.0, 10.0),
    "beta1": (float, 0.0, 0.99999), "beta2": (float, 0.0, 0.99999),
    "grad_clip": (float, 0.0, 1e6), "batch_size": (int, 1, MAX_TOKENS_PER_MICRO),
    "block_size": (int, 1, MAX_BLOCK), "gradient_accumulation_steps": (int, 1, 1024),
    "n_layer": (int, 1, 128), "n_head": (int, 1, 128), "n_embd": (int, 1, 8192),
    "dropout": (float, 0.0, 0.95), "bias": (bool,),
}
DEFAULTS = dict(learning_rate=6e-4, min_lr=6e-5, warmup_iters=2000, lr_decay_iters=None,
                decay_lr=True, weight_decay=1e-1, beta1=0.9, beta2=0.95, grad_clip=1.0,
                batch_size=12, block_size=1024, gradient_accumulation_steps=1, n_layer=12,
                n_head=12, n_embd=768, dropout=0.0, bias=False)
# Bookkeeping keys of the upstream file that change nothing here: accepted and ignored.
INERT = {"out_dir", "eval_interval", "log_interval", "always_save_checkpoint", "wandb_log",
         "wandb_project", "wandb_run_name"}
# Keys the scorer owns. The file may keep them only at the pinned upstream value.
FROZEN_KEYS = {"dataset": "shakespeare_char", "eval_iters": 200, "max_iters": 5000,
               "eval_only": False, "init_from": "scratch", "device": "cuda",
               "dtype": "bfloat16", "compile": True, "backend": "nccl"}

# ----------------------------------------------------------------------------- worker
# Runs inside work/venv. Prints exactly one JSON line on its stdout; the frozen model.py's
# prints go to stderr.

def worker(spec_path):
    proto = os.fdopen(os.dup(1), "w", buffering=1)
    os.dup2(2, 1)
    with open(spec_path) as f:
        spec = json.load(f)
    hp, seed = spec["hp"], spec["seed"]
    import numpy as np, torch
    import torch.nn.functional as F
    if spec["deterministic"]:
        torch.use_deterministic_algorithms(True)
    sys.path.insert(0, FROZEN)
    import model as M
    if os.path.realpath(M.__file__) != os.path.realpath(os.path.join(FROZEN, "model.py")):
        raise SystemExit(f"imported model.py from {M.__file__}, not from work/frozen")
    dev = "cuda"
    torch.manual_seed(1337 + seed)
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    train = torch.from_numpy(np.fromfile(TRAIN_BIN, dtype=np.uint16).astype(np.int64)).to(dev)
    val = torch.from_numpy(np.fromfile(VAL_BIN, dtype=np.uint16).astype(np.int64)).to(dev)
    B, T, GA = hp["batch_size"], hp["block_size"], hp["gradient_accumulation_steps"]
    ar = torch.arange(T, device=dev)

    def get_batch():                      # train.py's sampler: uniform random windows
        ix = torch.randint(len(train) - T, (B,)).to(dev)
        idx = ix[:, None] + ar
        return train[idx], train[idx + 1]

    cfg = M.GPTConfig(block_size=T, vocab_size=VOCAB, n_layer=hp["n_layer"],
                      n_head=hp["n_head"], n_embd=hp["n_embd"], dropout=hp["dropout"],
                      bias=hp["bias"])
    raw = M.GPT(cfg).to(dev)
    opt = raw.configure_optimizers(hp["weight_decay"], hp["learning_rate"],
                                   (hp["beta1"], hp["beta2"]), "cuda")
    model = torch.compile(raw)
    ctx = torch.amp.autocast(device_type="cuda", dtype=torch.bfloat16)
    iters, warm, decay = spec["iters"], hp["warmup_iters"], hp["lr_decay_iters"]
    lr0, lrmin = hp["learning_rate"], hp["min_lr"]

    def get_lr(it):                       # train.py's schedule, verbatim
        if it < warm:
            return lr0 * (it + 1) / (warm + 1)
        if it > decay:
            return lrmin
        ratio = (it - warm) / (decay - warm)
        return lrmin + 0.5 * (1.0 + math.cos(math.pi * ratio)) * (lr0 - lrmin)

    X, Y = get_batch()
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    loss = None
    for it in range(iters):
        lr = get_lr(it) if hp["decay_lr"] else lr0
        for g in opt.param_groups:
            g["lr"] = lr
        for _ in range(GA):
            with ctx:
                _, loss = model(X, Y)
                loss = loss / GA
            X, Y = get_batch()
            loss.backward()
        if hp["grad_clip"] != 0.0:
            torch.nn.utils.clip_grad_norm_(raw.parameters(), hp["grad_clip"])
        opt.step()
        opt.zero_grad(set_to_none=True)
        if it % 100 == 0 and time.perf_counter() - t0 > spec["train_cap_s"]:
            proto.write(json.dumps({"error": f"training passed the {spec['train_cap_s']}s "
                                    f"wall-time cap at step {it} of {iters}"}) + "\n")
            return
    final_train = float(loss.item()) * GA
    torch.cuda.synchronize()
    train_s = time.perf_counter() - t0

    @torch.no_grad()
    def nll(data):
        """Mean next-character cross-entropy over EVERY character of `data` after the first,
        in fp32, with the uncompiled frozen model. Non-overlapping windows of the candidate's
        block_size; the last, shorter window is scored too, so every candidate is scored on
        the same characters."""
        raw.eval()
        n = (len(data) - 1) // T
        tot, cnt = 0.0, 0
        xs = data[:n * T].view(n, T); ys = data[1:n * T + 1].view(n, T)
        for i in range(0, n, 64):
            logits, _ = raw(xs[i:i + 64], ys[i:i + 64])
            tot += F.cross_entropy(logits.float().reshape(-1, VOCAB), ys[i:i + 64].reshape(-1),
                                   reduction="sum").item()
            cnt += ys[i:i + 64].numel()
        if n * T + 1 < len(data):
            x, y = data[n * T:-1][None], data[n * T + 1:][None]
            logits, _ = raw(x, y)
            tot += F.cross_entropy(logits.float().reshape(-1, VOCAB), y.reshape(-1),
                                   reduction="sum").item()
            cnt += y.numel()
        assert cnt == len(data) - 1
        return tot / cnt

    half = len(val) // 2
    out = {"seed": seed, "val_loss": nll(val[:half]), "holdout_loss": nll(val[half:]),
           "final_train_loss": final_train, "train_s": train_s, "iters": iters,
           "params": raw.get_num_params(), "gpu": torch.cuda.get_device_name(0),
           "max_mem_gb": torch.cuda.max_memory_allocated() / 2**30}
    proto.write(json.dumps(out) + "\n")

# ----------------------------------------------------------------------------- parent

PROCS = []


def fail(msg):
    for p in PROCS:
        if p.poll() is None:
            p.kill()
    sys.stderr.write(f"FAIL: {msg}\n")
    sys.stdout.write(json.dumps({"passed": False, "reason": msg[:2000],
                                 "workload": WORKLOAD}) + "\n")
    sys.exit(1)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _num(node):
    """A literal number, bool or string, allowing +, -, *, /, ** between numbers
    (so `min_lr = 1e-3 / 10` parses). Anything else is refused."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, str, bool)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = _num(node.operand)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return -v if isinstance(node.op, ast.USub) else v
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult,
                                                            ast.Div, ast.Pow)):
        a, b = _num(node.left), _num(node.right)
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (a, b)):
            if isinstance(node.op, ast.Pow) and abs(b) > 64:
                raise ValueError("exponent too large")
            op = type(node.op)
            if op is ast.Add: return a + b
            if op is ast.Sub: return a - b
            if op is ast.Mult: return a * b
            if op is ast.Div: return a / b
            return a ** b
    raise ValueError(f"line {getattr(node, 'lineno', '?')}: not a literal value")


def parse_config(path):
    """The candidate's config as {key: value}, refusing every statement that is not
    `NAME = literal`, every unknown key, and every frozen key at a non-upstream value."""
    try:
        with open(path) as f:
            tree = ast.parse(f.read(), filename=CONFIG_REL)
    except (OSError, SyntaxError, ValueError) as e:
        fail(f"{CONFIG_REL}: cannot read or parse: {e}")
    vals = {}
    for st in tree.body:
        if isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant) \
                and isinstance(st.value.value, str):
            continue                                          # a docstring
        if not (isinstance(st, ast.Assign) and len(st.targets) == 1
                and isinstance(st.targets[0], ast.Name)):
            fail(f"{CONFIG_REL} line {st.lineno}: only `name = literal` assignments are "
                 f"allowed (no imports, calls, conditionals or other code)")
        key = st.targets[0].id
        try:
            vals[key] = _num(st.value)
        except (ValueError, ZeroDivisionError, OverflowError) as e:
            fail(f"{CONFIG_REL}: {key}: {e}")
    hp = dict(DEFAULTS)
    for key, v in vals.items():
        if key in INERT:
            continue
        if key in FROZEN_KEYS:
            if v != FROZEN_KEYS[key] or type(v) is not type(FROZEN_KEYS[key]):
                fail(f"{CONFIG_REL}: {key} is fixed by the scorer at {FROZEN_KEYS[key]!r}; "
                     f"the file sets {v!r}. Only the hyperparameters in the README are "
                     f"editable; the step count comes from the FLOP budget")
            continue
        if key not in EDITABLE:
            fail(f"{CONFIG_REL}: unknown key '{key}'. Editable keys: "
                 + ", ".join(sorted(EDITABLE)))
        typ, *rng = EDITABLE[key]
        if typ is bool:
            ok = isinstance(v, bool)
        elif typ is int:
            ok = isinstance(v, int) and not isinstance(v, bool)
        else:
            ok = isinstance(v, (int, float)) and not isinstance(v, bool)
        if not ok:
            fail(f"{CONFIG_REL}: {key} = {v!r} is not of type {typ.__name__}")
        if rng and not (rng[0] <= v <= rng[1]) or (typ is float and not math.isfinite(v)):
            fail(f"{CONFIG_REL}: {key} = {v!r} is outside [{rng[0]}, {rng[1]}]")
        hp[key] = float(v) if typ is float else v
    return hp


def n_params(hp):
    """model.py's get_num_params() (position embeddings excluded, lm_head tied to wte)."""
    C, L, b = hp["n_embd"], hp["n_layer"], hp["bias"]
    per_layer = 2 * C * (1 + b) + 3 * C * C + 3 * C * b + C * C + C * b \
        + 4 * C * C + 4 * C * b + 4 * C * C + C * b
    return VOCAB * C + L * per_layer + C * (1 + b)


def flops_per_iter(hp):
    """model.py estimate_mfu's count: (6N + 12 L H Q T) per token, times tokens per step."""
    L, H, T = hp["n_layer"], hp["n_head"], hp["block_size"]
    per_token = 6 * n_params(hp) + 12 * L * H * (hp["n_embd"] // H) * T
    return per_token * T * hp["batch_size"] * hp["gradient_accumulation_steps"]


BUDGET = flops_per_iter(dict(DEFAULTS, **BASE)) * BASE_ITERS


def check_hp(hp):
    if hp["n_embd"] % hp["n_head"]:
        fail(f"n_embd {hp['n_embd']} is not divisible by n_head {hp['n_head']}")
    N = n_params(hp)
    if N > MAX_PARAMS:
        fail(f"model has {N:,} parameters; the cap is {MAX_PARAMS:,}")
    if hp["batch_size"] * hp["block_size"] > MAX_TOKENS_PER_MICRO:
        fail(f"batch_size*block_size = {hp['batch_size'] * hp['block_size']:,} tokens per "
             f"micro-batch; the cap is {MAX_TOKENS_PER_MICRO:,}")
    iters = BUDGET // flops_per_iter(hp)
    if iters < 1:
        fail("one step of this config costs more than the whole FLOP budget")
    if hp["lr_decay_iters"] is None:
        hp["lr_decay_iters"] = iters
    if hp["decay_lr"] and hp["lr_decay_iters"] <= hp["warmup_iters"]:
        fail("lr_decay_iters must be greater than warmup_iters (train.py asserts this)")
    return iters, N


def main():
    args = sys.argv[1:]
    if args[:1] == ["--worker"]:
        return worker(args[1])
    seeds_n, seed_base, sequential, determ, cap = SEEDS, None, True, True, TRAIN_CAP_S
    rest = []
    while args:
        a = args.pop(0)
        if a == "--seeds":
            seeds_n = int(args.pop(0))
        elif a == "--seed-base":
            seed_base = int(args.pop(0))
        elif a == "--parallel":
            sequential = False
        elif a == "--nondeterministic":
            determ = False
        elif a == "--train-cap":
            cap = int(args.pop(0))
        else:
            rest.append(a)
    workspace = os.environ.get("CRUX_WORKSPACE") or None
    # An argument, else CRUX_CANDIDATE, else -- only when crux auto started us, which it marks
    # by setting CRUX_WORKSPACE -- the cwd, which run_scorer sets to the worktree.
    cand = ((rest[0] if rest else "") or os.environ.get("CRUX_CANDIDATE")
            or (os.getcwd() if workspace else ""))
    if not cand:
        fail("no candidate: pass a path, set CRUX_CANDIDATE, or run under crux auto")
    cand = os.path.abspath(cand)
    if seed_base is None:     # crux's confirmation passes CRUX_SEED: new seeds, same commit
        seed_base = 1000 * int(os.environ.get("CRUX_SEED") or 0)
    seeds = [seed_base + k for k in range(seeds_n)]

    with open(os.path.join(HERE, "reference", "pins.json")) as f:
        pins = json.load(f)
    if not os.path.exists(VENV_PY):
        fail("work/venv missing: run setup.sh first")
    for name, path in (("input.txt", os.path.join(FROZEN, "data", "input.txt")),
                       ("train.bin", TRAIN_BIN), ("val.bin", VAL_BIN),
                       ("model.py", os.path.join(FROZEN, "model.py"))):
        if not os.path.isfile(path) or sha(path) != pins[name]:
            fail(f"frozen {name} missing or its sha256 differs from the pin: run setup.sh")

    signal.signal(signal.SIGALRM, lambda *_: fail(f"scorer timed out after {TIMEOUT}s"))
    signal.alarm(TIMEOUT + max(0, seeds_n * (cap + 20) - SEEDS * (TRAIN_CAP_S + 20)))
    started = time.perf_counter()
    cfg_path = os.path.join(cand, CONFIG_REL)
    if not os.path.isfile(cfg_path):
        fail(f"no {CONFIG_REL} under candidate {cand}")
    hp = parse_config(cfg_path)
    iters, N = check_hp(hp)

    if workspace:
        os.makedirs(workspace, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="nanogpt_score_", dir=workspace)
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("PYTHON", "TORCH", "CUDA_LAUNCH", "CUBLAS"))}
    env.update(PYTHONDONTWRITEBYTECODE="1", TORCHINDUCTOR_CACHE_DIR=os.path.join(tmp, "ind"))
    if determ:
        env["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    results = []

    def launch(seed):
        spec = os.path.join(tmp, f"spec_{seed}.json")
        with open(spec, "w") as f:
            json.dump({"hp": hp, "seed": seed, "iters": iters, "deterministic": determ,
                       "train_cap_s": cap}, f)
        p = subprocess.Popen([VENV_PY, os.path.abspath(__file__), "--worker", spec],
                             cwd=tmp, env=env, stdout=subprocess.PIPE, text=True)
        PROCS.append(p)
        return p

    def collect(p):
        out, _ = p.communicate()
        try:
            r = json.loads(out.strip().splitlines()[-1])
        except (ValueError, IndexError):
            fail(f"training worker died (exit {p.returncode}); see stderr above")
        if "error" in r:
            fail(r["error"])
        if not all(math.isfinite(r[k]) for k in ("val_loss", "holdout_loss")):
            fail(f"seed {r['seed']}: loss is not finite (training diverged)")
        results.append(r)

    try:
        if sequential:          # the default: parallel workers share one GPU and gain nothing
            for s in seeds:
                collect(launch(s))
        else:
            for p in [launch(s) for s in seeds]:
                collect(p)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    def leaf(key, unit="nats/char"):
        v = [r[key] for r in results]
        med = statistics.median(v)
        return {"value": round(med, 5), "direction": "min", "unit": unit,
                "statistic": f"median of {len(v)} seeds", "repeats": [round(x, 5) for x in v],
                "min": round(min(v), 5), "max": round(max(v), 5),
                "spread": round(max(v) - min(v), 5)}

    wall = time.perf_counter() - started
    doc = {
        "val_loss": leaf("val_loss"),
        "holdout_loss": leaf("holdout_loss"),
        "passed": True,
        "workload": {"id": WORKLOAD, "nanogpt_commit": PINNED_COMMIT,
                     "flop_budget": BUDGET, "flops_per_iter": flops_per_iter(hp),
                     "iters": iters, "params": N, "seeds": seeds,
                     "val_chars": "first half of val.bin (55,770)",
                     "holdout_chars": "second half of val.bin (55,770)",
                     "deterministic": determ, "parallel": not sequential},
        "hparams": hp,
        "runs": [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}
                 for r in results],
        "candidate": {"path": cand, "config_sha256": sha(cfg_path)},
        "scorer_wall_s": round(wall, 1),
    }
    sys.stderr.write(f"val_loss {doc['val_loss']['repeats']} median "
                     f"{doc['val_loss']['value']}  iters {iters}  wall {wall:.1f}s\n")
    sys.stdout.write(json.dumps(doc) + "\n")


if __name__ == "__main__":
    main()
