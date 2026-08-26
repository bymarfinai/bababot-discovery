# ETH F85/F15 Transfer — M2 Pre-H2 Entry Grid

**Status: PREREGISTERED before result-bearing execution.**

## Purpose
Continue only the multi-clock ETH transfer lineage whose M1 K1 OPP0 structural replication passed all five habitats.

M2 asks one question only:

> After K1 OPP0 and a completed causal leave, which frozen range retrace levels can fill strictly before H2 while preserving high H2-arrival quality across external, development, and reference-validation partitions?

This is the direct B27W-style structural entry milestone. It is **not** an economic backtest.

## Frozen M1 habitats
LONG:
- ALT_0330
- RAW_0530
- LONDON
- RAW_2330

SHORT:
- SHORT_2000

No new clocks may be introduced.

## Frozen market structure
- Instrument: Binance USD-M ETHUSDT perpetual.
- Raw event clock: 5m.
- Reference duration: 5h30m = 66 bars.
- Execution duration: 6h30m = 78 bars.
- H = frozen reference high.
- L = frozen reference low.
- R = H-L.
- Weekday execution starts only.
- K1 OPP0, distinct visit semantics, strict break semantics, and causal leave are unchanged from ETH M1.

## LONG M2 sequence
`High K1 OPP0 -> contiguous High-touch episode -> completed causal leave -> pre-H2 retrace fill -> High H2 arrival`.

After leave, H2 is the first later raw 5m bar with `high >= H` regardless of close.
A completed `close < L` before H2 is opposite-break failure.
The H2/opposite terminal bar itself is never entry-eligible.

### LONG frozen grid
Measured from L=0 to H=1:
- F95 = L + 0.95R
- F90 = L + 0.90R
- F85 = L + 0.85R
- F80 = L + 0.80R
- F75 = L + 0.75R

A level fills when an eligible pre-H2 bar spans that exact level.

## SHORT M2 sequence
`Low K1 OPP0 -> contiguous Low-touch episode -> completed causal leave -> pre-H2 retrace fill -> Low H2 arrival`.

After leave, H2 is the first later raw 5m bar with `low <= L` regardless of close.
A completed `close > H` before H2 is opposite-break failure.
The terminal bar itself is never entry-eligible.

### SHORT exact-mirror grid
Mirror of LONG around the range midpoint:
- F05 = L + 0.05R
- F10 = L + 0.10R
- F15 = L + 0.15R
- F20 = L + 0.20R
- F25 = L + 0.25R

A level fills when an eligible pre-H2 bar spans that exact level.

## Entry eligibility chronology
- K1 episode must end with a completed non-touch bar.
- Entry search starts only on the **next raw 5m bar**.
- No fill is allowed on the causal-leave bar.
- No fill is allowed on the H2/opposite terminal bar.
- If no level fills before terminal/end, it is unfilled.
- No same-bar confirmation logic is added in M2.

## M2 outputs
For every habitat × level × partition and pooled-major:
- M1 K1 opportunities;
- clean causal-leave windows;
- clean-window H2 arrival rate;
- pre-H2 fills;
- fill rate among clean windows;
- H2 arrivals among fills;
- opposite breaks among fills;
- no-H2/end among fills;
- H2 hit rate among all fills;
- resolved H2 win rate;
- median minutes fill -> H2;
- median adverse excursion in range units before terminal;
- 10th percentile minimum post-fill fraction for LONG / 90th percentile maximum post-fill fraction for SHORT.

Persist one-row-per-window and one-row-per-level candidate audit files.

## Frozen discovery screen
A habitat × level gets `SCREEN_PASS` only if the exact same level satisfies in **each** major partition:
- >=30 pre-H2 fills; and
- >=70% H2 arrival among fills.

No pooled-only rescue is allowed.

## M2 interpretation
For each habitat:
- if exactly one level passes, it is the M2 structural winner;
- if multiple levels pass, report all passes and rank by fill count first, then H2 hit rate; do not tune between them yet;
- if no level passes, habitat fails M2 and is not advanced automatically.

M2 overall is descriptive across the five already-passed M1 habitats. It does not require all habitats to survive.

## Prohibited in M2
- TP/SL optimization;
- F35/F65 invalidation testing;
- E20/E20_DOWN targets;
- reclaim/rejection confirmation;
- next-open executable entry;
- runner logic;
- fees, leverage, PnL, PF, expectancy;
- clock filters or new habitat discovery.

## Mandatory assertions
1. K1 OPP0 identities are causal and use no future outcome.
2. Consecutive K1 bars remain one episode.
3. Entry eligibility begins only after a completed causal leave bar.
4. H2 is first later same-side boundary arrival after leave.
5. No fill occurs on leave or terminal bar.
6. Strict opposite break terminates before any later fill.
7. Every level equals its exact frozen range fraction.
8. LONG and SHORT grids are exact mirrors.
9. Raw 5m coverage must be >=99.5%.
10. No economic metric is used for selection.

**Research only. Stop after M2 result persistence.**
