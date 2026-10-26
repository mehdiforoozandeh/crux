---
anchor: @ANCHOR@
repo: @REPO@
base: HEAD
editable: config/train_shakespeare_char.py
scorer: python3 @BENCH@/score.py
objective: val_loss min 1.36
mode: climb
budget_hours: 4
attempt_minutes: 20
---
Lower the best validation loss of nanoGPT on tinyshakespeare at a fixed compute budget (FLOPs, not steps). The score is the median of 2 seeds.
Only `config/train_shakespeare_char.py` counts, and only `name = literal` lines for the hyperparameter keys the README lists; `max_iters`, `eval_iters`, `dtype`, `compile` and the other frozen keys must keep their values, and any code fails.
The scorer trains its own frozen `model.py` and loop, so editing other files changes nothing. Two scores of one config differ by up to about 0.01.
