# B27AD — BTC London -> New York SHORT Exact Mirror — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Test whether the existing BTC London -> New York LONG liquidity mechanism has a causal SHORT mirror without tuning any threshold to improve results.

The frozen sequence is:

`Touch Low #1 -> causal leave -> pre-H2 short entry -> Touch Low #2 (H2 milestone) -> strict breakdown/extension below London Low -> E20 milestone -> profit-lock runner`.

B27AD is research only. Live BBC is unchanged.

## Frozen source and detector
- Instrument: Binance USD-M BTCUSDT perpetual.
- Raw event/execution clock: 5m.
- Transition: `LONDON_TO_NEWYORK` only.
- Previous London High/Low are frozen before New York.
- Source signals: exact B27Q `SHORT`, `K1`, `OPP0` (`opp_visits_at_signal == 0`).
- Low touch: `low <= L` and `close >= L`.
- Consecutive qualifying bars are one touch episode.
- K1 is Touch Low #1.
- No signal is inferred from future breakdown.

## Causal leave and H2
After the K1 low-touch episode:
- require one completed 5m bar that no longer qualifies as a Low touch;
- entry eligibility begins only at the next 5m bar open;
- H2 is the first later 5m bar with `low <= L`, regardless of whether that bar also closes below L;
- H2 is a milestone, not TP;
- opposite thesis break before H2 is first completed 5m `close > H`;
- if the same bar both reaches L and closes > H, mark `AMBIGUOUS_H2_VS_OPPOSITE_BREAK` and do not use that terminal bar as an entry fill.

## Exact mirror geometry
Let `R = H - L` and `F(f) = L + f*R`.

Long parameter -> frozen short mirror:
- LONG F85 entry -> SHORT **F15** entry (`L + 0.15R`).
- LONG F35 close-invalidation -> SHORT **F65** close-invalidation (`L + 0.65R`).
- LONG E20 target above H -> SHORT **E20_DOWN** = `L - 0.20R`.

No F14/F16, no stop sweep, no target sweep.

## Entry variants
### BLIND_F15
After causal leave, a resting F15 order may fill only strictly before the H2/opposite-break terminal bar.

### EARLY_REJECT
Using the exact BLIND_F15 opportunity identity:
- F15 must first be touched pre-H2;
- earliest completed 5m `close < F15` confirms rejection;
- enter at the next 5m open if the open is still strictly above L and below F65;
- if the next open is `<= L`, H2 has already arrived at/open before a valid short entry and the trade is skipped.

### SAME_BAR_REJECTION
Diagnostic subset only:
- the original F15-touch bar itself must close `< F15`;
- entry is next 5m open under the same geometry.

`EARLY_REJECT` is primary; `BLIND_F15` and `SAME_BAR_REJECTION` are diagnostics.

## Fixed E20_DOWN baseline
For every executed entry:
- TP = `L - 0.20R`;
- invalidation boundary = F65;
- wick above F65 does not stop the trade;
- stop only on completed raw 5m `close > F65`, exiting at that actual close;
- a resting E20_DOWN target hit is resolved before a same-bar close-based invalidation;
- unresolved trades exit at the 20:00 UTC session-end 5m open.

Short gross return is `(entry_px - exit_px) / entry_px`.
Illustrative notional = $500; completed-trade fee = $0.40.

## E20_DOWN profit-lock hybrid
This is the exact directional mirror of B27AC.

Before E20_DOWN is reached:
- no upper/lower fixed TP order is assumed in the hybrid simulation;
- F65 completed-close invalidation remains active;
- E20_DOWN is reached on first raw 5m `low <= E20_DOWN`.

When an E20_DOWN-reaching bar completes without F65 close invalidation:
- E20_DOWN becomes a hard **profit ceiling** effective from the next 5m bar;
- activation bar cannot be retroactively exited at E20_DOWN;
- on a later bar, if `open >= active_ceiling`, exit at actual open;
- otherwise if `high >= active_ceiling`, exit at the active ceiling.

Structural ratchet:
- strict 3-bar pivot HIGH centered on bar `i-1` is confirmed only when bar `i` completes and requires `high[i-1] > high[i-2] AND high[i-1] > high[i]`;
- if a newly confirmed pivot high is below the current active ceiling, ratchet the ceiling downward;
- a newly confirmed ceiling is effective only from the next bar;
- ceiling can never move upward.

If price keeps falling and never retraces into the active ceiling, the position remains open until a lower confirmed ceiling is hit or session end.

## Frozen structural screen
For BLIND_F15, the exact mirror of B27W structural screen requires in each major partition:
- >=30 F15 fills; and
- >=70% H2 arrival among fills.

This is structural only, not economic WR.

## Reporting
For each partition and pooled major partitions report:
- K1 opportunities, clean windows, F15 fills, H2 hit rate and median minutes to H2;
- executed counts for BLIND_F15 / EARLY_REJECT / SAME_BAR_REJECTION;
- fixed E20_DOWN WR, PF, expectancy, total net;
- hybrid WR, PF, expectancy, total net and delta;
- E20 reach, exit reason counts, peak extension below L, realized exit extension, capture/giveback diagnostics.

## Audit requirements
Execution must abort before persistence if any fail:
1. B27Q SHORT K1 OPP0 signal bar reproduces as a Low touch.
2. Consecutive K1 touch bars remain one episode.
3. Leave must complete before entry eligibility.
4. No BLIND_F15 fill may occur on H2/opposite terminal bar.
5. H2 is first later `low <= L` and is never treated as TP.
6. F15/F65/E20_DOWN prices equal the frozen range formulas exactly.
7. EARLY_REJECT confirmation is strictly causal and entry is next-open.
8. Same-bar subset is a subset of EARLY_REJECT opportunities.
9. Hybrid E20 ceiling cannot affect the E20-touch bar retroactively.
10. Structural pivot high cannot affect its own confirmation bar.
11. Hybrid ceiling never rises.
12. Raw 5m source coverage must be 100%.

No live BBC modification is authorized by this experiment.