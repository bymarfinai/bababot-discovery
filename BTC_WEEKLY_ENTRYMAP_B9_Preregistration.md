# BTC Weekly Entry Map B9 — Preregistration

Status: **FROZEN BEFORE RESULT**

Purpose: test whether a causal weekly entry-selection process can produce at least one BTC trade in every complete ISO week while reaching 100% historical positive-return win rate on both untouched external data and reference validation, with modeled net RR >= 1:1. This is a research target, not a guarantee of future wins.

## Why B9 is materially different from covered work
The registry already covers generic ORB, support/resistance, FVG, Fibonacci, candle filters, regime filters, and the B8 multi-theory voting router. B9 does not retune those studies. The new object is a **side-conditioned structural level map + development-only supervised ranking model**. Instead of counting how many theories agree, B9 represents the geometry of the current price relative to multiple causal levels and learns which geometry historically produced a net 1R win. The model is trained only on 2022-2024 and then frozen before external/reference-validation evaluation.

No retrospective best-trade-of-week selection is allowed. A trade must be knowable at the completed signal bar and entered at the next bar open.

## Market / source / partitions
- BTCUSDT USD-M perpetual.
- Official completed Binance Futures H1 archive already used in this repository.
- Native H1 and UTC-aligned H4 aggregated from H1.
- External untouched: 2020-01-01 through 2021-12-31.
- Development/training only: 2022-01-01 through 2024-12-31.
- Reference validation: 2025-01-01 through 2026-07-29.
- August diagnostic: 2026-08-01 onward through available completed archive.

## Weekly clock
For each timeframe independently:
- ISO week starts Monday 00:00 UTC.
- Causal scan window is Monday 00:00 UTC through the fixed Friday 12:00 UTC signal bar.
- H1 Friday checkpoint entry is Friday 13:00 UTC open.
- H4 Friday checkpoint uses the completed 12:00-16:00 UTC H4 bar and enters Friday 16:00 UTC open.
- Maximum one trade per complete ISO week.
- If no model-qualified structural entry occurs earlier, the Friday checkpoint is a forced fallback so weekly coverage cannot be hidden by NO TRADE weeks.

## Causal structural map
Every completed signal bar is evaluated for LONG and SHORT separately using only information available by that close. The fixed feature family is:

1. **Prior-20 support/resistance geometry**
   - normalized distance from close to the relevant prior-20 extreme in ATR units;
   - current-bar sweep/reclaim of the relevant prior-20 extreme;
   - normalized room from entry-side extreme toward the opposite prior-20 extreme.

2. **Previous-week liquidity geometry**
   - previous complete ISO-week high and low only;
   - normalized distance from close to the side-relevant previous-week extreme;
   - current-bar sweep/reclaim of that previous-week extreme;
   - position inside the previous-week range.

3. **Opening-range geometry**
   - fixed UTC daily opening range 00:00-04:00 UTC, available only after completion;
   - normalized signed distance to the side-relevant OR boundary;
   - reclaim/rejection state at the OR boundary.

4. **FVG geometry**
   - most recent still-active standard 3-bar FVG formed strictly before the signal bar, searched in the prior 12 completed bars;
   - normalized distance to its midpoint for the matching side;
   - whether the current signal bar touches/mitigates that FVG.

5. **Fibonacci geometry**
   - prior 12 completed bars, excluding signal bar;
   - impulse requires total range >= 2 ATR and chronological low->high for bullish / high->low for bearish;
   - fixed 50.0%-61.8% retracement zone;
   - normalized distance to zone midpoint for the matching side;
   - current-bar zone touch.

6. **Signal-bar rejection geometry**
   - side-aligned candle body / ATR;
   - side-relevant rejection wick / ATR.

No EMA, funding, OI, taker flow, weekday carve-out, session optimization, arbitrary Fibonacci sweep, alternative OR duration, or management layer is introduced in B9.

## Side-conditioned rows and labels
At each eligible completed bar, construct one LONG row and one SHORT row from the same causal map.

Training label is executable net-positive outcome for that side using the frozen B9 execution below. Labels use future bars only for training targets; no future information enters features.

