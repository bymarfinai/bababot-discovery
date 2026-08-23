# B27CS — BTC 24H Clock-TP Reward-Scaled SL Economics — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Test whether the B27CR clock-specific natural TP map can become economically viable when each clock receives a causal pre-T5 stop scaled to that clock's frozen reward distance.

B27CS freezes the F05 entry and the B27CR TP map. It tests **SL geometry only** plus the previously established delayed-protection staircase. No entry level, TP, confirmation gate, rescue duration, regime, weekday, or clock inclusion may be changed after results are seen.

## Data-reuse caveat
External and reference_validation have been inspected throughout the lineage. They are reused-data confirmation only, not untouched OOS. Even a positive B27CS result is a research candidate requiring a genuinely fresh holdout before promotion. Live BBC remains unchanged.

## Frozen source and data
Source: `BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv`, major partitions only with `eligible == True`.
Expected source: external 202 / development 333 / reference_validation 194 / pooled major 729.
Raw 5m identity: exactly 698,112 rows, 100% coverage.

Preserve executable F05 fill semantics from B27CN/B27CO. Expected executable fills: external 183 / development 297 / reference_validation 172 / pooled major 652. Candidate SL must not change fill identity.

## Frozen entry
- `R4 = H-L`
- F05 reference = `L + 0.05*R4`
- SHORT limit at F05 inside the original 4H block.
- If first executable bar opens above F05 but below H, actual fill is that open; otherwise F05.
- open >= H before fill cancels.
- completed close < L before fill cancels.
- completed close > H before fill cancels.
- no new entry after original block end.

## Frozen B27CR clock TP map
No clock target may change in B27CS:
- `00-04 UTC / 07-11 WIB`: **T5 = L - 0.05*R4**
- `04-08 UTC / 11-15 WIB`: **T15 = L - 0.15*R4**
- `08-12 UTC / 15-19 WIB`: **T15**
- `12-16 UTC / 19-23 WIB`: **T10 = L - 0.10*R4**
- `16-20 UTC / 23-03 WIB`: **T10** (B27CR reused confirmation was fragile/failed; still frozen here, no post-hoc downgrade)
- `20-00 UTC / 03-07 WIB`: **T15**

## Frozen reward-scaled SL candidates
For each actual executable fill, define `reward_px = entry_px - selected_target_px`, which must be >0.

Candidates:
- `BASE_H`: no added pre-T5 stop; structural completed close >H is the catastrophic invalidation comparator.
- `R50`: stop threshold = `entry_px + 0.50 * reward_px`; nominal RR = 2.00:1.
- `R75`: stop threshold = `entry_px + 0.75 * reward_px`; nominal RR = 1.333...:1.
- `R100`: stop threshold = `entry_px + 1.00 * reward_px`; nominal RR = 1.00:1.

Stops are defined from **actual fill** so marketable fills cannot accidentally violate nominal RR >=1:1. Realized loss can exceed nominal risk because close-stop execution occurs at the completed 5m close.

No wider-than-R100 candidate is allowed.

## Causal pre-T5 stop semantics
The candidate stop is a **completed 5m close invalidation**, never an intrabar touch/wick stop.

Before T5 is reached:
1. first completed close > H exits at that actual close as `FULL_SL_HIGH_BREAK`;
2. otherwise first completed close > candidate threshold exits at that actual close as `PRE_T5_CLOSE_SL`.

Fill-bar completed close may trigger either rule. If both are true, High-break classification has priority.

For T10/T15 final-target clocks, if a bar touches T5 but closes above the candidate threshold on that same bar, the close-stop wins; T5 protection is only earned after that bar completes and becomes active from the next raw 5m bar. This preserves the conservative B27CO chronology and prevents retroactive protection.

For the T5 final-target clock, an eligible T5 target touch exits the position immediately; because the completed-close stop is only known at bar close, the already-filled T5 target has chronological priority.

