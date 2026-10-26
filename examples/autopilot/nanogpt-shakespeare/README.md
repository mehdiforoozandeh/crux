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
- **Metric `val_loss`:** the BEST mean next-character cross-entropy (nats per character)
  on the first half of `val.bin` (55,770 characters) over 20 evaluations during training,
  one after every 1/20 of the candidate's steps (every 250 steps for the baseline, nanoGPT's
  `eval_interval` for this config). This is what nanoGPT's `train.py` reports, since it keeps
  the best checkpoint. Each evaluation reads the whole half, in fp32, with no dropout and
  non-overlapping windows of the candidate's `block_size`, so it uses no random numbers and
  does not change the training run. The number of evaluations is the same for every
  candidate, so no config buys more chances at a low minimum. The score is the median over
  `SEEDS` training runs of each run's best.
- **`holdout_loss`:** the same measurement on the second half of `val.bin`, at the step where
  that run's `val_loss` was best. The scorer reports it and never uses it as the objective.
  That half is harder text: its loss is about 0.15-0.2 higher than `val_loss`.
- **Also reported:** `best_step`, `final_val_loss` (the loss at the last step) and, per run,
  the whole curve.
- **Direction:** lower is better. Plan: `address:: val_loss`, `direction:: min`.

## Numbers (Fir, H100 MIG 3g.40gb slice, deterministic kernels, 2 seeds per call)

All rows are one scorer call each (median of 2 seeds; the 2 seeds in brackets), run as crux
runs it: cwd = candidate, `CRUX_WORKSPACE` and `CRUX_SEED` set. Jobs 428648, 428649, 442266.

**Known improvement:** `dropout = 0.3` with `lr_decay_iters = 3500` (more regularization,
and the learning rate decays by the time the val loss bottoms out). Both calls (1.3692,
1.3613) are below every baseline call (1.3801-1.3879): 0.011-0.019 below the best baseline
call and 0.018-0.026 below the baseline median (1.3873). It is a modest gain, about 2-4x the
noise between two scores.

| candidate | `val_loss` | `holdout_loss` | best step | scorer wall |
|---|---|---|---|---|
| baseline, `CRUX_SEED` 0 | 1.3873 (1.3850, 1.3896) | 1.541 | 2000, 1750 | 236 s |
| baseline, `CRUX_SEED` 1 | 1.3801 (1.3847, 1.3755) | 1.556 | 1750, 2000 | 174 s |
| baseline, `CRUX_SEED` 2 | 1.3879 (1.3855, 1.3902) | 1.550 | 1750, 1750 | 175 s |
| `dropout = 0.3`, `CRUX_SEED` 0 | 1.3743 (1.3749, 1.3737) | 1.544 | 3000, 2750 | 186 s |
| `dropout = 0.3`, `CRUX_SEED` 1 | 1.3689 (1.3715, 1.3663) | 1.535 | 2500, 2750 | 173 s |
| `lr_decay_iters = 2500`, `CRUX_SEED` 0 | 1.3727 (1.3697, 1.3756) | 1.533 | 2000, 1750 | 230 s |
| `lr_decay_iters = 2500`, `CRUX_SEED` 1 | 1.3744 (1.3763, 1.3725) | 1.558 | 2500, 2000 | 173 s |
| **known improvement:** `dropout = 0.3, lr_decay_iters = 3500`, `CRUX_SEED` 0 | **1.3692** (1.3697, 1.3687) | 1.544 | 3000, 2750 | 174 s |
| **known improvement:** same, `CRUX_SEED` 1 | **1.3613** (1.3647, 1.3578) | 1.546 | 2750, 3500 | 192 s |
| `weight_decay = 1.0`, `CRUX_SEED` 0 | 1.3812 (1.3880, 1.3744) | 1.530 | 2750, 2500 | 173 s |
| `learning_rate = 1e-2, min_lr = 1e-3` (10x) | **1.4610** (1.3570, 1.5650) | 1.638 | 3500, 5000 | 241 s |
| `learning_rate = 1e-4, min_lr = 1e-5` (0.1x) | **1.4570** (1.4568, 1.4573) | 1.595 | 5000, 5000 | 173 s |
| model.py, train.py and val.bin of the candidate edited | 1.3873 (bit-identical to the baseline) | 1.541 | 2000, 1750 | 177 s |
| over-long config (1 layer, 16 wide, context 8, batch 1: 27e9 steps allowed) | fails: wall-time cap at step 75,800 | | | 138 s |

- **Compare to nanoGPT's 1.47.** nanoGPT's README reports a best val loss of 1.4697 over the
  whole val split. The scorer splits val in two: the mean of `val_loss` and `holdout_loss`
  for the baseline is (1.385 + 1.549) / 2 = 1.467, which matches.
- **The baseline peaks early.** Its best val is at step 1750-2000 of 5000; after that it
  overfits (final val 1.58-1.60, final train loss 0.83).
- **Sensitivity.** A learning rate 10x up (1.461) and 10x down (1.457) both score worse than
  every baseline call (1.380-1.388). The 10x-up config is unstable: one seed reached 1.357,
  better than the baseline, and the other 1.565.
- **Noise.** Six baseline seeds: 1.3755-1.3902, SD 0.0052. The median of 2 seeds then has an
  SD of about 0.004, and two such scores differ by noise alone by up to about 0.010 (2 SD).
  Treat a smaller gain as noise until crux's confirmation repeats it at new seeds. A third
  seed would cut that to about 0.008 and cost about 85 s more per call, which breaks the
  5-minute target; 2 seeds stay.
- **Cost of the evaluations.** 20 evaluations of both halves take 1.4-2.5 s per seed, under
  2% of training time.
- **Determinism.** With default CUDA kernels, the same seed on the same slice type gave
  losses 0.001-0.004 apart. The scorer forces `torch.use_deterministic_algorithms(True)`
  (with `CUBLAS_WORKSPACE_CONFIG=:4096:8`): the same seed then gives the same loss to the
  last digit, it costs about 4% of training time, and it is what lets the scorer prove that
  edits outside the config change nothing. It is deterministic per GPU type only: seed 0 of
  the baseline gives a final val loss of 1.5833 on a 3g slice, 1.5922 on a 1g slice and
  1.5937 on a full H100. The best-val runs reproduced the final-loss runs' final values to
  the last digit.
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
