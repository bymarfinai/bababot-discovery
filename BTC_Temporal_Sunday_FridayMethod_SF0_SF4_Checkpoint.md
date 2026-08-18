# Sunday Friday-Method — SF0 to SF4

**Status: COMPLETE — staged failure/repair/confirmation test; live BBC untouched.**

## Architecture
- Parent Sunday16 SELL / TP2.5 / SL1.4 / 18h.
- +2h WATCH: progress<=0 + close>=EMA20 + buyer taker-flow.
- +4h REPAIR: any favorable progress, close<EMA20, or seller-flow releases back to runner.
- +6h FAILURE: same 3 failure signs still agree.
- +7h CONFIRM: lower close vs +6h OR seller-flow => HOLD; otherwise CUT actual +7h open.

## Funnel
- WATCH +2h **29** (D/V 17/12)
- persistent +4h **10**
- candidate +6h **2**
- +7h recovery HOLD **1**
- final CUT7 **1**

## Economics
- Parent: WR **47.48%**, PnL **$+63.60**, PF **1.14**, DD **$61.50**.
- Immediate CUT6: WR **47.48%**, PnL **$+66.40**, D/V **$+55.92 / $+10.48**.
- Friday-style CONFIRM7: WR **47.48%**, PnL **$+63.77**, PF **1.14**, DD **$61.50**.
- CONFIRM7 delta vs parent **$+0.17**; D/V **$+0.00 / $+0.17**.
- final CUT7 parent W/L **0/1**; loss->positive **0**; winner->nonpositive **0**.
- positive chrono blocks **5/8**.

## Guardrail
Friday-style methodology adaptation only. Sunday history has prior research exposure, so D/V are robustness slices, not untouched OOS. Do not retune from August N=3.