Once T5 has been validly reached without an exit, the pre-T5 candidate stop is permanently disabled.

## Frozen rebreak and milestone chronology
- completed close < L confirms rebreak;
- target/milestone scanning begins only from the next raw 5m bar after rebreak confirmation;
- no favorable target on the fill/rebreak confirmation bar is credited;
- before rebreak, no T5/T7.5/T10/T15 target is credited.

After rebreak:
- final selected TP is a resting favorable target and exits immediately when reached; if bar opens beyond the target, use actual open, otherwise target price;
- for T10/T15 clocks, first T5 touch earns an `L` ceiling from the next bar;
- first T7.5 touch earns a `T5` ceiling from the next bar;
- for T15 clocks, first T10 touch earns a `T10` ceiling from the next bar;
- existing active protection has priority at bar open/high before new milestones are evaluated;
- no pivot runner is used: B27CS isolates selected TP + SL economics.

If a milestone bar closes >H while no protection was already active, completed High invalidation is evaluated before the newly earned protection becomes active, except when that bar itself fills the final TP as described above.

## Frozen horizon
If final selected TP has not been reached by original block end, carry the position for exactly +4h, preserving the B27CN/B27CR rescue horizon. Protection and invalidation rules continue unchanged during the extension.

If still unresolved at `obs_end + 4h`, exit at boundary open when available, otherwise the final completed 5m close before the boundary.

## Economics
- fixed notional: **$500** per filled trade;
- round-trip fee: **$0.40**;
- no additional slippage beyond actual gap/open and completed-close execution rules;
- trading win = net PnL > 0.

Report N/trades, fill rate, WR, PF, expectancy/trade, total net PnL, avg win/loss, max drawdown, max loss streak, TP count, pre-T5 stop count, High-break count, protection exits, time exits, median hold.

## Development-only per-clock SL selection
Evaluate `BASE_H`, `R50`, `R75`, and `R100` independently in each of the six clocks using development only.

A new SL candidate can replace BASE_H only if:
1. development trades >=30;
2. development expectancy >0;
3. development PF >=1.10;
4. development expectancy is strictly greater than BASE_H expectancy in that same clock.

Among qualifying new candidates choose highest development expectancy. Tie-break: higher PF, then tighter risk in fixed order `R50 -> R75 -> R100`.

If no new candidate qualifies, select `BASE_H`. No clock may be dropped.

## Reused-data confirmation
Apply the frozen six-clock SL map unchanged to external and reference_validation.

A selected non-BASE SL is `REUSED_CONFIRMED` only if in both external and reference_validation:
- trades >=10;
- expectancy >0;
- PF >1.00;
- expectancy >= that partition/clock's BASE_H expectancy.

Failure cannot change the stop or delete the clock.

## Overall candidate gate
`B27CS_CLOCK_TP_SL_REUSED_CANDIDATE` requires all:
1. audit PASS and exact executable fill identity 183 / 297 / 172 / 652;
2. at least 3 of 6 clocks select a new SL rather than BASE_H;
3. at least half of selected new SL clocks are reused-confirmed;
4. selected-map development expectancy >0 and PF >=1.10;
5. selected-map external expectancy >0 and PF >1.00;
6. selected-map reference_validation expectancy >0 and PF >1.00;
7. selected-map pooled-major expectancy >0 and PF >=1.10;
8. no clock exclusion.

Otherwise verdict: `B27CS_CLOCK_TP_SL_NOT_SUPPORTED`.

`HIGH_QUALITY_70` is reported separately as WR >=70% in external, development, and reference_validation; it cannot override PF/expectancy.

## Required report order
1. six clocks first: every candidate's development N/WR/PF/expectancy/net and selected SL;
2. external + validation confirmation of the frozen selected rule for each clock;
3. selected-map economics by partition and pooled major;
4. direct comparison to `BASE_H` under the same frozen clock-TP architecture;
5. status and interpretation.

Research only. No live BBC changes.