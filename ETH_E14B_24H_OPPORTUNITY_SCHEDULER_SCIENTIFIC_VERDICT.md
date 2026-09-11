# ETH E14B — 24H Opportunity-Cost Scheduler Scientific Verdict

**Status:** Development-only. OOS CLOSED. No live authorization.

## Frozen question
Can the full frozen 24h ETH LONG character map be used as a causal TAKE-vs-WAIT scheduler, preserving each source hour's native E12 rule/lookback/hold, one active position max, and $500 notional?

## Result-bearing run
- Branch: `eth-e14b-24h-opportunity-scheduler`
- Workflow run: `34582801036`
- Job: `103210046921`
- Trigger/head commit: `afaf7603eaf256568d10c2ab2c26429170fe601a`
- Artifact: `10192332498`
- Artifact SHA256: `fa9726ca7e1bbf31ff2708c025332ea46fef98a655adda9c16c0f849ea8c102e`
- Raw ETHUSDT 5m coverage: 100.0000%

## Reference reproduction
`FIRST_VALID_ALL24` exactly reproduced the E13C all-24 sequential baseline:
- N 1149
- WR 51.00%
- net +$381.19
- expectancy +$0.33/trade
- PF 1.075
- DD $390.17
- max loss streak 11

This confirms the E14B replay preserves E13C native-hold one-position accounting before scheduler filtering.

## Preregistered policy grid

| Policy | N | WR | Net | Exp | PF | DD | LS | Min-year exp | Years WR>=55 | Robust |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| FIRST_VALID_ALL24 | 1149 | 51.00% | +$381.19 | +$0.33 | 1.075 | $390.17 | 11 | -$0.13 | 0/3 | NO |
| OC_M000 | 826 | 54.12% | +$899.69 | +$1.09 | 1.286 | $233.78 | 10 | +$0.66 | 2/3 | NO |
| OC_M025 | 686 | 54.08% | +$905.89 | +$1.32 | 1.355 | $173.40 | 7 | +$0.97 | 2/3 | NO |
| OC_M050 | 588 | 53.91% | +$885.25 | +$1.51 | 1.397 | $169.89 | 6 | +$1.05 | 1/3 | NO |
| OC_M075 | 412 | 53.64% | +$706.39 | +$1.71 | 1.416 | $156.17 | 6 | +$1.47 | 1/3 | NO |
| **OC_M100** | **276** | **57.25%** | **+$608.89** | **+$2.21** | **1.622** | **$101.14** | **5** | **+$2.09** | **3/3** | **YES** |
| OC_M150 | 68 | 57.35% | +$317.36 | +$4.67 | 2.753 | $37.99 | 4 | +$3.83 | 2/3 | NO — sample/era gate |
| OC_M200 | 0 | — | 0 | — | — | — | 0 | — | 0/3 | NO |
| OC_M300 | 0 | — | 0 | — | — | — | 0 | — | 0/3 | NO |

## Development-selected scheduler

### OC_M100
TAKE only when the Bellman TAKE-vs-WAIT advantage is at least +$1.00.

Pooled:
- N **276**
- WR **57.25%**
- net **+$608.89**
- expectancy **+$2.21/trade**
- PF **1.622**
- DD **$101.14**
- max loss streak **5**
- average native hold **13.59h**

Cross-era:
- 2022: N79, WR55.70%, net +$180.17, exp +$2.28, PF1.433
- 2023: N112, WR56.25%, net +$234.59, exp +$2.09, PF1.798
- 2024: N85, WR60.00%, net +$194.13, exp +$2.28, PF1.719

All three years have WR >=55%, positive net, positive expectancy, and PF >=1.05.

## What the scheduler actually executed

The selected M100 scheduler did **not** spread executions evenly across 24 hours. It used the full 24h map to decide when *not* to spend the capital slot and concentrated actual execution in three source hours:

- **00 WIB / E12L / H720:** 166 executed, WR55.42%, net +$252.83, exp +$1.52, PF1.384
- **05 WIB / E12Q / H960:** 45 executed, WR62.22%, net +$71.23, exp +$1.58, PF1.446
- **17 WIB / E12E / H960:** 65 executed, WR58.46%, net +$284.83, exp +$4.38, PF2.770

All other source hours were either rejected by WAIT value when flat or blocked while a selected native-hold position was active.

This is an important distinction: **the 24h map is being used as a reservation/opportunity-cost map, not as a mandate to trade 24 hours.**

## Comparison with E13C all-24 first-valid

OC_M100 is a strict pooled Pareto improvement versus the all-24 first-valid baseline:
- WR: 51.00% -> 57.25%
- net: +$381.19 -> +$608.89
- expectancy: +$0.33 -> +$2.21
- PF: 1.075 -> 1.622
- DD: $390.17 -> $101.14
- max loss streak: 11 -> 5

Therefore the central E14B hypothesis is supported in Development: **opportunity-cost scheduling is materially better than consuming the slot at the first available 24h signal.**

## Comparison with E13D K+L+O

Frozen K+L+O benchmark:
- N381
- WR55.64%
- net +$647.28
- exp +$1.70
- PF1.469
- DD $96.03
- LS6

OC_M100:
- higher WR: 57.25%
- lower net: +$608.89
- higher expectancy: +$2.21
- higher PF: 1.622
- slightly higher DD: $101.14
- lower loss streak: 5

Therefore OC_M100 is **not** a strict Pareto improvement versus K+L+O because net is lower and DD is slightly higher. It is a different trade-off: fewer trades, stronger per-trade economics, stronger WR/PF/era consistency, slightly less total net, and slightly more DD.

## Interpretation of former FAIL hours

E12Q at 05 WIB and E12E at 17 WIB remain formal E12 FAIL characters. E14B does not retroactively promote them. Their new role is narrower:
- they can be useful **conditional portfolio opportunities** when the scheduler's continuation-value logic says consuming the capital slot is worthwhile;
- this is different from saying they satisfy the original broad standalone E12 formal character gate.

The 17 WIB E12E clue is especially important: its original standalone sample was small, but under M100 it contributes 65 executed trades with +$284.83 net, +$4.38 expectancy, PF2.770, while the full scheduler remains cross-era robust.

## Scientific caveat

The Bellman prior uses all Development years to estimate signal probability and conservative hourly expectancy and assumes independent future signal arrivals. The margin family was selected on the same Development partition. Therefore OC_M100 is a **Development-selected architecture**, not confirmation and not OOS evidence.

## Frozen conclusion

**ETH_E14B_ROBUST_SCHEDULER_FOUND**

The 24h data can be exploited more effectively as a temporal opportunity-cost map than as 24 independent trades or a forced daily campaign. E14B provides the first robust Development evidence for this interpretation.

No TP/SL, DCA, SHORT, or OOS changes are authorized by this result.
