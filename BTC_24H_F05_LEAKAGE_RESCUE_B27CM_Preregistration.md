# B27CM — BTC 24H F05 BE/TIME Leakage Rescue Anatomy — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Diagnose the two dominant B27CL leakage families without changing live trade rules:
- `BE` / scratch exits;
- `TIME` exits that had **not** reached T10.

Question 1: if these trades had been given exactly one additional fixed 4-hour breath window after their actual B27CL exit, how many would later causally rebreak L and reach T5/T10 before a genuine close above H?

Question 2: which already-available causal state at the actual B27CL exit best distinguishes later T10 rescue from non-rescue?

B27CM is anatomy/counterfactual continuation analysis only. Trading WR/PF/PnL/expectancy are N/A and no B27CL rule is changed here.

## Frozen source
Source: `BTC_24H_F05_STATE_MACHINE_B27CL_Trades.csv`.
Use only filled trades in major partitions.
Expected filled identity:
- external 183
- development 297
- reference_validation 172
- pooled OOS 355
- pooled major 652.

Leakage cohorts are frozen as:
1. `BE`: `exit_ceiling_kind == BE`.
2. `TIME_OTHER`: `exit_ceiling_kind == TIME AND t10_reached == False`.

Expected exact leakage identity:
- BE: external 67 / development 107 / validation 61 / pooled OOS 128 / pooled major 235;
- TIME_OTHER: external 37 / development 55 / validation 39 / pooled OOS 76 / pooled major 131;
- combined leakage: external 104 / development 162 / validation 100 / pooled OOS 204 / pooled major 366.

No clock/regime/weekday exclusion.

## Frozen counterfactual breath window
For every leakage trade, preserve the original B27CL H/L/R4/F05/T5/T10 levels.

Counterfactual observation starts at the first raw 5m bar that is causally available after the actual exit:
- `CEILING_OPEN_EXIT` or `TIME_BLOCK_END_OPEN`: the exit occurs at the bar open, so the same raw 5m bar may be observed after that open;
- `CEILING_STOP`: exit timestamp is bar completion in B27CL, so observation begins on the next raw 5m bar;
- `TIME_FALLBACK_CLOSE`: observation begins at the next raw 5m bar after the fallback close.

The breath horizon is exactly **4 hours from actual exit timestamp**. No 1h/2h/8h sweep is permitted.

## Causal continuation chronology
The B27CL rebreak state is preserved causally:
- if `rebreak_confirmed == True` at the actual exit, the counterfactual begins already in the post-rebreak state and T5/T10 may be scanned from the first causally available post-exit bar;
- otherwise, first completed 5m close strictly `> H` terminates the counterfactual as `FUTURE_HIGH_BREAK`, while first completed 5m close strictly `< L` confirms `FUTURE_REBREAK`;
- for trades needing a fresh FUTURE_REBREAK, T5/T10 scanning starts only on the **next** raw 5m bar after that confirmation, matching B27CI chronology.

After the trade is in post-rebreak state:
- `low <= T5` marks future T5 reached;
- `low <= T10` marks future T10 reached;
- if a bar touches T5/T10 and later completes with `close > H`, the favorable touch counts because the High invalidation is only knowable at bar close;
- after a completed close `>H`, later bars cannot affect the outcome.

No SL, BE, runner, fee, or PnL is simulated in B27CM.

## Frozen causal candidate signals at actual exit
Only these five binary candidates may be evaluated; no post-hoc feature creation or combination is allowed:

1. `REBREAK_AT_EXIT` — B27CL had already confirmed Low rebreak before the actual exit.
2. `T5_AT_EXIT` — B27CL had already reached T5 before the actual exit.
3. `FAST_L_TOUCH_10M` — first strictly-post-fill bar with `low <= L` occurred within 10 minutes of fill and before the exit event.
4. `NO_F25_CLOSE_BEFORE_EXIT` — no causally completed 5m close at or above `F25 = L + 0.25*R4` was observed before the actual exit event. This reuses the B27CG persistence boundary only as a diagnostic signal; F25 is not a stop.
5. `LAST_CLOSE_LE_F05` — the last causally completed 5m close before the actual exit event was at or below F05.

For signal construction, the bar in which an intrabar ceiling stop occurred is excluded because its close was not known at the stop time. For open exits, the current bar is excluded because its close is not yet known.

## Frozen development selection
Select separately for `BE` and `TIME_OTHER` using development only.

For each leak family:
- compute the family's unconditional future-T10 rescue rate;
- for each candidate signal, require candidate N >=30 for BE and >=20 for TIME_OTHER;
- require future-T10 rescue-rate uplift >=10 percentage points versus that family's unconditional development rate;
- among eligible candidates, select the highest future-T10 rescue rate;
- tie-break by larger N, then fixed candidate order listed above;
- if none qualifies, select `NONE`.

No threshold tuning is allowed.

## Untouched OOS support
A development-selected signal is OOS-supported only if:
- external candidate N >=10 and validation candidate N >=10;
- external and validation each have future-T10 rescue rate strictly above their own leak-family baseline;
- pooled OOS uplift is >=7.5 percentage points.

External/reference_validation are confirmation only and cannot change the selected signal.

## Required reporting
Six untouched-OOS 4H clocks first, then major partitions/pools.

For BE, TIME_OTHER, and combined leakage report:
- leakage N;
- future rebreak N/rate;
- future T5 N/rate;
- future T10 N/rate;
- future High-break N/rate;
- no-resolution-by-4h N/rate;
- median minutes exit->future rebreak/T5/T10 where applicable.

Also report all five development candidate signals and the untouched OOS confirmation of the selected signal for BE and TIME_OTHER separately.

User-facing interpretation must also translate pooled OOS results to counts per 100 **original filled F05 entries**, while clearly labeling these as counterfactual rescue opportunities rather than realized wins.

## Verdict discipline
Per leak family:
- `SUPPORTED` only if a development signal is selected and passes the untouched OOS support rule;
- otherwise `NOT_SUPPORTED`.

Overall label:
- `B27CM_LEAKAGE_RESCUE_SIGNAL_SUPPORTED` if at least one leak family is SUPPORTED;
- otherwise `B27CM_LEAKAGE_RESCUE_SIGNAL_NOT_SUPPORTED`.

This experiment cannot claim a profitable strategy and cannot authorize an economic or live-rule change. Any use of a supported signal requires a new preregistered economics experiment.

Research only. Live BBC unchanged.
