# BNB LONG Reset V1 — H01 Primary Persisted Verdict

- Habitat: **01:00–02:00 WIB**
- Development: **2022–2024**
- Events: **4,384**
- Primary candidates: **34**
- Full-gate passers: **0**
- Verdict: **PRIMARY_FAIL**
- OOS: **sealed; not downloaded/evaluated**

## Strongest primary candidate

`drive_240m__LOW`

- N: **1,366**
- Consensus WR: **56.73%**
- Mean consensus return: **+0.0443% / observation**
- Consensus PF: **1.159**
- Max loss streak: **14**
- Supportive horizons: **2/3**
- Supportive anchors: **4/4**
- Years with WR >55%: **3/3**

Reference economics at $500 notional (diagnostic, not executable net PnL):
- Raw mean: **+$0.22 / observation**
- Raw cumulative equivalent: **+$302.74**
- Avg winning observation: **+$2.85**
- Avg losing observation: **-$3.23**
- Raw max DD equivalent: **-$128.66**

### Cross-year
- 2022: N 413, WR 56.17%, mean +0.1091%, PF 1.362, raw eq +$225.38
- 2023: N 462, WR 58.66%, mean +0.0231%, PF 1.098, raw eq +$53.29
- 2024: N 491, WR 55.40%, mean +0.0098%, PF 1.032, raw eq +$24.07

### Horizons
- 60m: WR 56.52%, mean +0.0593%, PF 1.286, raw eq +$404.81 — supportive
- 120m: WR 57.17%, mean +0.0121%, PF 1.036, raw eq +$82.33 — not supportive
- 240m: WR 58.13%, mean +0.0617%, PF 1.150, raw eq +$421.07 — supportive

### Exact failure
1. Pooled PF **1.159 < frozen 1.20** → pooled gate FAIL.
2. 2024 PF **1.032 < frozen 1.05** → era gate FAIL, despite 2024 WR 55.40% and positive mean.
3. 120m PF **1.036 < frozen 1.10** → that horizon not supportive; 2/3 horizon rule still passes, but it confirms weak middle-horizon economics.

No threshold relaxation, pairwise rescue, or secondary-confirmation rescue is allowed. H01 is closed. Next eligible habitat: **H02 02:00–03:00 WIB**, same frozen methodology.
