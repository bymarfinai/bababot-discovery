# Friday F6.26 — FAILED_LAUNCH_10 Management

**Screen: FAIL**
**Research only; live BBC untouched. No threshold/timing sweep.**

## Exact predeclared rule
At +10m, exit at actual decision open iff still alive, never reached +0.5R, second 5m high < first 5m high, second close < entry, and second close < EMA7. Frozen layers win any same-time tie.

## Frozen parity
- latest five-layer: **+138.329**, 73W/65L, WR **52.90%**, PF **1.827**, DD **24.259**

## Result
- raw/active signals **39 / 26**; D/V actions **15 / 11**
- F6.25 failure-to-develop caught **9/24 (37.5%)**
- parent winners/losses acted **13 / 13**
- loss→positive **0**; baseline positive→nonpositive **14**
- incremental **-39.878**; D/V **-31.698 / -8.180**
- PnL **+138.329 -> +98.451**; WR **52.90% -> 42.75%**
- PF **1.827 -> 1.606**; DD **24.259 -> 19.606**
- jackknife min remaining incremental **-43.307**

## Guardrail
This is a same-sample action test motivated by F6.25. Do not retune +10m, lower-high definition, +0.5R milestone, EMA7, or add taker/body filters based on this run.
