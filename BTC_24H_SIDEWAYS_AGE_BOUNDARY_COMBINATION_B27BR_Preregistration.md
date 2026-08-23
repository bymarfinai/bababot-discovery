# B27BR — BTC 24H SIDEWAYS Age × Frozen-Boundary Combination — Preregistration

## Purpose

Combine the two already-supported regime findings from B27BM and B27BN without adding entry/exit logic:

1. SIDEWAYS age changes the cause-specific RESUME vs TRANSITION hazard; and
2. frozen prior swing-boundary invalidation increases transition risk.

B27BR asks whether the frozen-boundary signal becomes more discriminative once SIDEWAYS has survived into age 2 / 8h, while preserving strict out-of-sample partition reporting.

This is regime-state anatomy only. No LONG/SHORT mapping, entry, stop, target, fee, WR, PF, PnL, session filter, classifier fitting, or live BBC change is permitted.

## Frozen lineage

Reuse unchanged:
- B27BH bracketed SIDEWAYS episodes;
- B27BM age semantics;
- B27BN frozen boundary semantics and episode-level break fields.

Mandatory identity:
- 1,023 major-partition bracketed episodes;
- 527 RESUME + 496 TRANSITION;
- BULL-origin 532;
- BEAR-origin 491;
- pooled OOS BULL-origin 313;
- pooled OOS BEAR-origin 242;
- frozen boundary availability >=95% pooled OOS for both origins.

OOS partitions are `external` and `reference_validation`. `development` is reported but cannot rescue an OOS failure.

## Causal age risk sets

Age `k` means the episode has remained SIDEWAYS through `k` completed 4H SIDEWAYS intervals. Primary ages are:
- age 1 = 4h;
- age 2 = 8h;
- age 3 = 12h.

For age `k`, include only episodes with `n_intervals >= k`. This is causal because membership is known once the kth SIDEWAYS interval has completed.

## Frozen boundary state

Boundary remains exactly B27BN:
- BULL-origin: latest confirmed swing low from the immediately preceding completed BULL state;
- BEAR-origin: latest confirmed swing high from the immediately preceding completed BEAR state.

At each age k classify the cumulative boundary state through the first k completed SIDEWAYS intervals:

- `HOLD`: no wick break has occurred by age k;
- `WICK_BREAK`: at least one wick break has occurred by age k.

A wick break is exactly B27BN:
- BULL-origin: 4H low strictly below frozen swing low;
- BEAR-origin: 4H high strictly above frozen swing high.

Close-break state is reported only as a secondary diagnostic and cannot rescue the primary wick-break gate.

## Primary outcome

For each partition, origin, and age report:
- risk N;
- WICK_BREAK N and HOLD N;
- eventual TRANSITION N/rate in each state;
- eventual RESUME N/rate in each state;
- `transition_lift = P(TRANSITION | WICK_BREAK) - P(TRANSITION | HOLD)`.

Also report the same descriptive readout for cumulative close-break vs no close-break.

## Frozen primary hypothesis

The primary decision age is **age 2 / 8h**.

Call `B27BR_AGE2_BOUNDARY_ROUTER_SUPPORTED` only if ALL hold:

1. source/parent identity reproduces exactly and boundary availability is >=95% pooled OOS for both origins;
2. pooled-OOS age-2 risk N >=30 for each origin;
3. pooled-OOS age-2 WICK_BREAK N >=20 and HOLD N >=20 for each origin;
4. pooled-OOS age-2 transition lift is strictly positive for both BULL-origin and BEAR-origin;
5. age-2 transition lift is strictly positive in `external` and `reference_validation` separately for both origins, with >=5 observations in each compared cell;
6. pooled-OOS age-2 transition lift is greater than pooled-OOS age-1 transition lift for both origins;
7. all boundary states use only information available through the completed age-k interval;
8. no trading/economic rule or live BBC file is changed.

Otherwise call `B27BR_AGE2_BOUNDARY_ROUTER_NOT_SUPPORTED`.

Age 3 / 12h is descriptive only and cannot rescue a failed age-2 primary gate.

## Interpretation boundary

A supported result would validate only a simple causal regime router: after SIDEWAYS survives to 8h, cumulative frozen-boundary break adds stable transition information beyond elapsed age alone. It would not by itself authorize a trade or define a 5m entry.

Research only. Live BBC unchanged.
