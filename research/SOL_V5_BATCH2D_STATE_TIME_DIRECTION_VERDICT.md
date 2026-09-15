# SOL V5 Batch 2D — State-Time Direction Selector Verdict

Authoritative frozen run: `34915832542`
Artifact: `sol-v5-batch2d-state-time-direction` (ID `10376511027`)
Artifact SHA256: `e2a67c174f8d5922d528b5508aba7aef4d3f3eaa2c8031aba2d03a396a7b18b6`
Branch: `sol-v5-batch2d-state-time-direction`

## Result

- Data coverage: **99.769767%**
- OOS HIGH_STATE test episodes 2022–2024: **2,763**
- Selected LONG entries at state onset: **232**
- Selection rate: **8.40%**
- OOS ROC AUC: **0.5553**
- 2025+ reference_validation remained CLOSED.

## Direction separation

- All HIGH_STATE UP_FIRST rate: **30.98%**
- Selected UP_FIRST rate: **41.38%**
- UP_FIRST lift: **1.336x**

The state-time representation contains weak directional information, but not enough to satisfy the frozen directional precision gates.

## Fixed +60m diagnostic from causal state-time entry

- Selected WR: **46.12%**
- Selected expectancy: **-0.0754%**
- Selected PF: **0.886**
- Selected net PnL: **-$87.43** at $500 notional/trade
- Selected max DD: **$185.68**
- Selected max loss streak: **7**

Baseline all HIGH_STATE:
- expectancy: **-0.1285%**
- PF: **0.795**

Thus the selector improves the negative HIGH_STATE baseline, but does not cross into positive economics.

## Year stability

### 2022
- episodes 857
- selected 115
- baseline UP_FIRST 30.81%
- selected UP_FIRST 39.13%
- lift 1.270x
- AUC 0.532
- WR 40.87%
- expectancy **-0.2790%**
- PF **0.644**
- PnL **-$160.41**

### 2023
- episodes 750
- selected 108
- baseline UP_FIRST 35.87%
- selected UP_FIRST 43.52%
- lift 1.213x
- AUC 0.558
- WR 52.78%
- expectancy **+0.1733%**
- PF **1.330**
- PnL **+$93.58**

### 2024
- episodes 1156
- selected 9
- baseline UP_FIRST 27.94%
- selected UP_FIRST 44.44%
- lift 1.591x
- AUC 0.548
- WR 33.33%
- expectancy **-0.4578%**
- PF **0.383**
- PnL **-$20.60**

## Leading state-time features

- `sigma60_pct` — 0.0331
- `impulse_threshold_pct` — 0.0312
- `volume_23` — 0.0217
- `range_09` — 0.0137
- `close_loc_21` — 0.0126
- `compression_rv_30_120` — 0.0122
- `compression_range_30_120` — 0.0115
- `body_23` — 0.0113
- `close_loc_02` — 0.0111
- `close_loc_22` — 0.0107

## Gate audit

- PASS — selected N >= 200
- PASS — OOS AUC >= 0.55
- FAIL — selected UP_FIRST >= 50%
- FAIL — UP_FIRST lift >= 1.35x
- FAIL — selected fixed +60m expectancy > 0
- FAIL — selected PF >= 1.10
- FAIL — positive selected PnL in >=2/3 test years

# VERDICT: STATE_TIME_DIRECTION_NOT_READY

## Architectural conclusion

Across Batch 1, Batch 2, Batch 2B, Batch 2C, and Batch 2D the evidence is now coherent:

1. V4 HIGH_STATE is useful as a **two-sided expansion habitat detector**.
2. Direction becomes substantially more predictable after several post-state candles (Batch 2 AUC 0.7327; activated UP_FIRST 64.11%), but waiting for that confirmation sacrifices the entry edge.
3. Remaining-magnitude prediction using the current checkpoint representation did not rank future returns (Batch 2B Spearman ~0).
4. Entering every HIGH_STATE and trying to repair the trade after +5m is negative (Batch 2C).
5. At state onset, the current V4 representation carries only weak LONG directional information (Batch 2D AUC 0.5553) and is not economically sufficient.

Therefore the next step must **change directional representation**, not sweep thresholds/models/exits on the same representation. The next research unit should construct a direction-specific causal sequence/path representation at state onset—e.g. normalized candle path, close-location progression, signed body/wick sequence, relative volume progression, local HH/HL and sweep/reclaim state—while keeping V4 as the expansion-habitat gate.

Do not begin adaptive TP/SL yet. TP/SL work should start only after a causal entry layer has positive economics before exit optimization.

2025+ remains CLOSED.
