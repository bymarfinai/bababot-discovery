# SOL Long Leg Onset V2 — Preregistration

Purpose: fix the timing failure found in SOL Long Leg Capture V1.

V1 showed abundant ex-post long-leg opportunity but poor early-hit rates. V2 therefore changes ONLY the supervised target: instead of learning generic TP-before-SL outcomes, learn whether the current completed 15m bar belongs to the early onset region of a future large LONG leg.

Frozen data/execution:
- SOLUSDT USD-M, repository 5m loader
- completed 15m signal; next 15m open entry
- completed 1H/4H context only
- 0.15% round-trip cost
- USD500 notional
- one active position
- same-5m TP/SL ambiguity = loss

Ex-post onset labels:
- legs are the same 1% reversal-segmented 15m close legs as V1
- for each L2/L3/L5 leg, a bar is ONSET=1 only while:
  1. it lies between leg start and leg peak;
  2. its close has progressed no more than 25% of the final leg amplitude from the leg start.
- all other feature-complete bars are ONSET=0.
- future information is used only to create training labels, never as an input feature.

Trade evaluation remains:
- L2: TP +2%, SL -1%, max hold 24h
- L3: TP +3%, SL -1%, max hold 48h
- L5: TP +5%, SL -1%, max hold 72h
Thus all variants satisfy TP>=1% and RR>=1:1.

Time discipline:
- fit only on 2023 onset labels
- choose score threshold on 2024 only
- freeze and transfer to 2025 and 2026
- no refit after 2023

Model family:
RandomForestClassifier, balanced_subsample, settings:
- depth 4 / min leaf 100
- depth 6 / min leaf 100
- depth 8 / min leaf 100
- depth 8 / min leaf 200
Threshold quantiles: 50% through 99%, fixed grid identical to V1.

Eligible 2024 threshold:
- >=3 executed trades/week
- positive after-cost expectancy
Ranking:
1. highest mean weekly net return
2. highest early-leg hit rate
3. highest WR
4. highest median weekly return

Success criterion:
A useful onset detector must improve early-leg hit rate materially versus V1 AND retain positive expectancy on 2025 and 2026. No conclusion is based on training-label accuracy alone.
