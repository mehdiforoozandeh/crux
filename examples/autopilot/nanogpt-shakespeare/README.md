# nanoGPT Shakespeare: an autopilot benchmark that lowers a loss

**Task.** Lower the validation loss of nanoGPT's character-level Shakespeare model by changing
only its hyperparameters, under a fixed training compute budget, on one GPU.

This is the climb-the-loss problem in the style of Karpathy's autoresearch. The model, data
and training loop come from [karpathy/nanoGPT](https://github.com/karpathy/nanoGPT) (MIT) at
commit `3adf61e` (master, 2025-11-12). The baseline is the repository's own
`config/train_shakespeare_char.py`, unchanged: 6 layers, 6 heads, 384 wide (10.65M
parameters), context 256, batch 64, dropout 0.2, learning rate 1e-3, 5000 steps.

## Metric

- **Data:** tinyshakespeare (`input.txt`, the file nanoGPT's `prepare.py` downloads), pinned
  by sha256 and encoded exactly as `prepare.py` does: 65 characters, the first 90% train,
  the last 10% val. `reference/pins.json` holds the sha256 of the text, of `train.bin`,
  `val.bin` and of the frozen `model.py`; the scorer refuses to run when one differs.
- **Metric `val_loss`:** the mean next-character cross-entropy (nats per character) of the
  FINAL model on the first half of `val.bin` (55,770 characters). The scorer computes it
  itself, in fp32, over every character, with non-overlapping windows of the candidate's
  `block_size`. There is no early stopping and no checkpoint selection. The score is the
  median over `SEEDS` training runs.
- **`holdout_loss`:** the same measurement on the second half of `val.bin`. The scorer
  reports it and never uses it as the objective. That half is harder text: its loss is about
  0.2 higher than `val_loss` for every config measured.
- **Direction:** lower is better. Plan: `address:: val_loss`, `direction:: min`.

## Numbers (Fir, H100 MIG 3g.40gb slice, deterministic kernels, 2 seeds per call)

| candidate | `val_loss` (median of 2 seeds) | `holdout_loss` | scorer wall |
|---|---|---|---|
| baseline, `CRUX_SEED` 0 / 1 / 2 | 1.5848 / 1.5920 / 1.5946 | 1.789 / 1.806 / 1.789 | 233 / 170 / 180 s |
| `dropout = 0.3`, `CRUX_SEED` 0 / 1 | **1.4108 / 1.4089** | 1.602 / 1.595 | 170 / 177 s |
| model.py, train.py and val.bin of the candidate edited | 1.58481 (bit-identical to the baseline) | 1.78929 | 171 s |
| `learning_rate = 1e-2, min_lr = 1e-3`, `CRUX_SEED` 0 | 1.4829 (seeds: 1.4009, 1.5650) | 1.665 | 172 s |
| `dropout = 0.0` (1g slice, seed 0; baseline 1.5922 there) | **4.0355** (train loss 0.085) | 4.470 | |
| `learning_rate = 1e-5, min_lr = 1e-6` (1g slice, seed 0) | **2.1688** (train loss 2.21) | 2.188 | |
| over-long config (1 layer, 16 wide, context 8, batch 1: 27e9 steps allowed) | fails: wall-time cap at step 78,700 | | 139 s |

- **The baseline overfits.** It reaches a train loss of about 0.83 and a final val loss of
  about 1.59; nanoGPT's README reports 1.47 because `train.py` keeps the best checkpoint.
  The scorer measures the final model, so regularization is the first lever a search finds
  (`dropout = 0.3` gains 0.18).
- **Sensitivity runs both ways.** Less regularization is far worse (`dropout = 0.0`: 4.04,
  the model memorizes the train text) and so is too low a learning rate (1e-5: 2.17, the
  model underfits). But a learning rate 10x up or 10x down is NOT worse here: both train
  less well and so overfit less. 10x up scored 1.40, 1.56 (3g slice) and 1.41, 1.38, 1.48
  (1g slice), and 1.68 on one more 1g seed; 10x down scored 1.457 (1g slice). A 10x learning
  rate is high-variance, and the scorer's 2 seeds do not always show that.
- **Noise.** Six baseline seeds on the 3g slice, deterministic: 1.5833-1.6011, SD 0.0068.
  Six seeds on a 1g slice with default (non-deterministic) kernels: SD 0.0084. With 2 seeds
  per call, two scores differ by noise alone by up to about 0.015 (2 SD); treat a smaller
  gain as noise until crux's confirmation repeats it at new seeds.
- **Determinism.** With default CUDA kernels, the same seed on the same slice type gave
  losses 0.001-0.004 apart. The scorer forces `torch.use_deterministic_algorithms(True)`
  (with `CUBLAS_WORKSPACE_CONFIG=:4096:8`): the same seed then gives the same loss to the
  last digit, it costs about 4% of training time, and it is what lets the scorer prove that
  edits outside the config change nothing. It is deterministic per GPU type only: seed 0 of
  the baseline gives 1.5833 on a 3g slice, 1.5922 on a 1g slice and 1.5937 on a full H100.
  **Score the baseline and every candidate of one search on the same GPU type.**
- **Time per seed** (5000 steps of the baseline): 1g.10gb slice 219-238 s; 3g.40gb slice
  72-99 s; full H100 58 s. Two seeds on one GPU in parallel are no faster than in sequence
  (three in parallel on a 1g slice took 703 s each), so the scorer runs seeds one after
  another. With 2 seeds, one scorer call takes 170-233 s on the 3g slice. The per-seed
  wall-time cap (`TRAIN_CAP_S` = 130 s) leaves a candidate about 1.5x the baseline's time
  on that slice.

## The compute budget

A candidate gets a fixed number of training FLOPs, not a fixed step count and not a fixed
wall time. The budget is what the baseline spends in its 5000 steps, counted with
nanoGPT's own formula (`model.py` `estimate_mfu`: 6N + 12·L·H·Q·T FLOPs per token):
5.81e15 FLOPs. The scorer gives a candidate `floor(budget / flops_per_step)` steps. A
model twice as big, or a batch twice as large, gets half the steps.

- A fixed step count would let a bigger model or batch win for free.
- A fixed wall time makes the score depend on the GPU type, on the MIG slice and on what
  else runs on the node, and it makes the step count, and with it the loss, vary run to run.
- The FLOP budget is the same on every machine, and with deterministic kernels a seed gives
  the same loss every time.

Backstops, because FLOPs do not bound wall time or memory: at most 40M parameters, at most
65,536 tokens per micro-batch (`batch_size * block_size`), `block_size` at most 1024, and a
per-seed training wall-time cap (`TRAIN_CAP_S`). A config of tiny kernels that the budget
allows millions of steps trips the wall-time cap and fails.

`lr_decay_iters` defaults to the step count the budget gives; a candidate that changes the
model size and keeps `lr_decay_iters = 5000` decays on the old schedule. The scorer prints
the step count it used under `workload.iters`.

## What the agent may edit, and what is frozen

- **Editable:** `config/train_shakespeare_char.py` in the candidate checkout, and only these
  keys: `learning_rate, min_lr, warmup_iters, lr_decay_iters, decay_lr, weight_decay, beta1,
  beta2, grad_clip, batch_size, block_size, gradient_accumulation_steps, n_layer, n_head,
  n_embd, dropout, bias`. A key the file does not set takes `train.py`'s default.
- **Ignored:** `out_dir, eval_interval, log_interval, always_save_checkpoint, wandb_*`.
- **Frozen, and refused if changed:** `max_iters` (5000), `eval_iters` (200), `dataset`,
  `device`, `dtype`, `compile`, `init_from`, `eval_only`, `backend`. The file may keep them
  at the upstream value. Any other key fails.
- The scorer **parses** the file with Python's `ast` and never executes it. Each statement
  must be `name = literal` (numbers, strings, booleans, and + - * / ** between numbers). An
  import, a call or any other code fails.
- Every other file of the candidate is ignored: `model.py`, `train.py`, `data/`. The scorer
  trains the frozen `work/frozen/model.py` with its own loop (a copy of `train.py`'s
  sampler, cosine schedule with warmup, AdamW from `configure_optimizers`, gradient
  clipping, bf16 autocast, `torch.compile`) on the frozen `work/frozen/data/`.

## The scorer contract

```
python3 score.py CANDIDATE                  # or: CRUX_CANDIDATE=CANDIDATE python3 score.py
```

- `CANDIDATE` is a nanoGPT checkout. **Candidate:** a path argument, else `CRUX_CANDIDATE`,
  else the working directory, but only when `CRUX_WORKSPACE` is set (crux's `run_scorer`
  sets the working directory to the attempt's worktree). The plan needs no adapter:
  `scorer: python3 <abs path>/score.py`. Temp files go inside `CRUX_WORKSPACE` when set.
- **Seeds:** `CRUX_SEED=s` (set by crux's confirmation) moves the seeds to
  `1000*s, 1000*s+1, ...`, so a confirmation trains on seeds the attempt never saw.
- **Pass:** exit 0; stdout is exactly one JSON object with the leaves `val_loss` and
  `holdout_loss` (`value`, `direction`, `unit`, `repeats`, `min`, `max`, `spread`), plus
  `passed`, `workload` (budget, steps, parameters, seeds), `hparams`, `runs` (per seed:
  losses, train seconds, GPU, peak memory), `candidate` and `scorer_wall_s`.
- **Fail:** exit 1; stdout is `{"passed": false, "reason": "..."}` with no `val_loss` leaf,
  and the reason is also on stderr. A candidate fails when its config breaks a rule above,
  breaks a backstop, diverges (a loss that is not finite) or crashes the worker (for
  example, out of GPU memory). crux treats `scorer-exit` as a machine fault and retries it
  `retries:` times before it records the attempt as failed.
- **Where it runs:** on the GPU node it is started on. It submits no job. The crux driver
  runs inside a Fir SLURM job and calls it there.

## How to run (Fir)

```
module load StdEnv/2023 python/3.12.4
./setup.sh                                   # clone at 3adf61e, data, work/venv
python3 score.py work/cand-baseline          # inside a GPU job
```

`setup.sh` makes everything under `work/`, which git ignores: the clone, `work/frozen/`
(`model.py` and the encoded data), the baseline candidate and a venv built from the Alliance
wheelhouse with the versions in `requirements.lock` (resolved set in `work/versions.txt`).
It installs nothing outside `work/`.

The driver's job must ask for the GPU type the baseline was scored on, here
`--gres=gpu:nvidia_h100_80gb_hbm3_3g.40gb:1`. A 1g.10gb slice is too slow for 2 seeds in
5 minutes (one seed takes 219-238 s); a full H100 (58 s per seed) would allow 3-4 seeds.
One Fir node (`fc10713`) failed every job with `CUDA-capable device(s) is/are busy or
unavailable`; the scorer reports that as a failed worker, which crux retries as a machine
fault.

## Cheat candidates (all on the 3g slice unless noted)

- `max_iters = 20000`, `eval_iters = 1`, `dataset = 'openwebtext'`, `device = 'cpu'`: refused,
  "fixed by the scorer". `data_dir = '/tmp/mydata'`: refused, unknown key. `import os` with
  `learning_rate = float(os.environ[...])`: refused, not `name = literal`.
- `model.py` patched to return a zero loss, `train.py` replaced and `data/.../val.bin`
  zeroed: ignored; the score is bit-identical to the baseline (1.58481, 1.78929).
- 24 layers x 768 wide (170M parameters): refused, over the size cap. `batch_size = 512`:
  refused, over the token cap. The over-long tiny config: fails at the wall-time cap.
