# B27DR — Generic F15 SHORT Clock-Rotation Scan — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Find whether the bearish continuation structure homologous to the London -> New York F85 LONG SAME_BAR_REJECTION has a stronger natural time habitat outside London -> New York.

This experiment changes **clock placement only**. It does not tune entry fraction, rejection rule, stop geometry, target extension, reference duration, execution duration, timeframe, fee, or sizing after seeing SHORT results.

The frozen bearish sequence is:

`Reference range -> first Low pressure visit (K1 OPP0) -> causal leave -> pre-H2 F15 touch -> SAME_BAR rejection close < F15 -> SHORT next 5m open -> return/arrival to Low (H2) -> continuation/extension below Low toward E20_DOWN`.

## Frozen market / data
- Instrument: Binance USD-M BTCUSDT perpetual.
- Raw event/execution clock: 5m.
- Same repository 5m source and frozen external / development / reference_validation / August partitions used by the F85 research lineage.
- Required raw 5m coverage: 100%.

## Frozen clock grid
Scan exactly 48 reference starts, every 30 minutes across one UTC day:

`00:00, 00:30, 01:00, ..., 23:30 UTC`.

For every clock:
- reference duration = **5h30m** (66 x 5m bars);
- execution duration = **6h30m** (78 x 5m bars);
- execution begins immediately when the reference range is complete;
- reference High/Low are frozen before execution begins;
- skip execution starts on Saturday/Sunday, matching the generic LONG clock scan convention.

The existing London -> New York control is reference start **08:00 UTC**, reference 08:00-13:30 UTC, execution 13:30-20:00 UTC.

No clock may be added, removed, shifted, or refined after result inspection.

## Frozen directional detector
For each completed reference range:
- `H = reference High`;
- `L = reference Low`;
- `R = H - L`, require `H > L`.

During the following execution window, before any strict close-break of either range edge:
- Low touch = `low <= L AND close >= L`;
- High touch = `high >= H AND close <= H`;
- consecutive qualifying bars at the same edge are one touch episode;
- SHORT K1 OPP0 = **first distinct Low visit while High visits are still zero**.

No future breakdown may be used to infer the signal.

## Causal leave and H2
After the K1 Low-touch episode:
- require one completed 5m bar that no longer qualifies as a Low touch;
- entry search begins only from the next 5m bar after that leave completes;
- H2 is the first later 5m bar whose `low <= L`, whether it merely retests L or immediately breaks below it;
- H2 is a structural milestone, not entry-eligible;
- opposite thesis break before H2 = first completed 5m `close > H`;
- if one terminal bar simultaneously reaches L and closes > H, classify ambiguous and do not use it for entry.

## Frozen F15 SAME_BAR_REJECTION entry
Exact short mirror geometry:
- `F15 = L + 0.15R`;
- `F65 = L + 0.65R`;
- `E20_DOWN = L - 0.20R`.

Entry sequence:
1. After causal leave, find the first F15 touch strictly before H2/opposite-break terminal bar.
2. The F15-touch bar itself must complete with `close < F15`.
3. If it does not close below F15, the setup is rejected; **no later-reject confirmation is allowed in B27DR**.
4. Entry = next raw 5m bar OPEN.
5. If next open `<= L`, H2 has effectively arrived at/open and entry is rejected as `MISSED_H2_AT_OPEN`.
6. Valid entry geometry requires `L < entry < F65`.

No F14/F16 sweep, no wick/body/EMA/ATR/volume filters, and no regime filter are allowed.

## Frozen fixed economics
To isolate clock habitat, use one fixed economic model for every clock:
- TP = exact `E20_DOWN = L - 0.20R`, resting target;
- invalidation = completed raw 5m `close > F65`;
- wick above F65 alone does not stop the trade;
- invalidation exits at that completed close price;
- if E20_DOWN target and close-invalidation occur on the same 5m bar, resting target receives priority;
- unresolved trade exits at the first 5m open at execution-window end;
- SHORT gross return = `(entry_px - exit_px) / entry_px`;
- illustrative notional = $500;
- round-trip fee = $0.40.

No runner is used in B27DR. This first scan asks only whether the same bearish entry structure has a better clock habitat.

## Mandatory London control parity
Before any rotated-clock result is interpreted, the generic detector at **08:00 UTC** must reproduce the persisted B27AD London -> New York SAME_BAR_REJECTION fixed-E20_DOWN control within frozen tolerances:
- external executed N = 25;
- development executed N = 25;
- reference_validation executed N = 12;
- August executed N = 1;
- pooled-major N = 62;
- pooled-major wins = 36;
- pooled-major WR = 36/62;
- pooled-major PF approximately 0.73 (tolerance +/-0.03);
- pooled-major expectancy approximately -$0.44 (tolerance +/-$0.03);
- pooled-major total approximately -$27.49 (tolerance +/-$0.15).

If London parity fails, abort before clock interpretation/persistence.

## Development selection gate
A non-London clock is a development candidate only if its **SAME_BAR_REJECTION fixed-E20_DOWN** development result satisfies all:
- executed N >= 25;
- WR >= 70%;
- PF >= 1.30;
- mean net expectancy/trade > 0.

If multiple clocks pass, select exactly one by the frozen ranking:
1. higher PF;
2. higher WR;
3. higher expectancy;
4. higher executed N;
5. earlier UTC clock as final deterministic tie-break.

The 08:00 UTC London control cannot be selected as the new clock.

## Historical replication label
Only after the single development clock has been selected, inspect reused historical partitions.

Call historical replication `SUPPORTED` only if the exact selected clock has:
- external: N >= 15, WR >= 65%, PF >= 1.20, positive expectancy;
- reference_validation: N >= 10, WR >= 65%, PF >= 1.20, positive expectancy.

Otherwise label `NOT SUPPORTED`.

These are reused historical partitions, not pristine unseen OOS.

## Structural reporting
For every clock/partition report at minimum:
- eligible days;
- K1 OPP0 count;
- clean causal-leave windows;
- F15 touches pre-H2;
- H2-after-F15-touch rate;
- SAME_BAR confirmations;
- executed trades;
- WR;
- PF;
- expectancy;
- total net;
- E20_DOWN TP rate;
- time-exit rate.

Persist one-row-per-day/clock case data and the development leaderboard.

## Decision labels
- `B27DR_NO_NEW_SHORT_CLOCK_CANDIDATE` if no non-London clock passes development gate.
- `B27DR_NEW_SHORT_CLOCK_DEV_CANDIDATE_NOT_REPLICATED` if one development clock is selected but fails historical replication.
- `B27DR_NEW_SHORT_CLOCK_HISTORICAL_REPLICATION_SUPPORTED` if the selected exact clock passes the frozen external + reference-validation replication rules.

## Guardrails
- This is a clock-habitat discovery scan, not live promotion.
- Do not modify live BBC code/configuration.
- Do not change LONG B27DQ/B27DK research artifacts.
- Do not optimize a runner, stop, target, entry fraction, or confirmation rule inside B27DR.
- Any follow-up refinement must receive a new preregistered experiment ID.

Research only; live BBC unchanged.
