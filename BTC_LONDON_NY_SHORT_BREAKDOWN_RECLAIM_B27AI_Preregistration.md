# B27AI — BTC London -> New York SHORT Breakdown-Reclaim Exit — Preregistration

## Purpose
Build a SHORT-specific all-regime execution rule without imposing the LONG E20/hybrid exit. The frozen SHORT entry universe remains B27AD; 4H BULL/BEAR/SIDEWAYS is diagnostic only and never blocks a trade.

## Frozen cohort and entry
- Instrument/data/partitions/session semantics: unchanged from B27AD.
- Primary entry: `EARLY_REJECT` exactly as B27AD.
- Diagnostics: `BLIND_F15` and `SAME_BAR_REJECTION` exactly as B27AD.
- No change to K1 OPP0 detector, F15, F65, causal leave, H2 timing, confirmation timing, fee, notional, or session-end exit.
- Existing B27AD entry identities and fixed/hybrid baseline economics must reproduce before B27AI is interpreted.

## SHORT-specific exit hypothesis
The hypothesis is that downside continuation should be managed by acceptance/failure of the frozen London Low rather than by mirroring the LONG E20 profit-floor runner.

For every executed short:
1. Before breakdown acceptance, completed 5m `close > F65` remains the invalidation; exit at that completed close, exactly as B27AD.
2. H2 remains a milestone only; it is not an exit.
3. Breakdown acceptance occurs at the first completed 5m bar with strict `close < L` after entry.
4. There is no fixed TP after acceptance.
5. After breakdown acceptance, hold the full position while completed 5m closes remain `< L`.
6. Exit at the first completed 5m `close >= L`; exit at that actual completed close and label `BREAKDOWN_RECLAIM_L`.
7. If no exit occurs before New York session end, exit at the first 5m open at 20:00 UTC as in B27AD.
8. `E20_DOWN = L - 0.20R` is diagnostic only; it never triggers an exit.

This rule contains no new numeric threshold.

## Diagnostics
Report by partition and pooled-major:
- N, WR, PF, expectancy/trade, total PnL;
- breakdown-acceptance rate;
- E20 diagnostic reach rate;
- pre-acceptance invalidations, Low-reclaim exits, time exits;
- median maximum downside extension below L among accepted trades;
- median realized exit extension relative to L;
- median capture ratio and giveback from trough;
- comparison versus the frozen B27AD fixed-E20 and hybrid results.

## Frozen support gate
Primary `EARLY_REJECT` is `B27AI_SUPPORTED` only if:
- pooled-major expectancy > 0;
- pooled-major PF >= 1.20;
- pooled-major total PnL exceeds both the frozen B27AD fixed-E20 total and frozen B27AD hybrid total;
- each of external, development, and reference-validation has expectancy >= 0 and PF >= 1.00.

Reference-validation has only 22 frozen primary trades and remains a stated sample-size limitation regardless of outcome.

## Prohibited rescue
After results are visible, do not change F15/F65, add a buffer around L, require multiple closes, add EMA/ATR/volume/regime filters, change timeframe, add a fixed target, or tune session timing inside B27AI.

Research only. Live BBC remains unchanged.