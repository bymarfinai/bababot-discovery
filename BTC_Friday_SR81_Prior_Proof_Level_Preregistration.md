# BTC Friday SR81 — Prior-Proof Support/Resistance Preregistration

**FROZEN BEFORE RESULT. Research-only; live BBC untouched.**

## Objective
Test a deterministic support/resistance hypothesis that is independent of SR80's fitted tree:

> A Friday level is high-confidence only when the same numerical level has already produced at least two clean same-side reactions during the prior seven days and zero resolved same-side breaks.

The target remains level correctness, not trading PnL.

## Friday candidate levels
Use the exact frozen SR80 level universe and construction:
- PDH / PDL
- prior-7-WIB-day high / low
- up to 3 most recent confirmed 1H swing highs / lows from prior 7 days
- confirmed pivot span = 3 completed 1H bars each side
- cluster raw levels within 0.10 x Friday-start Wilder ATR14(1H)
- cluster price = median member price
- Friday-start side: below open = SUPPORT; above open = RESISTANCE
- candidates frozen at Friday 00:00 WIB

## Historical proof window
For each Friday-frozen cluster, inspect only completed BTCUSDT 5m history from Friday-start minus 7 days up to Friday-start.

Historical interaction uses the CURRENT frozen cluster price, which is fully known at Friday start. The historical test does not imply the level was traded previously; it only asks whether the price area had repeatedly behaved as the same support/resistance before the current Friday.

### Same-side prior touch
At a candidate prior touch time `t`, use the most recent completed 1H Wilder ATR14 available strictly before `t`.

A prior touch is eligible only if:
- the 5m candle range contains the frozen level price; and
- the immediately previous completed 5m close is at least `0.10 x touch-time ATR` on the correct approach side:
  - Friday SUPPORT candidate: previous close > level + 0.10 ATR
  - Friday RESISTANCE candidate: previous close < level - 0.10 ATR

This prevents repeated bars sitting on a level from being counted as separate proof events.

### Prior touch outcome
Use the same symmetric reaction concept as SR80, scaled by touch-time ATR:
- reaction distance = 0.50 ATR
- horizon = 6 hours after touch
- SUPPORT HOLD: +0.50 ATR before -0.50 ATR
- RESISTANCE HOLD: -0.50 ATR before +0.50 ATR
- opposite boundary first = BREAK
- touch candle reaching either boundary = AMBIGUOUS
- later candle hitting both boundaries = AMBIGUOUS
- neither in 6h = UNRESOLVED

After an eligible prior touch is detected, scanning for the next proof event resumes only after that touch's 6-hour evaluation window. Thus one reaction episode cannot create multiple proof counts.

## Exact high-confidence rule
A frozen Friday level is `PRIOR_PROVEN` iff, before Friday starts:
- resolved same-side prior proof events >= 2
- HOLD count == resolved count
- BREAK count == 0

There is NO alternative threshold and no ranking among qualifying levels.

## Friday outcome
For every PRIOR_PROVEN frozen level that is first touched during Friday, use the exact SR80 Friday correctness label:
- scale = Friday-start Wilder ATR14(1H)
- reaction = 0.50 ATR
- horizon = 6h after first Friday touch
- same ambiguity/unresolved exclusions
- primary correctness = HOLD / (HOLD + BREAK)

## Evaluation
Keep the exact SR80 chronological Friday split:
- first 70% Friday dates = discovery
- last 30% = validation

Because SR80 already inspected aggregate level outcomes on this historical window, SR81 is an independent deterministic follow-up but NOT pristine untouched history. No parameters may be chosen from SR81 outcomes.

Promotion to `BTC_FRIDAY_SR81_PRIOR_PROOF_80_CANDIDATE` requires ALL:
1. discovery resolved N >= 20 and HOLD rate >=80%
2. validation resolved N >= 10 and HOLD rate >=80%
3. full resolved N >= 30 and HOLD rate >=80%
4. validation rate > unconditional SR80 validation baseline of 60.00%
5. at least 3/4 chronological blocks containing >=5 resolved PRIOR_PROVEN levels have HOLD rate >50%
6. zero causality/integrity violations

Support and resistance performance are reported descriptively, but neither side may be used as a post-result rescue if combined SR81 fails.

Report Wilson 95% intervals for all primary rates.

## Guardrails
- no change to 2 prior holds / zero breaks
- no 3-touch, 1-touch, weighted-touch, recency, source-family, hour, or support/resistance-only rescue after result
- no change to 0.10 ATR approach separation, 0.50 ATR reaction, 6h horizon, pivot span or clustering
- no PnL/TP/SL optimization
- if SR81 passes, freeze exact rule and transfer unchanged to other pairs before any live use
- observed historical 80% is never a guarantee of future support/resistance behavior
