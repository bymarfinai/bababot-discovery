# B27R — London -> New York LONG Entry Optimization — Preregistration

## Purpose
Optimize entry price/timing only after the audited B27Q liquidity-pressure signal is already known.

B27Q market-structure logic is frozen and MUST NOT be changed in this experiment.

Primary cohort is frozen before results:
- transition: `LONDON_TO_NEWYORK`
- side: `LONG`
- pressure threshold: `K1` = first distinct visit to the completed London High
- purity: `OPP0` = zero visits to completed London Low at signal time

This cohort is chosen because B27Q already showed a large and directionally consistent structural sample. B27R does not re-select direction, session, or touch definition.

Secondary diagnostic cohort:
- same transition / side / purity
- `K2` = second distinct High visit

K2 is reported separately and cannot replace the primary cohort based on B27R results.

## Frozen upstream signal contract
Read the persisted B27Q signal atlas. Do not reconstruct or retune it.

For every signal:
- previous-session High/Low are the completed London High/Low frozen by B27Q;
- exact 5m distinct-touch chronology is inherited from B27Q;
- signal time is completion of the 5m bar that created the qualifying High visit;
- no signal exists after a strict range breakout;
- `OPP0` means `opp_visits_at_signal == 0`.

B27Q files remain the source of truth for signal identity.

## Frozen exit contract
For all B27R entry methods:
- LONG only;
- TP = frozen previous-session High `H`;
- SL = frozen previous-session Low `L`;
- no trailing stop, partial, breakeven move, extension target, or management filter;
- unresolved positions exit at the first available 5m open at/after New York session end;
- notional = $500;
- round-trip fee = $0.40.

Thus B27R isolates entry mechanics only.

## Entry methods
All entries become eligible strictly after signal-bar completion. No same-signal-bar fill is allowed.

### 1. NEXT_OPEN
Market entry at the open of the first 5m bar whose start equals `signal_ts`.

The open must be inside the frozen range `[L, H]`; otherwise the candidate is marked invalid rather than repaired.

Because entry occurs at the known bar open, target-only or stop-only touches inside that entry bar are valid. If TP and SL are both touched in the same 5m bar, score conservative SL.

### 2. Frozen range-fraction limit grid
For LONG, define `entry = L + f*(H-L)`.

Predeclared fractions:
- `F50`: f = 0.50
- `F55`: f = 0.55
- `F60`: f = 0.60
- `F65`: f = 0.65
- `F70`: f = 0.70
- `F75`: f = 0.75
- `F80`: f = 0.80

This deliberately densifies the unexplored zone between B27Q midpoint (0.50) and shallow (0.75), while retaining the B27Q anchors.

Limit eligibility begins with the first 5m bar starting at `signal_ts`.
Before fill, any strict 5m close above H or below L cancels the order (`RANGE_BROKE_BEFORE_FILL`).
If a limit fills, fill-bar ordering is unknown: if SL is touched anywhere in the fill bar score conservative SL; target-only touch in the fill bar is not awarded. From the next 5m bar onward, first barrier touch resolves; same-bar TP+SL = conservative SL.

### 3. Local signal-bar limit methods
Use only the already completed B27Q signal bar:
- `SIG_MID`: midpoint of signal-bar High and Low.
- `SIG_LOW`: signal-bar Low.

A local entry is valid only if its planned price lies strictly inside or on `[L, H]`; otherwise mark invalid. No clipping to the range is allowed.

The same post-signal eligibility, pre-fill range-break cancellation, and conservative fill-bar ordering as the fraction limits apply.

## Primary selection rule
Entry-method selection uses ONLY `external` + `development` for the primary K1/OPP0 cohort.

A method is `DEV_ELIGIBLE` only if in BOTH external and development:
- at least 20 filled/resolved trades;
- positive net expectancy after fee;
- net PF >= 1.10.

Among eligible methods, select exactly one frozen candidate by:
1. highest `min(PF_external, PF_development)`;
2. tie-break: highest pooled external+development net expectancy;
3. tie-break: higher minimum fill count.

If no method is eligible, B27R has no selected candidate.

## Reference-validation check
The selected method, if any, is then read on `reference_validation` without reselection.

Call it `REFERENCE_PASS` only if:
- >= 15 filled/resolved trades;
- positive net expectancy after fee;
- net PF >= 1.20.

Important: this is not pristine independent OOS because prior research has already inspected this historical era. It is a frozen reference-validation check only, not live promotion evidence.

August is telemetry only and never influences selection.

## Secondary K2 diagnostic
Report the same entry methods for K2/OPP0 across all partitions, but:
- do not select a K2 champion;
- do not compare K2 against K1 to replace the primary rule;
- treat small-N results as diagnostic only.

## Required outputs
Persist:
1. all candidate trades;
2. summary by partition / K / method;
3. primary selection table with eligibility components;
4. selected-method reference-validation result;
5. audit status and invalid/cancel/no-fill counts.

Metrics:
- setups;
- valid planned entries;
- fills;
- fill rate;
- wins/losses;
- WR;
- TP rate;
- net PF;
- net expectancy/trade;
- total net PnL;
- time-exit rate;
- median nominal RR.

## Mandatory assertions
Abort before result persistence if any fail:
1. every source signal is from B27Q and matches London->NY LONG with K in {1,2};
2. primary rows have `opp_visits_at_signal == 0`;
3. no entry timestamp precedes `signal_ts`;
4. no fraction-method planned price differs from `L + f*(H-L)`;
5. TP is always H and SL always L;
6. no filled limit order has a strict close breakout between signal completion and fill;
7. `NEXT_OPEN` uses exactly the first eligible 5m bar open;
8. signal-bar High/Low used by local methods comes only from the completed B27Q signal bar;
9. entry-method simulation never changes the B27Q structural outcome or signal identity;
10. selection code cannot access reference_validation or august metrics before choosing the primary method.

Research only. Live BBC unchanged.
