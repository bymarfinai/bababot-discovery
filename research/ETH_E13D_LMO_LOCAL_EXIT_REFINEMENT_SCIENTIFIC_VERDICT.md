# ETH E13D — LMO Local Exit Refinement Scientific Verdict

## Status
**ETH_E13D_NO_LMO_LOCAL_EXIT_PASSER**

Development/shadow only. OOS remained closed.

## Result-bearing run
- workflow run: **34578434897**
- job: **103196167398**
- head SHA: **9acd4877175782134a34b807a02450445e77d3dd**
- artifact: **10190594680**
- artifact SHA256: **f2fdda92b10e6b197a891823ed3e1f69d6b4f000a12a406774322aa3726335a2**
- raw ETHUSDT 5m coverage: **100.0000%**

## Formal result
**0 / 12 local exit candidates passed both unchanged pooled and cross-era execution gates.**

E13D froze the E13C-selected LMO source subset and tested only the preregistered local neighborhood:
- net floors 0.75%, 1.00%, 1.25%, 1.50% of $500 notional;
- max holds 24h, 36h, 48h;
- one active LONG maximum;
- completed-5m-close target semantics;
- Development only.

## Closest candidate remains the E13C coordinate
**LMO / $5.00 net floor / 36h max hold** remains the strongest balanced candidate.

Pooled:
- N **355**
- WR **75.49%**
- net **+$440.64**
- expectancy **+$1.2412/trade**
- PF **1.3626**
- max DD **$113.70**
- max loss streak **6**
- timeout rate **26.48%**
- median duration **570m**
- pooled gate: **PASS**

Cross-era:
- 2022: N120, WR **81.67%**, net +$75.23, exp +$0.63, PF **1.1328** -> FAIL only PF <1.15.
- 2023: N108, WR **65.74%**, net +$106.34, exp +$0.98, PF **1.3362** -> PASS.
- 2024: N127, WR **77.95%**, net +$259.06, exp +$2.04, PF **1.7792** -> PASS.

Thus this coordinate still misses formal promotion by the same narrow 2022 payoff-efficiency clause found in E13C.

## Why nearby coordinates do not rescue it
The preregistered local neighborhood does not reveal a cleaner robust coordinate:

- 0.75% / 36h: WR79.06%, net +$283.78, exp +$0.78, but PF1.245 and DD$130.14 fail pooled; 2022 PF1.034 fails era.
- 1.00% / 48h: WR78.92%, net +$446.32, exp +$1.27, PF1.354, but DD$194.59 fails pooled; 2022 PF1.084 fails era.
- 1.25% / 36h: WR72.05%, net +$488.08, exp +$1.41, PF1.366, but DD$129.63 and timeout31.41% fail pooled; 2022 PF1.110 and 2023 WR63.21% fail era.
- 1.50% / 36h: PF1.302 and net +$441.30, but WR67.66%, DD$125.76, loss streak9 and timeout38.02% fail pooled; 2022 PF1.079 and 2023 WR58.82% fail era.

Longer 48h holds generally raise WR but worsen drawdown and do not repair 2022 PF. Higher targets raise expectancy but increase timeout/path risk and reduce hit rate. Lower targets improve hit rate but weaken payoff efficiency.

## Scientific interpretation
The LMO sequential LONG concept is economically meaningful in Development, and the exact $5/36h coordinate is already pooled-robust under the frozen execution gate. However the local grid demonstrates that the remaining 2022 weakness is not cleanly removable by further target/hold tuning.

This means the unresolved problem is no longer a simple exit-coordinate calibration problem. Continuing to narrow target/hold/source coordinates after E13D would constitute Development overfitting.

## Preregistered stop-rule outcome
**STOP target/hold/source tuning in this lineage.**

Do not create another E13 experiment that merely changes:
- the L/M/O source subset,
- nearby profit floors,
- nearby maximum holds,
- or the frozen execution gates.

The next research phase must change the scientific question. Valid next directions include:
1. a preregistered **structural-risk / timeout-loss anatomy** study using the frozen LMO + $5/36h candidate, to determine what causally distinguishes the profitable 75% majority from the unresolved timeout losses before entry; or
2. a separately preregistered **SHORT character discovery** program using the pair-native discovery playbook.

Do not open OOS for LMO because it has not passed the Development era gate.

No live promotion.