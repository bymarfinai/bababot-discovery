# Sunday Friday-Method SF6-SF8 — Confirmed Failure

**Status: COMPLETE — single natural failure state + Friday-style recovery confirmation.**

## Rule
- +6h candidate: MFE<0.5R, progress<=0, close>=EMA20, bullish candle majority >50%.
- +7h: if close improves downward vs +6h OR +6→7h taker flow is seller-dominant, HOLD original runner.
- Otherwise CUT at actual +7h open.

## Funnel
- candidates +6h **23** (D/V 14/9)
- recovery HOLD +7h **14**
- CUT7 **8**

## Result
- Parent: WR **47.48%**, PnL **$+63.60**, PF **1.14**, DD **$61.50**.
- Immediate CUT6: WR **44.60%**, PnL **$+82.70**, D/V **$+67.97 / $+14.73**.
- CONFIRM7: WR **47.48%**, PnL **$+75.25**, PF **1.17**, DD **$56.53**.
- delta vs parent **$+11.65**; D/V **$+4.59 / $+7.05**.
- CUT7 parent W/L **0/8**; loss→positive **0**; winner→nonpositive **0**.
- positive blocks **5/8**.

## Guardrail
Single natural state from SF5 forensic; no parameter sweep. Same-sample research; requires true-OOS trigger evidence before live.
