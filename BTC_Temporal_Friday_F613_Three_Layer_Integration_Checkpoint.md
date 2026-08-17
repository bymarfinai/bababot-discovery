# BTC Temporal Friday F6.13 — Three-Layer Loss Management Integration

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — **SAME-SAMPLE INTEGRATION PASS; PROVISIONAL**  
**Research only:** live BBC untouched.

## Frozen priority
No rule was retuned. Management priority is purely chronological:
1. **F6.12 FIB5** at +5m;
2. if no FIB5 action, **F6.9 EARLY10** at +10m;
3. if neither acted, **F6.5 TRUE FAILURE** at +60m;
4. otherwise preserve parent exit logic.

## Baselines
Parent Friday strategy:
- 138 trades
- WR **47.83%**
- PnL **+$64.630**
- PF **1.266**
- max DD **$56.530**

Existing F6.9 + F6.5 layering:
- PnL **+$90.683**
- improvement vs parent **+$26.052**
- PF **1.419**
- max DD **$39.317**

## Three-layer result
With F6.12 +5m added ahead of the existing layers:
- PnL **+$105.818**
- total improvement vs parent **+$41.188**
- incremental improvement vs F6.9+F6.5 **+$15.136**
- PF **1.525**
- max DD **$30.295**
- DD improvement vs parent **$26.235**
- WR remains **47.83%** because management reduces loss size rather than converting negative exits into positive trades.

Incremental contribution from adding FIB5:
- Discovery **+$2.215**
- Validation **+$12.920**

## Action interaction
Raw triggers:
- FIB5: **9**
- EARLY10: **10**
- F6.5 +60m: **6**

Active chronological layers after priority:
- FIB5: **9**
- EARLY10: **8**
- F6.5: **6**
- parent untouched: **115**

Overlap:
- FIB5 + EARLY10: **2**
- FIB5 + F6.5: **0**
- EARLY10 + F6.5: **0**
- all three: **0**

Thus the +5m Fib rule is mostly **complementary**, not a duplicate of F6.9.

For the two FIB5/EARLY10 overlap dates:
- 2026-03-06: +5m is better than +10m by **+$0.080**.
- 2026-05-15: +5m is worse than +10m by **-$0.082**.
- aggregate difference is essentially zero (**-$0.002**).

So the economic value of FIB5 comes mainly from **seven additional loser cases caught at +5m**, not from materially improving the two trades F6.9 would already catch.

## Interpretation
Friday's loss-management structure now has three distinct causal layers:

> **+5m:** shallow-Fib / expanded-range failed acceptance -> cut early  
> **+10m:** surviving no-reclaim + EMA/body failed acceptance -> cut  
> **+60m:** later FAILURE_60 + dominant upper wick -> cut late failure

This takes the same parent strategy from **+$64.630 to +$105.818** on the frozen historical sample while reducing max drawdown from **$56.530 to $30.295**.

## Guardrail
F6.12 was motivated from F6.11 same-sample Fib forensics, and F6.9 is also same-sample provisional. Therefore the three-layer stack is **not live-ready solely from this result**. Freeze all definitions and seek genuinely unseen Friday triggers; do not retune the Fib level, +5m timing, EMA/body conditions, +60m morphology, or parent TP/SL from the same 971-day sample.

## Execution
- workflow run: **32042941008** — success
- artifact: `f613-output`, ID **9292289578**
- script: `research/f613_friday_three_layer_integration.py`
- workflow commit: `078b06c2a4ea97c3f9ccce0f362330daa90fcd1a`
- live BBC untouched.