## Model
One fixed model per timeframe:
- `StandardScaler` + `LogisticRegression`;
- L2 penalty;
- `C=0.5`;
- `solver=liblinear`;
- `max_iter=2000`;
- deterministic random state 20260821 where applicable;
- trained on development 2022-2024 only.

The model outputs `P(net_positive)` separately for LONG and SHORT.

At every signal bar, the side with higher predicted probability is the provisional direction.

## Structural eligibility
An early trigger is allowed only if the chosen side is structurally near/engaged with at least one mapped location using this frozen rule:
- prior-20 extreme distance <= 0.35 ATR; OR
- previous-week extreme distance <= 0.35 ATR; OR
- OR boundary distance <= 0.35 ATR after OR completion; OR
- active matching FVG is touched; OR
- matching Fibonacci zone is touched; OR
- a prior-20 or previous-week sweep/reclaim occurs.

Distances are absolute for eligibility. This rule is fixed before results.

## Development-only probability threshold
No validation/external threshold tuning is allowed.

For each timeframe:
1. score every development signal bar inside the weekly scan window;
2. retain structurally eligible bars and the higher-probability side at each bar;
3. let `M` be eligible development bars and `W` be complete development weeks;
4. set one deterministic threshold using `q = max(0, 1 - W/M)` and the q-quantile of development max-side probabilities.

This targets roughly one raw above-threshold structural opportunity per development week without using validation or external outcomes.

## Weekly causal router
For each complete week:
1. scan bars chronologically from Monday to Friday checkpoint;
2. at each bar calculate LONG and SHORT probability;
3. choose the higher-probability side;
4. if the bar is structurally eligible and its probability >= the frozen development threshold, enter that side at the next bar open and stop scanning the week;
5. if no threshold event occurs by the Friday checkpoint, choose the higher-probability side at the checkpoint and enter next open regardless of eligibility (`FORCED_FALLBACK`).

No ranking of earlier bars after they have passed is allowed.

## Execution
- Risk distance = 1.0 ATR(14) from the completed signal bar.
- Modeled round-trip fee = 0.15%.
- TP raw distance is set so modeled **net reward equals modeled net loss** after fee (net RR 1:1).
- H1 max hold = 12 completed H1 bars / 12h.
- H4 max hold = 6 completed H4 bars / 24h.
- Same-bar TP+SL ambiguity = adverse-first / SL.
- TIME exit = final frozen hold-bar close.
- No trailing stop, break-even, partial exit, recovery, or post-entry rescue.

## Required reporting
For H1 and H4, report for development, external, reference validation, and August diagnostic:
- complete weeks / selected trades / weekly coverage;
- model-trigger vs forced-fallback counts;
- TP / SL / TIME;
- positive-return WR and decisive TP-vs-SL WR;
- net expectancy and profit factor;
- max losing streak;
- four chronological blocks;
- exact losing weeks;
- trained threshold;
- training sample size and training positive rate;
- model coefficients by named structural feature.

## Acceptance gates
`B9_ROBUST_WEEKLY_100=PASS` only if at least one timeframe satisfies all:
- external weekly coverage = 100%;
- reference-validation weekly coverage = 100%;
- external N >= 20 and positive-return WR = 100%;
- reference-validation N >= 20 and positive-return WR = 100%;
- zero losing weeks in both;
- positive expectancy and PF > 1 in both;
- all four chronological blocks positive-return expectancy in both external and validation.

`B9_HIGH_PRECISION_WEEKLY=PASS` only if the same coverage/N gates hold with:
- external and validation WR >= 80%;
- positive expectancy and PF > 1 in both;
- max losing streak <= 2 in both;
- at least 3/4 positive-expectancy blocks in both.

## Anti-rescue lock
If B9 fails, do not rescue this sample by changing logistic C, threshold quantile, eligibility distance, feature weights, OR hours, Fib ratios, FVG lookback, ATR stop, RR, hold, Friday checkpoint, side rule, or dropping forced fallback weeks. Do not cherry-pick one coefficient or one losing-week pattern and call it a strategy. Any follow-up must introduce a separately preregistered information source or selection mechanism.

Live BBC untouched.
