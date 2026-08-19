# BabaBot Research Registry Addendum — BTC Friday 80% Identifier Track

**Purpose:** prevent repeating or renaming the BTC-Friday high-WR identification studies run after the main `RESEARCH_EXPERIMENT_REGISTRY.md` checkpoint. Read this addendum together with the main registry before proposing another BTC Friday candle/setup backtest.

## Target definition
The research target is an **observed historical executable WR >=80% with meaningful support and chronological/OOS survival**, not a guarantee of future wins. Discovery-only 80% results are not accepted.

## P0 — exact F6.38 pre-entry balance relation as standalone filter — REJECT
Applied the already-known F6.38/F6.39 pre-entry wick-vs-body relationship to every canonical Friday opportunity, without post-entry cohort information.
- full BALANCE=True: N86, WR52.33%
- discovery: N49, WR59.18%
- validation: N37, WR43.24%
Verdict: `REJECT_AS_80_CANDLE_IDENTIFIER`.
Conclusion: the earlier high-WR F6.38 observation depended on its branch context; the candle relation alone does not identify winners.

## P1 — fixed 5m morphology grammar — REJECT
Frozen grammar: 12 already-defined morphology atoms, all single literals and all two-literal AND combinations, 288 discovery rules total.
Eligibility required discovery N>=12, WR>=80%, positive PnL and PF>1.
- qualifying discovery rules: 0
Verdict: `REJECT_P1_80_CANDLE_IDENTIFIER`.
Do not rerun by adding a third literal, flipping a runner-up, or changing morphology thresholds on the same sample.

## P2 — exact-Friday shallow price/candle tree — REJECT
Depth-2 decision tree, min leaf12, discovery first82 Fridays, validation remaining56, strictly pre-entry price/candle features.
Discovery-selected fingerprint:
`m15_ret <= -0.002743932 AND entry_dist_ema7 <= -0.0010714794`
- discovery: 21/22 = 95.45%
- validation: 8/15 = 53.33%
- full: 29/37 = 78.38%
Verdict: `REJECT_P2_80_CANDLE_IDENTIFIER`.
This is a canonical example of a spectacular discovery result collapsing in holdout. Do not deepen the tree on the same feature set to rescue it.

## C0 — all Friday-WIB 1h candle identifier — REJECT
All BTC Friday-WIB 1h signal candles, next-1h-open execution, continuation and reversal, TP/SL1.3/1.3, hold6h, fee0.15%, depth2/minleaf100.
- 142 Friday dates, 3,407 signal candles
- best discovery leaf approximately 59.83% continuation / 55.56% reversal
Verdict: `REJECT_C0_80_CANDLE_IDENTIFIER`.

## C1 — all Friday-WIB 15m single-candle archetypes — REJECT
Fixed six-field categorical candle archetype; no learned thresholds.
- 141 Fridays, 13,531 signals, 68 archetypes
- best support>=40 approximately 57.50% continuation / 58.14% reversal
- zero discovery 80% candidates
Verdict: `REJECT_C1_80_CANDLE_IDENTIFIER`.

## C2 — all Friday-WIB 5m single-candle archetypes — REJECT
Same frozen archetype logic on 5m candles.
- 141 Fridays, 40,568 signals
- zero discovery 80% candidates
- best support>=100 approximately 29.50% continuation / 34.68% reversal
Verdict: `REJECT_C2_80_CANDLE_IDENTIFIER`.
Conclusion with C0/C1: single-candle morphology alone is closed across 5m/15m/1h under these causal next-open studies.

## C3 — 15m two-candle sequence + local range context — REJECT
Frozen full categorical key: prior->signal colors, signal body/dominance, range state, prior4 trend, range break/inside, trend relation.
- 13,526 signals, 171 sequence/context archetypes
- zero 80% candidates
- best approximately 61.29% continuation / 64.71% reversal
Verdict: `REJECT_C3_80_SEQUENCE_IDENTIFIER`.
Do not simplify keys post-result or validate runner-up patterns.

## SR80 — Friday support/resistance level reliability — REJECT
First-touch deterministic levels; discovery-selected reliability rule reached 89.47% discovery but failed holdout:
- discovery: 34/38 HOLD = 89.47%
- validation: 7/11 = 63.64%
- full: 41/49 = 83.67%
Verdict: `REJECT_SR80_LEVEL_IDENTIFIER`.
This is level correctness, not trade PnL.

