# ETH R3 H04 Stage C — Technical Correction

The first Stage C run is **TECHNICALLY INVALID** and must not be interpreted as a scientific 2024 failure.

## Root cause

`research/eth_r3_h04_stageC_2024_confirmation.py` initially called `eth_r1_h00_robust_train.candidate_events()`. That helper is intentionally hardcoded for the R1 training window:

- `TRAIN_START = 2022-01-01`
- `TRAIN_END = 2024-01-01`

Therefore every genuine 2024 event was filtered out before the Stage C scorer received it, producing N=0.

## Correction rule

The corrected Stage C rerun must:

- keep the already-frozen rule `DRIVE_DOWN__STR_B80_100`;
- keep the already-frozen coordinate `LB240 / H360`;
- keep every preregistered 2024 gate unchanged;
- perform no rule, LB, hold, threshold, or neighborhood reselection;
- use a local event extractor restricted to 2024 instead of the R1 train-window helper;
- keep 2025+ CLOSED.

Because the invalid run never produced usable 2024 candidate events or performance metrics, this correction is an operational rerun of the same one-shot hypothesis, not a scientific rescue or retuning exercise.
