# BTC ORB B4 — Top 2 Per Week Preregistration

Research only. Live BBC untouched.

## Objective
Precision-first: select at most 2 BTC H4 classic breakout trades per ISO week, with minimum RR 1:1.

## Universe
All causal BTC H4 CLASSIC breakout opportunities across all 4H anchors (UTC 0,4,8,12,16,20). Same next-4H-open entry and 12h max hold as B1/B3.

## Ranking (frozen before results)
No indicator stack. Only breakout quality from the trigger candle:
1. EXT_SCORE = breakout close distance beyond prior 4H range boundary / prior 4H range width.
2. EXT_BODY_SCORE = EXT_SCORE * trigger candle body/range ratio.

For each ISO week and each ranking family separately, keep only the top 2 opportunities by score. No hard threshold and no other filter.

## RR geometries
- R100 = TP 1.0R / SL 1.0R
- R125 = TP 1.25R / SL 1.0R
- R150 = TP 1.5R / SL 1.0R

## Evaluation
Chronological 70/30 split on selected trades. Report selected trades/week, N, wins, WR, expectancy after 0.15% fee, PF, and 4 chronological blocks.

Target is high precision with roughly <=2 trades/week. No post-result threshold rescue inside B4.
