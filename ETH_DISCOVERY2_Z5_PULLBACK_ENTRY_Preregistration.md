# ETH Discovery 2 — Z5 Breakout Pullback Entry Geometry Preregistration

**PREREGISTERED before result-bearing execution.**

## Purpose
Restart ETH discovery from the frozen ETH-native Z1→Z4 lineage without relaxing or rescuing the failed Z4 replication gate.

Z4 selected NEXT_OPEN on Development, but the selected candidate failed historical replication because External F90 C10 post-entry reach was 54.3% versus a frozen 55% gate. Z4 also showed that NEXT_OPEN median entry was already around 1.04R above L, while early checkpoints can be marked ALREADY_PASSED_AT_ENTRY. Therefore Z5 does not reinterpret Z4 as a win and does not loosen any Z4 gate.

Z5 asks a new pair-native execution question:

> After a valid ETH-native B00 breakout, can a shallow resting pullback limit improve entry geometry while preserving enough continuation to justify later economic testing?

No TP, SL, fees, leverage, sizing, PnL, PF, or live promotion in Z5.

## Frozen lineage
- ETHUSDT Binance Futures raw 5m, coverage >=99.5%.
- Reference 11:30-17:00 UTC = 18:30-00:00 WIB.
- Execution 17:00-23:30 UTC = 00:00-06:30 WIB.
- LONG only.
- Same external / development / reference_validation partitions.
- H=max(reference high), L=min(reference low), R=H-L.
- Reuse Z2 K1/OPP0, contiguous touch, causal leave, F95/F90 shallow retest.
- B00 = first completed 5m close strictly above H after the completed retest.
- B00 is known only at its close.

## Frozen entry family
`NEXT_OPEN` is the non-selectable control.

Three selectable resting buy-limit modes are fixed before execution:
- `L02`: H + 0.02R
- `L04`: H + 0.04R
- `L06`: H + 0.06R

Order semantics:
1. The limit becomes active only after B00 completes.
2. It may first execute on the immediately following raw 5m bar.
3. The order remains active for a maximum of 30 minutes (6 raw 5m bars), and never beyond execution_end.
4. If a bar opens at or below the limit, fill at that bar open (price improvement).
5. Otherwise, if that bar trades low <= limit, fill exactly at the limit.
6. If a completed close < L is observed before a fill, cancel from the next bar onward.
7. If a limit fills intrabar and the same bar later closes < L, the fill remains valid; post-entry structural evaluation begins on the next raw bar to avoid intrabar ordering ambiguity.
8. No fill on the B00 bar.

This family is intentionally narrow. No additional levels, wait windows, retest definitions, or post-hoc interpolation may be introduced after results are seen.

## Structural diagnostics
For every available entry measure:
- participation among B00 cases;
- entry fraction `(entry-L)/R`;
- price improvement versus NEXT_OPEN for the same session;
- MFE and MAE from permitted post-entry evaluation;
- adverse excursion in R;
- first post-entry reach of:
  - C20 = H+0.20R
  - C30 = H+0.30R
  - C40 = H+0.40R
- completed close < L before C20;
- unresolved cases.

C20/C30/C40 are diagnostics, not TP candidates.

## Development-only candidate gate
A limit mode is a Development candidate only if BOTH F95 and F90 independently satisfy:
- >=30 available entries;
- participation >=50%;
- median entry fraction <= the corresponding NEXT_OPEN control median;
- C20 post-entry reach >=55%;
- C30 post-entry reach >=40%;
- C20 reaches > close<L-before-C20 failures.

Among candidate modes select lexicographically:
1. highest minimum C30 reach across F95/F90;
2. highest minimum C20 reach;
3. lowest worst median entry fraction;
4. highest minimum participation;
5. shallower level tie priority: L02, L04, L06.

## Historical replication
The selected Development mode is SUPPORTED only if External and Reference Validation, for BOTH F95/F90 independently, satisfy:
- >=18 available entries;
- participation >=40%;
- median entry fraction <= corresponding NEXT_OPEN control median;
- C20 reach >=50%;
- C30 reach >=35%;
- C20 reaches > close<L-before-C20 failures.

No pooled rescue. No switching the selected level after holdout inspection. No gate relaxation.

## Assertions
- F90 sessions remain a subset of F95.
- Every source B00 occurs strictly after the completed retest and has close > H.
- No limit is active on B00.
- All candidate fills are causal and strictly before execution_end.
- Limit fill price is never above the fixed limit.
- Same-session price improvement is computed only when both candidate and control exist.
- Selection reads Development only.
- Historical replication cannot alter the selected candidate.
- No economic output is produced.

## Scientific boundary
A SUPPORTED Z5 result only authorizes a separate preregistered economics milestone. It does not itself authorize live trading.

Research/shadow only.
