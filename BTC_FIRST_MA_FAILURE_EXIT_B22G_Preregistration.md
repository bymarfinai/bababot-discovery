# BTC First-MA-Failure Exit B22G — Preregistration

Status: **PREREGISTERED**  
Date: 2026-08-21

## Question
For a valid bullish EMA20/EMA50 pullback-reclaim entry, what is the actual trade win rate if the position is monitored candle-by-candle and exited at the **first** completed candle that shows MA-structure reversal? This directly separates trade WR from B22F survival statistics.

## Data / partitions
Same Binance BTCUSDT USD-M 5m source and frozen partitions as B22B–B22F. Higher-TF states are causally shifted to their close availability.

## Entries
Primary entry only: `PULLBACK_RECLAIM`, frozen from B22B:
- entry TF STRONG is ON;
- preceding candle reaches the EMA20/EMA50 zone without closing below EMA50;
- current candle is bullish and closes above EMA20;
- execute next entry-TF open.

Entry TFs:
- 5m, grouped by causally known 1h state: STRONG_BEAR / NEUTRAL / STRONG_BULL;
- 1h, grouped by causally known 4h state: STRONG_BEAR / NEUTRAL / STRONG_BULL.

## Exit variants
Every completed entry-TF candle after execution is inspected starting with candle 1. No fixed bar cutoff.

- `FIRST_SOFT_FAILURE`: first candle where close < EMA20 AND EMA20 < prior EMA20 AND bullish EMA20-EMA50 spread < prior spread. Execute next entry-TF open.
- `FIRST_HARD_FAILURE`: first candle where close < EMA50 OR EMA20 < EMA50. Execute next entry-TF open.

If no failure occurs before partition end, force-close at the final available open and mark it censored/partition close.

Only one position per `(entry_tf, higher_state, exit_variant)` is open at a time. No fixed TP/SL, fees, or slippage.

## Outputs
For every partition/state/exit variant report N, WR (exit return > 0), PF, mean/median return, median MFE/MAE, median bars held, and max losing streak.

This is descriptive research only. No promotion gate and no live BBC change.
