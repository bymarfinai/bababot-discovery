# SUN1.8 — Sunday16 Previous-Day RUNNER + Persistent Failed-Development

**Status: COMPLETE — fixed causal architecture; same-sample diagnostic; live BBC untouched.**

## Fixed architecture
- RUNNER: Saturday return < 0 AND Sunday 00:00→16:00 return < 0. Frozen parent unchanged.
- WATCH: every other state.
- +4h arm only if completed path has SELL progress <= 0 AND EMA7 >= EMA20.
- +6h cut only if the same failure persists; exit at actual +6h open. Parent exits first have priority.
- No threshold/timing/EMA sweep.

## Baseline
- N 139, WR **47.48%**, PnL **$+63.60**, PF **1.14**, DD $61.50.

## Pre-entry state decomposition
- RUNNER: N **23**, WR **82.61%**, PnL **$+140.07**, PF **6.51**.
- WATCH: N **116**, WR **40.52%**, PnL **$-76.48**, PF **0.82**.
- RUNNER D/V: N 14/9; PnL $+71.34/$+68.73; WR 78.6%/88.9%.

## +4h→+6h failed-development actions in WATCH
- +4h armed: 53 (D/V 35/18).
- +6h actions: **24** (D/V 17/7), parent W/L **6/18**.
- Incremental: **$-3.79** (D $-23.70, V $+19.91).
- Loss savings $+59.40; winner damage $-63.19; positive→nonpositive 6.

## Combined adaptive result
- N 139, WR **43.17%**, PnL **$+59.81**, PF **1.14**, DD $54.54, loss streak 7.
- D: WR 42.17%, PnL $+30.20, PF 1.12.
- V: WR 44.64%, PnL $+29.60, PF 1.18.

## Diagnostics
- If same +4→+6 rule were applied to ALL trades: full PnL $+49.15, delta $-14.45.
- RUNNER-only / WATCH-skip is capacity only, not recommended as final frequency architecture.

## Guardrail
Same-sample architecture test. Previous-day state came from SUN1.7 forensic inspection, so positive economics are diagnostic, not untouched OOS validation.
