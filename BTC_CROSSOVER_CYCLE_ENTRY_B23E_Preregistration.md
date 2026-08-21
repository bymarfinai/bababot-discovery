# BTC Crossover-Cycle Entry B23E — Preregistration

## Purpose
Correct the remaining mismatch with the reference image. B23D treated every reappearance of STRONG_BULL after a temporary non-strong candle as a fresh entry opportunity. The reference image instead depicts an entry near the beginning of a new bullish MA cycle. B23E therefore permits at most one long entry per bullish EMA20/EMA50 cycle.

## Timeframe independence
Run four independent systems: 5m, 15m, 1h, 4h. Entry, monitoring, deterioration and exit are all evaluated only on the same timeframe. Higher-timeframe context is diagnostic only and does not manage the primary trade.

## Position model
$10 margin, 50x leverage, $500 notional. Gross PnL excludes fees/slippage/funding. Illustrative fee sensitivity: 0.08% round trip = $0.40/trade.

## Bull cycle
- BULL_CROSS occurs when EMA20 > EMA50 and previous EMA20 <= previous EMA50.
- The bull cycle remains armed until the next BEAR_CROSS where EMA20 < EMA50 and previous EMA20 >= previous EMA50.
- At most one entry may be taken in that bull cycle. If the position exits early, no re-entry is allowed until a complete bear cross and a subsequent new bull cross occur.

## Image-like STRONG_BULL
Same frozen definition as corrected B23D:
1. EMA20 > EMA50
2. EMA20 > EMA20 three bars ago
3. EMA50 > EMA50 three bars ago
4. normalized EMA20-EMA50 spread > spread three bars ago
5. close > EMA20

## Entry variants
Only these two event-based variants are tested; neither uses an arbitrary bar delay.

### C1_CROSS_ENTRY
On the BULL_CROSS candle, require close > EMA20 and EMA20 > previous EMA20. Enter at the next same-timeframe open. If those conditions are not met, skip that bull cycle for C1.

### C2_FIRST_STRONG_AFTER_CROSS
After BULL_CROSS, remain armed and wait causally for the first candle in that same bull cycle that satisfies STRONG_BULL. Enter at the next same-timeframe open. If BEAR_CROSS occurs first, skip the cycle.

## Dynamic same-timeframe management
Every completed candle after entry is classified as:
- STRONG_BULL: same five conditions above.
- HEALTHY_BULL: EMA20 > EMA50, EMA50 non-decreasing versus 3 bars ago, close >= EMA50, and not DETERIORATING/REVERSAL.
- DETERIORATING: EMA20 > EMA50, close >= EMA50, and at least two of: EMA20 <= prior EMA20; spread narrower than prior bar; close < EMA20.
- REVERSAL: close < EMA50 OR EMA20 < EMA50.

Management:
- STRONG_BULL -> HOLD
- HEALTHY_BULL -> HOLD
- DETERIORATING -> EXIT next same-timeframe open
- REVERSAL -> EXIT next same-timeframe open
- TRANSITION -> HOLD and reassess next candle

No fixed TP, fixed SL or fixed holding horizon.

## Development selection / validation
For each timeframe, compare C1 vs C2 in Development only. Eligible sample minimums: 5m >=100, 15m >=80, 1h >=30, 4h >=15. Select higher WR; if within 1 percentage point, select higher PF; if still tied, smaller absolute median loser. Freeze the selected variant and report External and Reference Validation unchanged.

## Gates
A high-precision clue requires BOTH External and Reference Validation to satisfy: N >=30 (5m/15m), >=20 (1h), >=10 (4h); WR >=80%; PF >=1.20; median loser > -0.30%; MAE <= -1.5% in <5% of trades.
A 90% WR claim requires WR >=90% in BOTH External and Reference Validation with the exact same selected rule.

Research only. Live BBC untouched.
