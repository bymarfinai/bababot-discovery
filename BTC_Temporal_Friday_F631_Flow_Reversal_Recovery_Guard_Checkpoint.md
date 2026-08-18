# Friday F6.31 — Flow-Reversal Recovery Guard

**Diagnostic screen: FAIL**
**Same-sample diagnostic only; live BBC untouched; no automatic promotion.**

## Exact predeclared guard
When F6.29 would cut at +20m, protect/HOLD instead iff the +15→20m bar makes a fresh lower low versus +10→15m while taker imbalance improves. This is a natural price/flow divergence; no fitted magnitude threshold.

## Guard selectivity
- F6.29 false winners guarded **2/3 (66.7%)**
- F6.29 cut-losers guarded **4/9 (44.4%)**
- broader 13 winner / 9 true-dead guard rate **38.5% / 33.3%**

## Economics
- frozen PnL **+138.329** → F6.29 **+147.540** → guarded **+146.379**
- incremental vs frozen **+8.050**; vs F6.29 **-1.160**
- D/V incremental vs frozen **+4.161 / +3.889**
- WR **52.90% → 52.17%**; PF **1.827 → 1.923**; DD **24.259 → 22.675**
- baseline positive→nonpositive **1**; winner restored to positive **2**
- failure-to-develop still cut **4/24**

## Guardrail
This exact guard was motivated by F6.30 on the same sample. A PASS means the architecture is economically promising, not validated. Do not tune the divergence magnitude or timing on this sample.
