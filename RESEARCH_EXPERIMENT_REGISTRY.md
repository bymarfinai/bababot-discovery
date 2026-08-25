# BabaBot Research Experiment Registry — Do Not Repeat Without New Evidence

**Purpose:** prevent renaming/repeating research that has already been tested. This registry was built from the repository tree, research-script inventory, checkpoint/conclusion artifacts, and targeted reads of the key implementation families. New research should check this file first.

## 1. Legacy BBC / Mode3 / execution timing — COVERED
Already tested in multiple forms:
- Mode3/BBC baseline and config sweeps;
- EMA / body-ratio / direct-transition variants;
- same-hour 15m MTF;
- causal BBC and causal parity;
- causal sniper / next-15m confirmation;
- state reject / state+MTF reject;
- honest 15m execution;
- limit-entry simulation;
- filtered reclaim / filtered switcher;
- V2/V2.5/V3 entry-quality families;
- V7 legacy-vs-causal-vs-1H-close trigger forensics;
- BBC V4 strict next-1H-open causal baseline;
- BBC V4-A causal post-close 15m confirmation.

Latest causal conclusion: plain BBC/EMA architecture does **not** retain positive economics when entry is made executable. Do not reopen EMA/TP/SL/body-ratio sweeps merely to force a pass.

## 2. Structural / support-resistance / liquidity / order-block-like location — COVERED
Already tested:
- V4 structural zones;
- first retest quality;
- liquidity-created zones;
- liquidity first retest;
- liquidity-validated origin retest;
- reaction/absorption confirmation;
- absorption forensic.

Do not propose generic “add order block/support confluence” as a new idea without a materially different causal definition and preregistered hypothesis.

## 3. Fibonacci / contextual retracement — COVERED
Already tested across V4 context-Fib and multiple temporal transfer/forensic families, including recent-vs-history investigations.
Do not reopen arbitrary Fibonacci band sweeps.

## 4. Taker flow / order-flow proxies — COVERED PER PAIR
`taker_forensic_endpoint.py` validates and tests causal taker-buy volume, delta, z-scores, rolling delta, divergence/alignment, volume z-score, and 1h/4h context on fixed-pair entries.
Do not repeat winner-vs-loser taker filters on the same fixed-pair setup.

## 5. Derivatives context — DATA FEASIBILITY COVERED
`v5_derivatives_feasibility_endpoint.py` audited funding, open-interest history, global/top-trader long-short ratios, public metrics archives, and liquidation-history availability/causality.
Do not assume full 971d historical OI/ratio data is available from REST without rechecking source coverage.

## 6. Market regime / breadth / volatility state — COVERED FOR FIXED-PAIR SETUPS
Already tested:
- 4H regime experiment;
- V2.5 regime expansion;
- V4 market-state forensic (own 4h/24h/7d returns, ATR/RV expansion, trend efficiency, four-pair breadth/synchronization/alignment);
- BTC G0–G7 pooled/global regime family;
- temporal regime attribution / slow-health diagnostics.

G0–G7 conclusion: pooled BTC state is modestly learnable, but historical regime gates/sizing do not earn promotion for frozen Tuesday A5.11. Keep G1/G6 as telemetry only; no threshold/model-complexity sweeps.

## 7. Ratio-series / spreadsheet forecasting — COVERED
Causal ratio-series test of the uploaded workbook idea (recent close-ratio averaging, native lookbacks 4/5) has its own audit including contaminated diagnostic. Do not rebrand this as AI forecasting.

## 8. Continuation / dynamic-direction / entry-trigger families — COVERED
Already tested through continuation detector, V2.5 triggers, V7 trigger forensics, BTC temporal dynamic-direction and low-dimensional direction work. New work must differ in information set or selection problem, not merely trigger naming.

## 9. BTC temporal weekday research — EXTENSIVELY COVERED
### Tuesday
A1/A2/A3/A5 families through frozen A5.11; Tuesday-only ML; compression; true-OOS August; G0–G7 regime family; true-forward shadow/evaluator. **Frozen. Do not retune.**

### Friday
Large F5/F6 family through at least F6.41, covering failure timing, recovery, early sink, EMA failure, context, candle morphology, Fibonacci, giveback, post-1R protection, displacement, failure-to-accelerate/develop, fake bounce/slow recovery, flow reversal, rejection/expansion balance, robustness, and true-OOS August. Do not restart these as generic “management improvement.”

### Saturday
S5/S6 families covering adaptive failure, timing, EMA reclaim cut, runner protection/recovery/immunity, candle morphology, excursion/stall, dynamic direction, pre-entry features, low-dimensional walk-forward, Friday-method transfers, and true-OOS.

### Sunday
Sun/SF/ST families covering TP/SL surfaces, hold/exit, reverse, Tuesday-geometry transfer, funding forensics, failed development, dynamic direction, bad-state/wait refinement, frozen router true-OOS, Friday/T-method transfers, FastMR, morphology, regime, and August replay/OOS.

## 10. Recovery / exit / runner management — EXTENSIVELY COVERED
Across temporal families the repo has already tested break-even, early cuts, failure exits, FastMR, runner recovery/protection, giveback management, failed acceleration/development, recovery windows, and false-positive anatomy.
Do not optimize management on another same-sample slice unless a new entry edge first exists.