## SR81 — prior-proven level rule — REJECT
A level was PRIOR_PROVEN only if prior7d had >=2 resolved same-side reactions, all HOLD and zero BREAK.
- discovery: 17/28 = 60.71%
- validation: 7/9 = 77.78%
- full: 24/37 = 64.86%
Verdict: `REJECT_SR81_PRIOR_PROOF_LEVEL`.
Post-hoc descriptive SUPPORT subset was 11/13 =84.62%; this was NOT accepted as a rescue.

## SR82 — untouched earlier BTC validation of SR81 SUPPORT clue — REJECT
Support-only clue was frozen after SR81 and tested only on earlier BTC Fridays 2022-01-07 through 2023-11-24, entirely before the SR80/SR81 sample.
- PRIOR_PROVEN_SUPPORT touches:16
- resolved:12
- HOLD6 / BREAK6 =50.00%
- Wilson95 25.4%–74.6%
- integrity violations0
Verdict: `REJECT_SR82_SUPPORT_EXTERNAL`.
Conclusion: SR81's 84.62% SUPPORT observation was sample-specific.

`SR82-T0` executable bullish rejection-candle trade was preregistered conditionally but MUST NOT be evaluated because SR82 context rejected.

## C4 — 15m candle + taker-flow/participation — REJECT
Features added causal taker imbalance, taker change, relative quote volume and relative range to candle geometry; depth2/minleaf100 trees for continuation/reversal.
- 141 Fridays, 13,531 signals
- eligible discovery 80% leaves:0
- best continuation leaf41.56%; best reversal40.12%
Verdict: `REJECT_C4_TAKER_IDENTIFIER`.
Do not retune tree depth or flow thresholds on the same sample.

## C5 — 15m candle + derivatives state — REJECT
Official Binance futures metrics strictly before entry, max15m stale. Added top-vs-global positioning, top-position change, crowd change, taker long/short ratio, OI15m and OI60m changes.
- 139 Fridays, 13,253 causally aligned rows
- metrics rows280,054
- integrity violations0
- eligible discovery 80% leaves0
- best discovery leaf40.82%
Verdict: `REJECT_C5_DERIVATIVES_IDENTIFIER`.
Do not deepen the same tree or tune derivatives thresholds.

## C6 — selective walk-forward AI — REJECT
Strongest tested formulation of the “AI robot picks only the right candle” hypothesis.
- inner-joined C4+C5 causal features
- HistGradientBoosting models for LONG and SHORT success
- first52 Fridays warmup
- each later Friday model fit only on strictly earlier Fridays
- model scored all Friday 15m candles and selected at most one highest-confidence candidate
- TRADE only at frozen confidence >=0.80
- 86 pseudo-OOS Fridays scored
- confidence>=0.80 trades: **0**
- integrity violations0
Top-candidate calibration:
- <0.50: 60 Fridays, observed WR8.33%
- 0.50–0.60:21 Fridays, WR28.57%
- 0.60–0.70:5 Fridays, WR80.00% (only N5; mean model confidence61.86%; not a valid threshold rescue)
- 0.70–0.80:0
- >=0.80:0
Verdict: `REJECT_C6_SELECTIVE_AI_IDENTIFIER`.
Do NOT lower the threshold to 0.60 after observing the five favorable cases; that would be same-sample retuning and the support is far too small.

# Current conclusion of the Friday-80 track
No robust causal BTC-Friday executable candle/setup with observed WR>=80% and meaningful validation support has been identified by:
- pure 5m/15m/1h candle morphology;
- fixed two-candle 15m sequence/context;
- exact-Friday shallow price/candle tree;
- deterministic support/resistance reliability and prior-proof context;
- untouched earlier external validation of the strongest post-hoc support clue;
- candle-level taker participation;
- futures OI/top-trader/crowd derivatives state;
- selective pseudo-OOS AI with a frozen 80% confidence threshold.

Therefore **do not transfer any of these rejected fingerprints to other coins** and do not claim an 80% BTC setup has been found.

# Rule for next work
A new BTC-Friday 80% study must introduce genuinely new information or a genuinely independent target/validation design. It may not be a threshold, tree-depth, morphology-bucket, TP/SL, confidence-cutoff, runner-up, or source-family rescue of the rejected studies above. If no materially new historical information source is available, the scientifically correct outcome is to keep “80% robust identifier not found” rather than manufacture one.