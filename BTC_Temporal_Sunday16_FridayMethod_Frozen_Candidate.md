# BTC Sunday 16:00 WIB — FRIDAY-METHOD FROZEN CANDIDATE

**Freeze date:** 2026-08-19 WIB  
**Status:** FROZEN RESEARCH CANDIDATE FOR OOS / LIVE-PARITY VALIDATION — DO NOT RETUNE ON THE SAME 971-DAY SAMPLE  
**Live BBC:** untouched

Canonical checkpoint: `BTC_Temporal_Sunday_FridayMethod_SF6_SF8_Checkpoint.md`

## Frozen parent
- Symbol: BTCUSDT
- Temporal prior: every Sunday 16:00 WIB SELL
- Base TP: 2.50%
- Base SL: 1.40%
- Max hold: 18h
- $500 reference notional ($10 margin x 50)
- 0.15% round-trip fee
- historical funding using canonical Sunday exact-funding method
- adverse-first if TP and SL touch in the same 5m bar

## Frozen Friday-style failure-management layer
1. At +6h, only if the trade is still alive, mark FAILURE CANDIDATE when all are true:
   - cumulative favorable MFE < 0.5R, where R = 1.40% (therefore MFE < 0.70%);
   - current SELL close-progress <= 0;
   - latest completed 5m close >= EMA20;
   - more than 50% of completed 5m candles since entry are bullish/green.
2. Do NOT cut immediately. Wait until +7h if still alive.
3. At +7h HOLD the original parent runner if either:
   - latest completed close is lower than the +6h latest completed close; OR
   - aggregate taker imbalance from +6h to +7h is < 0 (seller-dominant).
4. Otherwise CUT at the actual +7h decision open.
5. Parent TP/SL/timeout has priority whenever it occurs before the management decision.
6. Completed bars only; no retrospective/look-ahead decisions.

## Frozen historical result
- Trades: 139
- Wins: 66
- WR: 47.48%
- Net PnL: **+$75.25**
- PF: **1.17**
- Max DD: **$56.53**
- Positive chronological blocks: 5/8
- +6h candidates: 23 (D 14 / V 9)
- +7h recovery HOLD: 14
- final CUT7: 8
- final CUT7 parent winners/losses: 0 / 8
- delta vs static parent: **+$11.65**
- discovery delta: **+$4.59**
- validation delta: **+$7.05**

## Guardrail
This is a same-sample research candidate. The Sunday history had already been inspected in prior research, so discovery/validation are robustness slices rather than untouched OOS. Future work may add new layers on top of this frozen baseline, but must not silently change the SF6-SF8 rule and still call it the frozen Friday-method candidate.
