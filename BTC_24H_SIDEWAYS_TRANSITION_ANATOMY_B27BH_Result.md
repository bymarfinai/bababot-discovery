# B27BH — BTC 24H SIDEWAYS Transition Anatomy Audit — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** Regime-state anatomy only; no future return, trade direction, entry, stop, target, fee, WR, PF, or PnL was used.

B27BG exact pooled flip-back reproduction: **459 / 2,202 = 20.8%**.

## One-interval flip-back anatomy — pooled major

| Pattern | N | Share of all 459 flip-backs |
|---|---:|---:|
| BULL->SIDEWAYS->BULL | 161 | 35.1% |
| BEAR->SIDEWAYS->BEAR | 145 | 31.6% |
| BULL->BEAR->BULL | 7 | 1.5% |
| BEAR->BULL->BEAR | 9 | 2.0% |
| SIDEWAYS->BULL->SIDEWAYS | 76 | 16.6% |
| SIDEWAYS->BEAR->SIDEWAYS | 61 | 13.3% |

**SIDEWAYS as the middle state accounts for 306/459 = 66.7% of all one-bar flip-backs.**

**Frozen primary readout: `SIDEWAYS_MIDDLE_DOMINATES_ONE_BAR_FLIPBACKS`.**

## One-interval flip-backs by major partition

| Partition | BULL-SIDEWAYS-BULL | BEAR-SIDEWAYS-BEAR | BULL-BEAR-BULL | BEAR-BULL-BEAR | SIDEWAYS-BULL-SIDEWAYS | SIDEWAYS-BEAR-SIDEWAYS | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| external | 43 | 25 | 1 | 1 | 18 | 12 | 100 |
| development | 71 | 84 | 1 | 6 | 30 | 33 | 225 |
| reference_validation | 47 | 36 | 5 | 2 | 28 | 16 | 134 |

## Bracketed SIDEWAYS episode bridge anatomy — pooled major

| SIDEWAYS episode class | N | Share | Median | P75 | P90 | 1 bar | 2 bars | 3+ bars |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BULL->SIDEWAYS->BULL | 281 | 27.5% | 1.0 / 4h | 2.0 | 5.0 | 161 | 63 | 57 |
| BEAR->SIDEWAYS->BEAR | 246 | 24.0% | 1.0 / 4h | 2.0 | 3.0 | 145 | 60 | 41 |
| BULL->SIDEWAYS->BEAR | 251 | 24.5% | 2.0 / 8h | 3.0 | 4.0 | 95 | 78 | 78 |
| BEAR->SIDEWAYS->BULL | 245 | 23.9% | 2.0 / 8h | 2.0 | 3.0 | 105 | 90 | 50 |

- Complete directionally bracketed SIDEWAYS episodes: **1023**.
- Resume same directional state: **527/1023 = 51.5%**.
- Exit to opposite directional state: **496/1023 = 48.5%**.
- From BULL: resume **281/532 = 52.8%**; opposite transition **251/532 = 47.2%**.
- From BEAR: resume **246/491 = 50.1%**; opposite transition **245/491 = 49.9%**.

- SIDEWAYS episodes not directionally bracketed / boundary-gap-censored: **1** (reported separately; excluded from bridge denominator).

## Interpretation boundary

This result only describes the existing detector state machine. It does not redesign SIDEWAYS. Any persistence/hysteresis/confirmation change requires a new preregistered experiment.

Research only. Live BBC unchanged.
