# BNB B41-S5 — Entry Geometry Discovery Preregistration

## Objective

Select a causal execution geometry for the two B41-S4B REF-validated direction classes without changing the direction detector.

S5 is entry-only. It does not define stop loss, take profit, leverage, position sizing, PF, expectancy, or PnL.

## Frozen parent

B41-S4B signature:
`acab9ae7928bdcbebc3608a1f5818a6b5eaa6a4a782f446a2cc418e8e50adcbc`

Only these direction classes are eligible:

1. UPPER Q80 + TF05 C1_CLEAN_REJECTION -> SHORT
2. LOWER Q80 + TF60 C2_RECLAIM_AFTER_CLOSE -> LONG

All other Q80 interactions remain NO_TRADE.

## Frozen entry candidates

At detector close, define D = detector_close and W = Q80 wall.

- **E0_MARKET**: D
- **E1_R25**: D + 0.25*(W-D)
- **E2_R50**: D + 0.50*(W-D)
- **E3_WALL**: W

For SHORT, these are progressively higher/better sell prices toward the upper wall.
For LONG, these are progressively lower/better buy prices toward the lower wall.

No other retracement fraction may be searched in S5.

## Causal fill semantics

- E0_MARKET is filled at detector close.
- Limit orders become active only after detector close.
- A limit may fill on subsequent 5m bars for at most **60 minutes** after the signal.
- SHORT limit fills if a subsequent 5m high >= limit.
- LONG limit fills if a subsequent 5m low <= limit.
- Fill price is the frozen limit price.
- If not filled within 60m, candidate is MISS for that signal.
- No same-detector-bar fill is allowed.

## Fixed evaluation endpoint

All candidates are evaluated at the same absolute endpoint:
**detector timestamp + 180 minutes**.

This prevents a delayed limit fill from receiving a longer outcome horizon.

For filled candidates:
- aligned180 = direction-aligned movement from fill price to the fixed +180m close, normalized by wall distance;
- hit180 = aligned180 > 0;
- MFE/MAE are measured from fill until the fixed +180m endpoint;
- favorable dominance = MFE > MAE.

If the +180m endpoint is outside the same UTC session, that signal has no 180m outcome.

## Missed-winner diagnostic

A baseline winner is an E0_MARKET signal with aligned180 > 0.

For each limit candidate:
- missed_baseline_wins = baseline winners where that limit did not fill;
- missed_win_fraction = missed_baseline_wins / all baseline winners with valid 180m outcome.

This explicitly guards against improving apparent quality by simply refusing too many real winners.

## DEV-only limit nomination

E0_MARKET is the frozen baseline.

A limit candidate is **DEV_ELIGIBLE** only if, for that direction class:

- fill rate >= 70%;
- valid filled n180 >= 30;
- median aligned180 > E0_MARKET median aligned180;
- median MAE < E0_MARKET median MAE;
- hit180 >= E0_MARKET hit180 - 3 percentage points;
- missed_win_fraction <= 30%.

Nominate the **shallowest** eligible limit in this fixed order:
E1_R25 -> E2_R50 -> E3_WALL.

If no limit qualifies, nominate **E0_MARKET**.

## REF holdout validation

If a limit was nominated on DEV, it validates on REF only if:

- fill rate >= 60%;
- valid filled n180 >= 20;
- median aligned180 > E0_MARKET REF median aligned180;
- median MAE < E0_MARKET REF median MAE;
- hit180 >= E0_MARKET REF hit180 - 3 percentage points;
- missed_win_fraction <= 30%.

No alternate limit may be substituted after REF is observed.

If the nominated limit fails REF, final entry geometry falls back to E0_MARKET.

Because E0_MARKET is the causal entry origin already validated in S4B direction testing, market fallback is not a newly selected REF rule.

## S5 promotion

S5 is READY_FOR_S6 once each validated direction class has a frozen final entry geometry (validated DEV->REF limit or E0 market fallback).

## Explicit exclusions

No wall changes, direction changes, alternate timeframe, additional limit percentages, timeout search, stop, target, holding-period search, fees/slippage optimization, WR/PF/expectancy/PnL.