## 11. Cross-sectional broad-universe Market Hunter — MH0 COVERED / REJECTED
MH0 was preregistered before result observation and tested 56 USDT perpetual symbols over a frozen 365d window using official Binance Data Vision 1h data.

Frozen design:
- same-time cross-sectional ranks across 56 contracts;
- causal completed 1h features: 4h/24h return, relative quote volume, range expansion, prior-24h breakout position, taker imbalance;
- trailing-24h cross-sectional liquidity filter;
- top-1 pair+direction selection;
- next-1h-open execution;
- 0.15% modeled round-trip cost;
- controls: raw 24h momentum and deterministic random selection;
- sequential TP/SL control: 1.3%/1.3%, max hold 6h.

365d result:
- independent composite 6h net expectancy: **-$0.6668/opportunity**, PF **0.887**;
- sequential composite: **3,713 trades, WR 44.52%, -$4,764.95, -$1.2833/trade, PF 0.648**;
- all four chronological blocks negative;
- LONG: -$3,984.92; SHORT: -$780.04;
- raw momentum and random controls were also negative after costs.

Verdict: **REJECT_MH0_LIVE_CANDIDATE.**
Do not sweep feature weights, Top-K, liquidity percentile, TP/SL, or score thresholds on this sample to force a pass. Any future cross-sectional study must introduce a materially different information set or a genuinely independent validation question.

Canonical artifacts:
- `MARKET_HUNTER_MH0_Preregistration.md`
- `MARKET_HUNTER_MH0_Result.md`
- `MARKET_HUNTER_MH0_Result.json`

## 12. F15 bearish continuation clock habitat — B27DR/B27DS COVERED / PROMISING HISTORICAL
The exact causal SHORT homolog of the London -> New York F85 LONG structure is frozen as:

`reference range -> first Low K1 OPP0 pressure visit -> causal leave -> pre-H2 F15 touch -> SAME_BAR close < F15 -> SHORT next 5m open -> return to Low/H2 -> E20_DOWN extension`, with F65 completed-close invalidation.

### B27DR — 48-clock rotation
B27DR moved only the clock across 48 half-hour reference starts while freezing the 5h30 reference duration, 6h30 execution duration, F15/F65/E20_DOWN geometry, SAME_BAR confirmation, fee and sizing. London 08:00 UTC parity against B27AD passed.

The formal development winner, reference 03:00 UTC, achieved development N=37, WR 83.8%, PF 1.67, but failed reference-validation replication (N=11, WR 54.5%, PF 0.73). Verdict: **B27DR_NEW_SHORT_CLOCK_DEV_CANDIDATE_NOT_REPLICATED**.

A separate preregistered follow-up was justified by the coarse 20:00 UTC row because all historical partitions were strong but development N=19 was below B27DR's minimum-N gate.

### B27DS — 20:00 UTC local stability
B27DS preregistered a narrow local grid 19:30/19:40/19:50/20:00/20:10/20:20/20:30 UTC without changing the SHORT structure or economics. Exact 20:00 B27DR parity passed.

Selected clock: **20:00 UTC reference -> 01:30-08:00 UTC next-day execution**.
- external: N=27, WR 74.1%, PF 2.22, net +$31.35;
- development: N=19, WR 78.9%, PF 3.99, net +$39.46;
- reference_validation: N=10, WR 80.0%, PF 2.70, net +$6.91;
- pooled major: N=56, WR 76.8%, PF 2.81, expectancy +$1.39/trade, net +$77.73.

Immediate-neighbor timing basin was supported: 20:10 remained development-eligible (N=25, WR 72.0%, PF 3.05), and 20:20 remained positive/supportive (N=25, WR 68.0%, PF 2.06). Verdict: **B27DS_LOCAL_BASIN_HISTORICAL_REPLICATION_SUPPORTED**.

Evidence limitation: external/reference_validation are reused historical partitions, not pristine unseen OOS. Do not re-sweep F15/F65/E20_DOWN or add indicators to force higher WR on these same samples. The next confirmatory question should freeze the 20:00 clock and exact SHORT rules before genuinely unseen forward data or another independent validation source is observed.

Canonical artifacts:
- `BTC_GENERIC_F15_SHORT_CLOCK_SCAN_B27DR_Preregistration.md`
- `BTC_GENERIC_F15_SHORT_CLOCK_SCAN_B27DR_Result.md`
- `BTC_F15_SHORT_2000_LOCAL_CLOCK_STABILITY_B27DS_Preregistration.md`
- `BTC_F15_SHORT_2000_LOCAL_CLOCK_STABILITY_B27DS_Result.md`

# Current open research gap
For the F15 SHORT clock-habitat lineage, the main evidence gap is **pristine unseen OOS confirmation** of the frozen 20:00 UTC reference / 01:30-08:00 UTC execution rule. Historical local-clock discovery and reused-partition replication are now covered; further same-sample clock or geometry tuning should not be used as confirmation.

# Rule for future research
Before creating a new backtest:
1. identify the proposed information set, selection mechanism, timing, and management;
2. compare it against this registry and repository search;
3. if only thresholds/indicators/naming differ from a covered family, do **not** run it;
4. if materially novel, preregister the hypothesis and controls before observing results;
5. persist a KEEP/REJECT conclusion so the registry can be updated.
