# B27BV — BTC 24H BEAR-Origin Failed-Reclaim MAE/MFE Anatomy — Preregistration

## Purpose

B27BU showed that the causal BEAR-origin failed-reclaim signal did not convert robustly into LONG economics using the exact next-5m-open entry, one local structural stop, and 1R/1.5R/2R targets. The pooled-major result was negative even though B27BT had a strong BEAR-origin transition association.

B27BV therefore freezes a non-optimizing path-anatomy audit:

> After the exact B27BT BEAR-origin FAILED_RECLAIM confirmation and next-5m-open eligibility, how much adverse excursion (MAE) and favorable excursion (MFE) occurs before the detector causally leaves SIDEWAYS, and does the previously frozen `LOCAL_LOW` risk unit appear materially tighter than the path actually needs?

No alternative stop, target, entry delay, filter, ATR, percentage buffer, or session restriction may be selected in B27BV. This experiment is descriptive structural anatomy only.

## Frozen source cohort

Use exactly the persisted B27BT episode artifact and select:
- `origin_state == BEAR`;
- `path_class == FAILED_RECLAIM`;
- external / development / reference_validation.

Mandatory identity:
- external: 6;
- development: 20;
- reference_validation: 8;
- pooled major: 34;
- pooled OOS external + reference_validation: 14.

Expected eventual-outcome identity from B27BU diagnostics:
- pooled major: 22 TRANSITION + 12 RESUME;
- pooled OOS: 11 TRANSITION + 3 RESUME.

Outcome is diagnostic only and is never used to define entry, risk unit, or the observation window.

## Frozen entry anchor

Entry anchor is unchanged from B27BU:
- `entry_ts = eligible_open_ts = confirmation_complete_ts`;
- `entry_px` = raw 5m OPEN exactly at `entry_ts`.

No later entry may be substituted.

## Frozen local risk unit

Reproduce B27BU exactly:
- `RCL` = first reclaim 5m bar from B27BT;
- `RB` = first re-break 5m bar from B27BT;
- `LOCAL_LOW = min(raw 5m low from RCL through RB inclusive)`;
- `LOCAL_R = entry_px - LOCAL_LOW`.

Require `LOCAL_LOW < entry_px` for every signal. B27BV must not alter this risk unit.

## Frozen observation window

For each signal observe raw 5m bars from `entry_ts` inclusive until `exit_effective_ts` exclusive, where `exit_effective_ts` is the causally completed 4H detector exit from SIDEWAYS already persisted by B27BT.

No 24h cap is applied because this is path anatomy rather than a trade-resolution experiment. The eventual detector outcome remains retrospective only.

## Frozen excursion definitions

For LONG orientation:
- `min_low` = minimum raw 5m LOW in the observation window;
- `max_high` = maximum raw 5m HIGH in the observation window;
- `MAE_pct_entry = max(0, entry_px - min_low) / entry_px`;
- `MFE_pct_entry = max(0, max_high - entry_px) / entry_px`;
- `MAE_local_R = max(0, entry_px - min_low) / LOCAL_R`;
- `MFE_local_R = max(0, max_high - entry_px) / LOCAL_R`.

Also record:
- whether `min_low <= LOCAL_LOW` (`local_low_breached`);
- first raw-5m timestamp at which the final MAE extreme occurs;
- first raw-5m timestamp at which the final MFE extreme occurs;
- minutes from entry to those extrema;
- realized detector-exit return from entry open to the first raw 5m OPEN at/after `exit_effective_ts`.

No threshold is optimized from these values.

## Required outputs

For each of external / development / reference_validation / pooled OOS / pooled major, separately for ALL / TRANSITION / RESUME, report:
- N;
- LOCAL_LOW breach rate;
- MAE % entry P25/P50/P75/P90;
- MFE % entry P25/P50/P75/P90;
- MAE in LOCAL_R P25/P50/P75/P90;
- MFE in LOCAL_R P25/P50/P75/P90;
- median minutes to MAE and MFE;
- median detector-exit return.

Also report frozen B27BU target reach diagnostics only at the already-preregistered levels 1R / 1.5R / 2R:
- share whose full pre-exit MFE reaches each level;
- no first-touch trade ordering is inferred from this descriptive reach statistic.

Persist one row per signal with all raw excursion fields.

## Frozen interpretation gate

Call `B27BV_FAILED_RECLAIM_EXCURSION_INFORMATIVE` only if ALL hold:
1. exact 6/20/8 signal identity and 22/12 pooled-major outcome identity reproduce;
2. every entry maps to a non-empty continuous raw 5m observation window ending strictly after entry;
3. every signal reproduces `LOCAL_LOW < entry_px` and positive `LOCAL_R`;
4. pooled-major TRANSITION N >=20 and pooled-OOS TRANSITION N >=10;
5. pooled-major TRANSITION median `MFE_local_R > MAE_local_R`;
6. pooled-OOS TRANSITION median `MFE_local_R > MAE_local_R`;
7. pooled-major TRANSITION P75 `MAE_local_R > 1.0`, demonstrating that the exact B27BU local stop is breached by a material upper-quartile share even among eventual transitions;
8. no stop/target/entry parameter is selected or changed from this result.

Otherwise call `B27BV_FAILED_RECLAIM_EXCURSION_NOT_INFORMATIVE`.

The gate is not a trading approval. An informative result only permits a separately preregistered follow-up geometry test based on the frozen descriptive envelope.

Reference_validation is already inspected and is not pristine live OOS.

Research only. Live BBC unchanged.
