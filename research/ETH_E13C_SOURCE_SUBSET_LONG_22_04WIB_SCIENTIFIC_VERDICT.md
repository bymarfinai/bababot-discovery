# ETH E13C — Sequential LONG Source-Subset Scientific Verdict

## Status
**ETH_E13C_NO_SOURCE_SUBSET_PASSER**

Development/shadow only. OOS remained closed.

## Result-bearing run
- workflow run: **34578220495**
- job: **103195497779**
- head SHA: **70401380257c923ce704b2562dc9f481547d6e83**
- artifact: **10190509189**
- artifact SHA256: **cdf762a89f5d14031421bc9b7ec7158bd7ac2228d20893527f212ba728adaafe**
- raw ETHUSDT 5m coverage: **100.0000%**

## Formal result
**0 / 15 source subsets passed both unchanged E13B pooled and era gates** at the frozen E13B coordinate: net floor $5.00 / 36h max hold.

## Key source-subset result
Source selection materially improves path quality. Three subsets pass the pooled execution gate:
- **KO**: N260, WR76.15%, net +$336.15, exp +$1.29, PF1.377, DD$124.35, LS3, timeout25.38%.
- **MO**: N224, WR73.66%, net +$279.20, exp +$1.25, PF1.382, DD$113.03, LS5, timeout28.57%.
- **LMO**: N355, WR75.49%, net +$440.64, exp +$1.24, PF1.363, DD$113.70, LS6, timeout26.48%.

All three remain era-gate failures.

## Closest robust near-miss — LMO
**LMO = E12L 00–01 + E12M 01–02 + E12O 03–04; E12K 23–00 excluded.**

Pooled execution passes every frozen E13B threshold:
- N **355**
- WR **75.49%**
- net **+$440.64**
- expectancy **+$1.2412/trade**
- PF **1.363**
- max DD **$113.70**
- max loss streak **6**
- timeout **26.48%**

Era:
- 2022: WR **81.67%**, exp **+$0.63**, PF **1.133** -> FAIL only because PF is below the frozen 1.15 floor.
- 2023: WR **65.74%**, exp **+$0.98**, PF **1.336** -> PASS yearly floor.
- 2024: WR **77.95%**, exp **+$2.04**, PF **1.779** -> PASS strongly.

Thus LMO misses full promotion by one narrow cross-era payoff-efficiency clause: 2022 PF 1.133 vs required 1.15.

## Source interpretation
- K alone is economically positive but has a weak 2023 regime: WR60.29%, exp -$0.59, PF0.856.
- L alone has a weak 2022 payoff profile: exp -$2.91, PF0.651.
- M alone is under the pooled N floor and has weak 2022 PF/2023 WR.
- O alone is economically strongest (WR81.13%, exp +$2.09, PF1.761, DD$71.49) but only N106 and its 2023 WR is 57.14%, so it is not a broad formal executor by itself.
- Combining L+M+O creates diversification that repairs pooled economics while retaining adequate yearly sample size, but 2022 PF remains marginally short of the preregistered era gate.

## Scientific interpretation
E13C supports source selection as a real execution dimension: not every E12 formal character should automatically feed the same sequential executor. Excluding K materially improves pooled DD/PF at the frozen exit coordinate.

However E13C does not promote LMO because its 2022 PF remains below the frozen threshold. No threshold relaxation is allowed.

## Final local refinement authorized
A new preregistered E13D may freeze the **LMO source subset** and test only a small exit neighborhood around the E13B/E13C coordinate. This is a one-time local refinement, not an open-ended search.

Recommended frozen grid:
- net profit floors: 0.75%, 1.00%, 1.25%, 1.50% of $500 notional;
- max holds: 24h, 36h, 48h;
- exactly 12 candidates;
- unchanged E13B/E13C promotion gates.

If E13D produces no full passer, stop target/hold/source tuning in this lineage and move to a separately preregistered structural-risk or SHORT research phase rather than continuing to fit Development.

No OOS exposure. No live promotion.