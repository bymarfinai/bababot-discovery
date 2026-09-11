# BNB Economic-First B28M — Scientific Verdict

## Status
**BNB_ECONOMIC_FIRST_B28M_LONG_CHARACTER_FOUND**

Research/shadow only. No live promotion or profit guarantee.

## Result-bearing run
- workflow run ID: **34581511078**
- job ID: **103205897255**
- result-bearing head SHA: **a17932acab4b3b2742f306d62c9533ce6d739aa5**
- artifact ID: **10191816631**
- targeted workflow conclusion: **success**
- raw BNBUSDT 5m coverage: **100.0000%**

## Frozen discovery scope
- BNBUSDT
- LONG only
- habitat: **12:00–13:00 WIB**
- anchors: **12:00 / 12:15 / 12:30 / 12:45 WIB** = **05:00 / 05:15 / 05:30 / 05:45 UTC**
- Development only
- exact same B28A–B28L 90-rule causal grammar, lookbacks, holds, fees, ranking and gates
- **3,240 candidates**
- no TP / no SL
- no weekday filter
- OOS unopened
- prior-hour winners and B27 structural coordinates excluded from ranking

## Formal result
**4 / 3,240 candidates passed the full preregistered anchor-stability + pooled-economics/risk + all-era gate.**

## Development-selected LONG character
### `RV_MID__RANGE_HIGH / LB30 / hold360m`
- N **201**
- WR **63.68%**
- net **+$412.35**
- expectancy **+$2.05/trade**
- PF **2.108**
- max DD **$41.59**
- max loss streak **5**
- supportive anchors **4/4**

### Cross-era Development
- 2022: N **55**, WR **63.64%**, expectancy **+$2.07**, PF **2.040**
- 2023: N **67**, WR **64.18%**, expectancy **+$1.70**, PF **2.149**
- 2024: N **79**, WR **63.29%**, expectancy **+$2.34**, PF **2.128**

### Quarter-hour anchor atlas
- 12:00 WIB: N **51**, WR **60.78%**, net **+$172.77**, exp **+$3.39**, PF **2.932**, DD **$39.81**, supportive **YES**
- 12:15 WIB: N **56**, WR **62.50%**, net **+$100.52**, exp **+$1.80**, PF **2.092**, DD **$22.36**, supportive **YES**
- 12:30 WIB: N **48**, WR **62.50%**, net **+$52.44**, exp **+$1.09**, PF **1.548**, DD **$27.98**, supportive **YES**
- 12:45 WIB: N **46**, WR **69.57%**, net **+$86.61**, exp **+$1.88**, PF **1.911**, DD **$42.24**, supportive **YES**

## Other formal passers
1. `RV_MID__RANGE_HIGH / LB30 / hold240m`
   - N **201**, WR **57.21%**, net **+$197.95**, exp **+$0.98**, PF **1.547**, DD **$64.05**, LS **6**, anchors **4/4**
   - yearly WR: **58.18% / 55.22% / 58.23%**

2. `RV_MID__RANGE_HIGH / LB60 / hold360m`
   - N **185**, WR **59.46%**, net **+$141.25**, exp **+$0.76**, PF **1.355**, DD **$94.12**, LS **7**, anchors **3/4**
   - yearly WR: **56.34% / 67.24% / 55.36%**

3. `EFF_HIGH__RV_MID / LB30 / hold360m`
   - N **304**, WR **58.88%**, net **+$354.38**, exp **+$1.17**, PF **1.560**, DD **$124.59**, LS **5**, anchors **3/4**
   - yearly WR: **55.67% / 56.70% / 63.64%**

The selected `RV_MID__RANGE_HIGH / LB30 / hold360m` row ranks first under the frozen sequence because its weakest-year expectancy is materially stronger while also delivering 4/4 anchor support, stronger pooled expectancy/WR/PF, and substantially lower drawdown.

## Important near-misses
Attractive failed rows remain formal failures:
- `DRIVE_DOWN__STR_B80_100 / LB60 / hold720`: N324, WR54.32%, +$715.41, exp +$2.21, PF1.459, 4/4 anchors, but pooled WR <55%, DD $218.60, and 2022 WR49.02%.
- `DRIVE_DOWN__STR_B80_100 / LB60 / hold960`: N324, WR56.48%, +$635.80, exp +$1.96, PF1.375, 4/4 anchors, but DD $297.90 and 2022 WR52.94% means only two years clear 55% while pooled risk is unacceptable.
- `DRIVE_DOWN__STR_B80_100 / LB30 / hold720`: N318, WR55.03%, +$578.28, exp +$1.82, PF1.382, but DD $270.97, only 2/4 anchors, and 2022 WR51.09%.
- `EFF_HIGH__RV_HIGH / LB240 / hold960`: N420, WR51.19%, +$960.46, exp +$2.29, PF1.499, but pooled WR, DD $313.39, LS16, anchor stability, and era robustness all fail.

No failed row is promoted.

## Transition interpretation
- 08:00–09:00 WIB (B28I): **PASS**, 2 passers.
- 09:00–10:00 WIB (B28J): **FAIL**, 0 passers.
- 10:00–11:00 WIB (B28K): **FAIL**, 0 passers.
- 11:00–12:00 WIB (B28L): **FAIL**, 0 passers.
- 12:00–13:00 WIB (B28M): **PASS**, 4 passers.

Therefore the first consecutive unsupported B28 LONG cluster is currently bounded at **09:00–12:00 WIB**. It lasts three consecutive hours and ends cleanly at 12:00 WIB, where a materially more robust LONG habitat reappears.

B28M is not a marginal boundary PASS. The selected row clears all pooled, anchor and era gates with substantial margin: WR above 63% in every Development era, PF above 2 in every era, all four quarter-hour anchors supportive, DD only $41.59, and loss streak 5. This is qualitatively stronger than the headline-positive but risk-concentrated rows seen in B28J/K and the generally weak robustness observed in B28L.

The selected family is also coherent internally: three of the four formal passers are `RV_MID__RANGE_HIGH`, with the same LB30 selected at both hold240 and hold360 and a nearby LB60/hold360 variant also passing. This supports a pair-native descriptive interpretation of **mid realized volatility + high normalized range** as the dominant 12:00–13:00 WIB LONG state family. This interpretation is post-selection only and must not bias B28N ranking.

## Integrity
- Preregistered before economic output.
- OOS unopened.
- No SHORT search.
- No gate relaxation.
- No prior-hour coordinate preference.
- No B27 H2/P10 rescue.
- No post-result clock shift.
- No substitution of attractive failed rows.
- Workflow-registration retriggers altered only `.bnb-b28m-trigger`; preregistration and runner remained frozen.

## Next preregistered action
Continue the unchanged LONG-only economic-first sweep to **13:00–14:00 WIB**. Keep B28A–B28M outcomes frozen for later validation.
