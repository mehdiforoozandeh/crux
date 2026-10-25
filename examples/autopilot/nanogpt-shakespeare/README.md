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

NUMBERS_PLACEHOLDER

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
