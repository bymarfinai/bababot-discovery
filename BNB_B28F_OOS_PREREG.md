# BNB B28F — Frozen OOS Validation Preregistration

## Frozen candidate
- BNBUSDT LONG only
- habitat: **05:00–06:00 WIB**
- UTC anchors: **22:00, 22:15, 22:30, 22:45**
- character: **DRIVE_DOWN__STR_B60_80**
- lookback: **120 minutes**
- hold: **720 minutes**
- notional: **$500**
- cost: **$0.75/trade**
- selected only from Development 2022-01-01 through 2024-12-31

No parameter above may change after OOS is viewed.

## Unseen data
Primary OOS is `external` (2020-01-01..<2022-01-01) + `reference_validation` (2025-01-01..<2026-07-30) from the frozen Binance Vision 5m loader. August 2026 is shadow-only and cannot change the decision.

## Anti-leak
No OOS search, parameter tuning, clock shift, candidate substitution, family rescue, or comparison-driven retuning. Feature lookback and exit must stay inside each evaluated partition. Tooling repairs may only restore this exact preregistered calculation.

## Frozen gates
A. Data: coverage >=99.5%, no duplicate `(entry_ts, clock)`.

B. Each primary partition independently: trades>=40, WR>=52%, net>0, expectancy>0, PF>=1.05.

C. Pooled primary OOS: trades>=160, WR>=55%, net>0, expectancy>=+$0.50/trade, PF>=1.20, max DD<=$125, max loss streak<=8.

D. Pooled anchor stability: each anchor evaluable at >=40 trades; supportive requires WR>=52%, net>0, exp>0, PF>=1.05, DD<=125, loss streak<=10. Require >=3 evaluable and >=3 supportive anchors.

## Decision
PASS only if A+B+C+D all pass. Sound data plus any gate failure = FUNDAMENTAL OOS REJECT. Data/tooling failure is separate. PASS advances to Trade Construction. A rejection freezes B28F as rejected and forbids tuning. No live orders are part of validation.
