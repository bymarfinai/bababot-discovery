# Market Hunter MH1 — Cross-Sectional Derivatives Hunter Preregistration

**Status:** FROZEN BEFORE RESULT. Research-only; live BBC untouched.

## Novelty lock
MH0 tested price/volume/taker-OHLCV cross-sectional selection and failed. Existing derivatives work used Binance metrics for fixed-pair/temporal forensics, but the repository contains no same-timestamp broad-universe selector based on derivatives positioning. MH1 tests that distinct information set.

## Frozen universe and window
- End-exclusive: `2026-08-19T00:00:00Z`
- Primary history: 365 days; report 90d / 120d / 365d
- Symbols: first 24 symbols from the already-frozen MH0 universe, in original order: BTC, ETH, BNB, SOL, XRP, DOGE, ADA, LINK, AVAX, DOT, LTC, BCH, TRX, ETC, XLM, ATOM, UNI, AAVE, NEAR, FIL, APT, INJ, SUI, OP (all USDT perpetual)
- A symbol is eligible only when both causal 1h kline state and official Binance Data Vision metrics are available.
- Dynamic top-50% trailing-24h quote-volume liquidity screen at each decision timestamp.
- Minimum 8 liquid eligible symbols or no decision.

## Causal timing
At 1h bar close `T`, the just-completed 1h price bar is observable. Entry is at the next 1h open, also denoted decision availability time. Derivatives metrics use the latest metrics row with timestamp **strictly earlier than entry time**. No forward fill from future observations.

## Derivatives-only selector
Price returns are NOT used to choose MH1 direction. They are only used for liquidity eligibility, execution, and the momentum control.

Per eligible symbol, causal Binance metrics features are:
1. `top_vs_global = log(top-trader position long/short ratio) - log(global account long/short ratio)`
2. `top_pos_chg_1h = 1h change in log(top-trader position long/short ratio)`
3. `taker_log = log(taker long/short volume ratio)`
4. `crowd_contra = -log(global account long/short ratio)`
5. `oi_chg_1h = 1h change in log(open-interest value)` used only as conviction, not directional sign.

At every timestamp, each directional feature is cross-sectionally percentile-ranked and mapped to [-1,+1].

`direction_score = mean(rank(top_vs_global), rank(top_pos_chg_1h), rank(taker_log), rank(crowd_contra))`

`oi_weight = 0.5 + 0.5 * percentile_rank(abs(oi_chg_1h))`

`opportunity_score = abs(direction_score) * oi_weight`

Select exactly top-1 symbol. LONG if `direction_score >= 0`, otherwise SHORT. No confidence threshold.

## Controls
- **Momentum:** same liquid universe/timestamp; choose largest absolute completed 24h return, direction follows its sign.
- **Random:** deterministic seeded random symbol and direction from same liquid universe.

## Economics
- Reference notional: $500
- Round-trip modeled cost: 0.15%
- Primary independent outcome: signed close-to-entry return after 6h minus cost
- Secondary executable control: TP 1.3%, SL 1.3%, max hold 6h; next-open entry; adverse-first on same-hour dual touch
- Sequential portfolio: max one open position at a time.

## Frozen promotion gates
MH1 earns only `KEEP_FOR_STRICTER_VALIDATION` if ALL hold on 365d:
1. independent 6h net expectancy > 0;
2. sequential TP/SL expectancy > 0;
3. sequential PF > 1.05;
4. at least 3/4 chronological sequential blocks have positive PnL;
5. MH1 independent 6h expectancy beats both momentum and random controls;
6. median liquid eligible universe >= 8.

Otherwise verdict is `REJECT_MH1_LIVE_CANDIDATE`.

## Anti-overfit lock
No threshold sweep, no feature-weight tuning, no feature deletion, no alternative OI lookback, no TP/SL sweep, and no symbol cherry-picking after seeing MH1 results. A failed MH1 closes this exact derivatives-selector definition.