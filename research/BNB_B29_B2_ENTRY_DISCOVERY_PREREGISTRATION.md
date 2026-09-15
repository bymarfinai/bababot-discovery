# BNB B29-B2 — Frozen Character Entry Discovery — Preregistration

## Scientific identity
`B29-B2-v1`

B2 is the first execution phase after the valid B1J character promotion. The B1J character itself is immutable in this phase. B2 asks only: **when should a LONG position be entered after the frozen character becomes known?**

No TP, SL, leverage, position sizing, fees, PnL dollars, hour/session filters, or live orders are part of B2.

## Immutable source and frozen character
Source artifact: accepted B29-A1 artifact `10336102957`, file `BNB_B29_A1_STRUCTURE_FINGERPRINT.csv.gz`, SHA256:

`eae8f278d45e7c3035b03900b30e315b16a241c1fbc5fda39231681390c25cfa`

Expected rows: 229,267. All calculations must be gap-safe on exact 15-minute timestamps.

Frozen B1J LONG character:
1. current completed decision bar has `sweep_low_60 == 1`;
2. previous exact 15-minute state has `path_state == CONT_DOWN`;
3. event bar `close_location >= 0.50` (`reclaim_strength == HIGH`);
4. event bar `body_range < 0.33` (`reclaim_body == LOW`);
5. same-family event cooldown remains 60 minutes.

The character definition, direction, thresholds, and event set may not be changed in B2.

## Price-return reconstruction
Accepted A1 `ret_15` is used to reconstruct exact close-to-close returns. No absolute price level is required.

For a character event at `t`, B2 evaluates close-entry candidates at `t`, `t+15m`, or `t+30m`. A delayed entry is allowed only when every required timestamp exists exactly. Entry at a decision close means the corresponding completed 15-minute close is known before the simulated market entry.

### Primary common anchor
The primary comparison exit anchor is the close at **event `t+60m`** for every policy.

This deliberately keeps the original B1J +60-minute character horizon fixed. Therefore B2 tests whether waiting/confirmation improves or degrades capture of the already-proven character move rather than silently changing the character horizon.

For an entry at `t+d`, primary signed return is close-to-close return from `t+d` to `t+60m`.

### Auxiliary robustness
For every filled policy also report:
- return from entry to event `t+120m`;
- return from entry to **60 minutes after entry**;
- participation rate relative to frozen B1J character events.

These are robustness diagnostics only; the primary promotion metric remains event-anchor `t+60m`.

## Frozen entry-policy grammar
Exactly the following 10 policies are tested. No threshold grid is allowed.

1. `E0_EVENT_CLOSE`
   - enter at event close `t`.
   - all valid frozen-character events are filled.

2. `E15_ANY`
   - enter at close `t+15m`.
   - no additional condition.

3. `E15_UP`
   - enter at close `t+15m` only if A1 `ret_15(t+15m) > 0`.

4. `E15_PULLBACK`
   - enter at close `t+15m` only if `ret_15(t+15m) <= 0`.

5. `E15_HOLD`
   - enter at close `t+15m` only if `break_low_60(t+15m) == 0`.

6. `E15_UP_HOLD`
   - enter at close `t+15m` only if `ret_15(t+15m) > 0` AND `break_low_60(t+15m) == 0`.

7. `E15_PULLBACK_HOLD`
   - enter at close `t+15m` only if `ret_15(t+15m) <= 0` AND `break_low_60(t+15m) == 0`.

8. `E30_TWO_UP`
   - enter at close `t+30m` only if `ret_15(t+15m) > 0` AND `ret_15(t+30m) > 0`.

9. `E30_PULLBACK_RECOVER`
   - enter at close `t+30m` only if `ret_15(t+15m) <= 0` AND `ret_15(t+30m) > 0`.

10. `E30_HOLD`
    - enter at close `t+30m` only if `break_low_60(t+15m) == 0` AND `break_low_60(t+30m) == 0`.

All conditions are known at the simulated entry close. No future bar may participate in an entry decision.

## Development and reference split
### Entry discovery / development
Use only frozen-character events from:
- 2022
- 2023
- 2024

Only these years rank/select entry policies.

### Reference validation
After the development shortlist is frozen inside the deterministic run, evaluate unchanged policies on:
- 2025
- 2026 through accepted A1 cutoff.

These are reference validation, not final untouched OOS. Final ready-to-trade evidence still requires future shadow observations after character + entry + risk rules are all frozen.

## Development eligibility gate
A policy can enter the ranked shortlist only if all are true:
- development filled N >= 120;
- filled N >= 30 in each of 2022, 2023, 2024;
- participation >= 35% of eligible frozen-character events in development;
- pooled primary `t+60` hit >= 60.0%;
- each development year primary hit >= 55.0%;
- Wilson 95% lower bound for pooled primary hit > 54.0%;
- pooled median primary signed return > 0;
- event `t+120` hit >= 57.0%;
- entry+60m hit >= 57.0%;
- max development-year share <= 45%.

For each policy compute a one-sided exact binomial p-value versus 50% on the primary hit. Apply Benjamini-Hochberg FDR at q=0.05 across the 10 frozen policies. A shortlisted policy must be FDR-significant.

## Development ranking / overlap control
Rank development-pass policies by:
1. highest worst development-year primary hit;
2. highest pooled primary Wilson lower bound;
3. highest pooled primary hit;
4. highest median primary signed return;
5. larger filled N;
6. lexical policy name.

Promote at most 3 policies to reference validation. After selecting a policy, suppress a later candidate if its filled development event set has Jaccard overlap >0.90 with an already-selected policy.

## Reference validation gate
A shortlisted policy passes B2 only if all are true unchanged:
- 2025 filled N >= 25 and primary hit >=55.0%;
- 2026 filled N >= 20 and primary hit >=55.0%;
- combined 2025+2026 primary hit >=57.0%;
- combined reference median primary signed return >0;
- combined reference event `t+120` hit >=55.0%;
- combined reference entry+60m hit >=55.0%;
- pooled 2022-2026 primary hit >=59.0%;
- pooled 2022-2026 Wilson 95% lower bound >55.0%;
- every one of five eras primary hit >50.0%;
- max five-era filled-sample share <=35%.

At least one of the frozen development-selected policies must pass every reference gate for status:

`BNB_B29_B2_ENTRY_DISCOVERY_PASS`

Otherwise:

`BNB_B29_B2_ENTRY_DISCOVERY_REJECT`

Any artifact/data/integrity failure before valid evaluation is `BNB_B29_B2_DATA_TOOLING_FAILURE` and is not a scientific rejection.

## Promotion boundary
A B2 PASS freezes an **entry mechanism only**. It does not authorize trading and is not a TP/SL result.

Only after B2 PASS may the winning frozen character + entry pair advance to a separately preregistered payoff/risk surface phase.

## Stop rule
After a valid B2-v1 result, do not rescue it by:
- changing the frozen B1J character;
- lowering gates;
- switching primary horizon;
- adding entry thresholds or clock/session filters;
- choosing an unshortlisted policy based on 2025/2026;
- changing sign conditions after seeing results;
- adding TP/SL and calling the same test B2-v1.

Any materially new entry family requires a new scientific identity.

No live orders are authorized by this phase.
