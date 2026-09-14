# SOL Adaptive Structure Detector v2 — Preregistration

## Objective
Replace threshold/hour hunting with an online sequence/path analog detector. The detector asks whether the current ORB-breakout-retest-BOS path resembles prior SOL paths whose outcomes are already known, then estimates P(win) and net 60m edge from those historical analogs.

## Frozen structural universe
- Symbol: SOLUSDT, 5m.
- Weekdays only.
- Event skeleton: 15m ORB -> first upside close breakout within the anchor hour -> first retest touch within 30m -> first small BOS within the next 3 bars, with BOS close above anchored VWAP -> entry next 5m open.
- Fixed diagnostic outcome: net return 60m after entry, roundtrip cost 0.15%, $500 reference notional.
- All 24 anchor hours remain in one universe; hour is context, not a separate strategy.
- Model/history data: 2020-01-01 through 2024-12-31 only. 2025+ remains closed.

## Sequence representation
For each event, use only information known by BOS close. Build a variable-length path from anchor start through BOS and resample it to 18 normalized time points. Four causal channels are stored at each point:
1. close position relative to ORB midpoint, divided by ORB range;
2. high position relative to ORB midpoint, divided by ORB range;
3. low position relative to ORB midpoint, divided by ORB range;
4. close minus causal anchored VWAP, divided by ORB range.

Add causal phase/context descriptors: breakout/retest phase, bars to BOS, hour sin/cos, trailing volatility/trend context, ORB volume/range context, breakout/retest/BOS timing and displacement descriptors. No future bars are features.

## Online analog rule
For each event at prediction time T:
- only prior events with their full 60m outcome already known by T may be analogs;
- analog memory is trailing 730 calendar days;
- minimum candidate pool = 120 prior events;
- robust-scale every vector dimension using only the current prior pool (median/IQR, no future data);
- Euclidean RMS distance in the standardized vector space;
- use the 60 nearest neighbors;
- similarity weight = exp(-distance / median-neighbor-distance);
- predicted P(win) = similarity-weighted analog win rate;
- predicted edge = similarity-weighted analog net 60m return;
- effective analog N = Kish effective sample size of similarity weights.

## Frozen trade gate
A current event is `TRADE` only when all are true:
- predicted P(win) >= 60%;
- predicted net 60m edge >= +0.15%;
- effective analog N >= 20.

These gates are diagnostic and may not be tuned after results are read.

## Evaluation
Evaluate every causally eligible prediction from 2020-2024 and report:
- ROC AUC of predicted P(win);
- Brier score;
- Spearman and Pearson correlation between predicted edge and actual net return;
- actual economics of all eligible events vs predicted TRADE events;
- edge quartiles;
- calendar-year economics.

A v2 detector is `PROMISING_SEQUENCE_ANALOG` only if:
1. ranking direction is positive (Spearman > 0 and top predicted-edge quartile has higher actual expectancy than bottom quartile);
2. predicted TRADE sample has N >= 30, actual WR >= 60%, positive expectancy and PF > 1;
3. at least two calendar years have N >= 5 predicted trades and positive expectancy.

Otherwise verdict is `REJECT_V2_SEQUENCE_ANALOG`.

## Anti-overfit boundary
No threshold, K, analog-window, path length, feature list, outcome horizon, or distance rule may be changed after inspecting this run. Any redesign must be a separately preregistered v3. 2025+ must remain unopened during v2 discovery.