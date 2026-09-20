# BNB B35 — 1H Liquidity-Sweep LONG Timeframe Hypothesis Preregistration

**Scientific identity:** `BNB_B35_H1_SWEEP_LONG_V1`

## Why this is a new identity
B31-B33 tested causal structures completed on 15m bars with 5m entry triggers. B33 stopped further slicing of that 15m OHLC family but explicitly allowed a separately preregistered timeframe hypothesis.

B35 tests one focused hypothesis only:
> BNB's actionable LONG liquidity-sweep character may exist at the slower 1H auction scale, while the analogous 15m sweep is too noisy.

This is not a repair of any B33 detector and does not reuse B33 reference outcomes.

## Side
LONG only. No SHORT discovery is authorized in B35.

## Data
- BNBUSDT USD-M perpetual Binance Vision 5m OHLC.
- Raw warmup from 2021-11-01.
- Study window 2022-01-01 through 2026-08-26 00:00 UTC.
- Reuse the accepted B29-A1 raw identity guard.
- 1H bars are reconstructed from exactly 12 consecutive closed 5m bars ending at each UTC hour.
- 15m entry bars are reconstructed from exactly three consecutive closed 5m bars.

## S1 — frozen 1H structure
### Causal 1H swing low
A pivot low at hour `p` is a swing low iff its low is strictly below lows at p-2h, p-1h, p+1h and p+2h.
It becomes known only when p+2h closes.

### H1 `H1_SWING_LOW_SWEEP_RECLAIM_LONG`
At a fully closed 1H bar:
1. use only the latest swing low already confirmed before that hour;
2. current low < that swing-low price;
3. current close >= that swing-low price.

The structural level is the swept swing-low price.
Per-detector cooldown: 4 hours, keeping the first event.

### Structural viability
Before entry outcomes are evaluated, H1 must satisfy:
1. pooled N >= 100;
2. at least 4/5 calendar eras 2022-2026* have >=10 events;
3. max era share <=40%;
4. raw/A1 identity and bar-contiguity checks pass.

If S1 is not viable, B35 stops and S2 is not evaluated.

## S2 — frozen 15m entry grammar
Search from structure completion through +180m. All triggers use fully closed 15m bars.

- `E0_STRUCTURE_CLOSE`: entry at 1H structure completion close.
- `E1_NATIVE_LEVEL_RETEST`: first 15m bar with low <= swept level and close > level.
- `E2_STRUCTURE_HIGH_BREAK`: first 15m close > completed 1H structure high.
- `E3_PULLBACK_RECLAIM`: after at least one adverse 15m close-to-close move, first later close above the high of the most recent adverse 15m candle.
- `E4_STRUCTURE_MID_RETEST`: first 15m bar with low <= 1H midpoint and close > midpoint.

No clock, weekday, session, regime, volatility, indicator, funding or derivatives filter is allowed.

## Directional outcome only
No trading economics in B35.

For each filled entry:
- signed +60m return;
- signed +120m return — primary horizon;
- signed +240m return;
- hit iff signed return > 1e-12.

No TP/SL, MFE/MAE, fees, leverage, sizing, PnL, PF or DD.

## Split
- Development: 2022, 2023, 2024 structure events.
- Reference: 2025, 2026*, opened once only for the single frozen development entry winner.

## Development gate
An entry policy may be frozen only if:
1. filled N >= 100;
2. each development year N >=25;
3. participation >=25% of development structures;
4. pooled +120m hit >=55%;
5. Wilson 95% LCB >52%;
6. every development-year +120m hit >=52%;
7. median signed +120m >0;
8. at least one of +60m/+240m hit >=53%.

Ranking:
1. worst development-year +120 hit;
2. Wilson LCB;
3. pooled +120 hit;
4. participation;
5. lexical entry id.

Freeze at most one policy.

If none passes, reference remains unopened and B35 stops.

## One-shot reference gate
The frozen entry passes only if:
1. 2025 N >=30 and 2026 N >=20;
2. participation >=25%;
3. pooled +120m hit >=53%;
4. 2025 and 2026 each >50%;
5. Wilson 95% LCB >50%;
6. median signed +120m >0;
7. at least one of +60m/+240m hit >=52%.

Only a reference pass may advance to economics.

## Anti-rescue
- no pivot-width change;
- no 1H cooldown change;
- no added structure family;
- no added entry trigger;
- no clock/session/day filter;
- no lower gate;
- no reference inspection without a development winner;
- no economics after a directional reject.
