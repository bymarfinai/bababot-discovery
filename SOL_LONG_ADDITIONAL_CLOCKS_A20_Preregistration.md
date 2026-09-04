# SOL LONG Additional Untouched Clocks — A20 Preregistration

## Objective
Continue Stage 12 after A17/A19 by testing whether SOL contains additional independent clock habitats beyond the supported 18:00 UTC and 03:00 UTC zones.

This is not an exit retune and not a rescan of already-tested clocks. Candidate clocks are derived mechanically from the pre-existing A1 Development anatomy atlas before any A20 economics are inspected.

## Frozen existing architecture
- Mature zone: R240 / 18:00 UTC, A2 parent + A4 REC_H2.
- Second supported zone: R420 / 03:00 UTC, A17 parent only.
- A18 H2 transfer to 03:00 remains rejected.
- A6/A8/A10/A11/A12/A14/A16 remain absent.
- H3/H4 recovery remains prohibited.
- Parent lifecycle remains A2 E0_RESTING_H -> E40.
- Cost stress remains frozen 5 bps convention.

## Candidate derivation from old A1 atlas
Use only A1 atlas cells satisfying all:
1. dominant visit H2,
2. topology_supported = true,
3. same dominant visit in >=4/6 Development half-year blocks,
4. dominant opportunity N >=100,
5. clock is not within 2 hours (circular UTC distance) of either supported habitat clock 18 or 03,
6. exact hours already economically tested in A17 (03, 08, 13) are excluded,
7. 18 is excluded as mature.

Rank remaining cells exactly by the frozen A17 anatomy rank:
1. same_dom_blocks descending,
2. dominant_min_block_conversion descending,
3. dominant_break_conversion descending,
4. dominant_median_extension_R descending,
5. dominant_opportunity_n descending,
6. ref_min ascending,
7. hour ascending.

Select at most four candidate cells, requiring candidate clocks to be >2 hours apart from one another. One frozen clock support and one frozen reference support are taken directly from the A1 topology fields using the same A17 ranking.

No candidate is selected using A20 PnL.

## Development economic gate
Each parent-only candidate must satisfy:
- N >=300,
- PF >1.15,
- 5bps PF >1.00,
- expectancy >0 raw and 5bps,
- net >0 raw and 5bps,
- >=4 adequate Development blocks,
- >=4/6 positive raw blocks,
- >=4/6 positive 5bps blocks.

If multiple pass, freeze one winner by:
1. 5bps net descending,
2. 5bps PF descending,
3. raw net descending,
4. N descending,
5. anatomy rank ascending.

## OOS gate
Only the frozen Development winner is opened OOS.

Required:
- exact candidate positive net, PF>1, 5bps net>0, 5bps PF>1 in both External and Reference Validation,
- clock support and reference support produce at least 3/4 positive raw cells and 3/4 positive 5bps cells.

No OOS retuning.

## Decision
- Pass => SOL_LONG_ADDITIONAL_CLOCKS_A20_SUPPORTED
- No Development winner => SOL_LONG_ADDITIONAL_CLOCKS_A20_REJECTED_DEVELOPMENT
- Development winner but OOS gate fails => SOL_LONG_ADDITIONAL_CLOCKS_A20_REJECTED_OOS

A20 does not authorize recovery transfer to a new clock. Any supported new parent habitat must test recovery separately.

Research only. Live Baba Bot remains unchanged.
