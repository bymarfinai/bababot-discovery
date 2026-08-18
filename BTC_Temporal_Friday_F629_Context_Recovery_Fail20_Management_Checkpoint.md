# Friday F6.29 — Context-Conditioned Recovery-Fail +20m Management

**Diagnostic screen: FAIL**
**Same-sample economic diagnostic only; live BBC untouched; no automatic promotion.**

## Exact rule
F6.26 at +10m becomes WATCH. At +20m, exit at actual decision open only when the pre-entry last 5m candle was red AND there has been no completed EMA7 reclaim after +10m. Frozen layers keep priority if they exited earlier.

## Frozen parity
- five-layer PnL **+138.329**, WR **52.90%**, PF **1.827**, DD **24.259**

## Result
- active WATCH cohort **26**; raw/action signals **12 / 12**; D/V actions **7 / 5**
- parent winners/losses acted **3 / 9**
- F6.25 failure-to-develop caught **7/24 (29.2%)**
- loser savings **+19.197**; winner damage **-9.987**
- incremental **+9.210**; D/V **-1.443 / +10.654**
- PnL **+138.329 -> +147.540**; WR **52.90% -> 50.72%**
- PF **1.827 -> 1.961**; DD **24.259 -> 16.670**
- baseline positive→nonpositive **3**; jackknife min remaining incremental **+5.669**

## Guardrail
Because F6.27/F6.28 used both chronology slices during forensic selection, D/V here are robustness slices, not untouched validation. Do not tune timing or add body/wick/taker thresholds from this result.
