# BabaBot Checkpoint — Before Live Trade Hardcoding

**Date:** 2026-08-26  
**Purpose:** Freeze the exact research/engineering state before any hardcoding or production integration into live trading.

## 1. Current strategy state

### LONG — F85 continuation
Frozen operating lineage:
- B27DQ live-executable LONG portfolio.
- Four operating zones: `ALT_0330`, `RAW_0530`, `LONDON`, `RAW_2330`.
- Entry structure: frozen prior range -> High Touch #1 -> causal leave -> F85 touch -> same-bar close back above F85 -> entry next 5m open.
- Fixed range duration: 5h30m.
- Execution duration: 6h30m.
- F85 entry / F35 invalidation / E20 extension structure remains frozen.
- B27DQ corrected runner timing: floor learned on completed bar N is not scored until N+2.

Saved B27DQ pooled-major benchmark before causal correction:
- Accepted N: 227
- WR: 72.2%
- PF: 2.25
- Net: +$289.76
- Max loss streak: 3

### SHORT — F15 continuation
Frozen preferred bearish habitat:
- SHORT20 / reference clock 20:00 UTC.
- Reference 20:00 UTC -> execution 01:30–08:00 UTC.
- Entry structure: frozen prior range -> Low Touch #1 -> causal leave -> F15 touch -> same-bar close below F15 -> entry next 5m open.
- F15 entry / F65 invalidation / E20_DOWN target remain frozen.

B27DU historical robustness:
- N: 56
- WR: 76.8%
- PF: 2.81
- Net: +$77.73
- 5 bps/fill stress: WR 71.4%, PF 1.99, Net +$49.81
- Completed-window stability: 3/4 pass.

## 2. Portfolio state

Historical B27DT/B27DU control before LONG causal correction:
- LONG accepted: 227
- SHORT20 accepted: 56
- Combined accepted: 283
- Combined net: +$367.49
- Historical SHORT20 addition displaced 0 accepted LONG trades.

These numbers are now treated as the **pre-correction benchmark**, not the final live benchmark, because B27DW uncovered one future-dependent veto in the LONG research lineage.

## 3. B27DV — durable control plane

**Status: `B27DV_SHADOW_CONTROL_PLANE_SUPPORTED`**

Validated:
- 283/283 candidate-order trade-by-trade parity against the frozen historical portfolio.
- Candidate ID set parity 100%.
- Duplicate completed 5m bar is idempotent.
- Entry is not ACTIVE before acknowledgement.
- Pending entry survives restart.
- Active position survives restart.
- Pending protective floor is not treated as active before acknowledgement.
- Acknowledged floor survives restart.
- Out-of-order closed bars fail closed.
- Transactional authoritative BTC lock allows only one owner across instances.
- Startup reconciliation can adopt an exchange-open position.
- Startup reconciliation clears stale local state when exchange is flat.
- Side mismatch halts instead of guessing.
- Existing exchange-native STOP_MARKET capability confirmed in repository.

Important limitation:
- B27DV is a shadow/durable control-plane proof.
- Legacy `bbc_live.py` is intentionally unchanged.
- No production exchange entry writes were enabled.

## 4. B27DW — raw 5m signal parity

B27DW rebuilt signals from raw completed 5m data instead of injecting precomputed research candidates.

Coverage:
- 5m rows: 698,112
- Coverage: 100%
- Causal sessions replayed: 8,646

### SHORT20 result
**Exact parity PASS**
- Generated: 57
- Canonical: 57
- Missing: 0
- Extra: 0
- Geometry mismatch: 0

Conclusion: SHORT20 entry logic is reproducible from raw live-available 5m events without historical candidate injection.

### LONG result
B27DW generated:
- Raw causal LONG signals: 245
- Canonical historical LONG signals: 244
- Missing canonical signals: 0
- Extra causal signals: 1

Only mismatch:
- Partition: `reference_validation`
- Zone: `RAW_0530`
- Entry timestamp: `2025-09-11 12:30:00+00:00`

B27DE historical case classified the day as:
`AMBIGUOUS_H2_VS_OPPOSITE_BREAK`

But chronology shows:
- K1 signal bar: 12:10 UTC
- causal leave: 12:15 UTC
- causal F85 confirmation occurred before entry
- next-open entry was valid at 12:30 UTC
- the ambiguous H2/opposite-break event was only known later

Therefore the old historical lineage used a **future-dependent terminal veto** to cancel an entry that was already valid at 12:30.

This is a research/backtest look-ahead artifact. The live adapter must **not** reproduce it by peeking into future bars.

## 5. Current interpretation

The engineering direction is now locked:

**Do not change the live signal adapter to imitate the historical phantom.**

Correct path:
1. Correct LONG historical candidate generation to causal entry semantics.
2. Add the one valid causal LONG candidate.
3. Recompute its causal B27DQ management/exit.
4. Re-run global one-BTC chronological lock.
5. Re-score LONG-only and LONG+SHORT20 portfolio.
6. Re-run B27DW raw signal parity against the corrected canonical LONG stream.
7. Require 100% signal identity and geometry parity before production integration.

## 6. B27DX — next experiment

B27DX has been preregistered as the causal LONG correction/rescore step.

Purpose:
- remove the future-dependent terminal veto from historical LONG signal eligibility;
- preserve every frozen F85/F35/E20, zone, timing, filter, fee, sizing, and runner rule;
- rescore the resulting corrected LONG portfolio and LONG+SHORT20 combined portfolio;
- confirm whether the strategy remains robust after removing the phantom cancellation.

**B27DX result-bearing execution has NOT yet been completed at this checkpoint.**

## 7. Hard stop before live trade hardcoding

Do **not** hardcode or enable production live trading until all below are complete:
- [x] Durable shadow control-plane parity — B27DV PASS.
- [x] SHORT20 raw 5m signal parity — PASS 57/57.
- [x] LONG historical/live divergence isolated to one exact case.
- [x] Root cause identified as future-dependent historical veto.
- [ ] B27DX causal LONG rescore completed.
- [ ] Corrected LONG historical benchmark persisted.
- [ ] Corrected LONG+SHORT20 portfolio benchmark persisted.
- [ ] Raw 5m LONG signal parity = 100% against corrected canonical stream.
- [ ] Full raw 5m LONG+SHORT20 -> durable control plane parity = 100%.
- [ ] Forward shadow / exchange-read-only reconciliation checked on current data.
- [ ] Only after those gates: production live integration / exchange entry writes.

## 8. Safety / integrity rule

No strategy parameter tuning is authorized during the live-parity repair phase.

Allowed changes:
- causality corrections;
- event-order semantics;
- persistence / restart handling;
- acknowledgement handling;
- authoritative position lock;
- exchange-state reconciliation;
- deterministic signal adapter parity.

Not allowed until a separate experiment:
- changing F85/F15/F35/F65/E20/E20_DOWN;
- changing clock windows;
- adding EMA/ATR/volume/body/wick/regime filters;
- changing fees/sizing to rescue metrics;
- deleting historically losing trades;
- reproducing a historical look-ahead bug in live code.

## 9. Resume point

When work resumes, start from **B27DX causal LONG correction/rescore**. Do not jump directly to editing `bbc_live.py` or enabling Binance order writes.

After B27DX passes, rerun B27DW against the corrected canonical stream. If raw-signal parity is 100% and the combined portfolio remains acceptable, proceed to forward shadow integration as the final gate before hardcoded live trading.
