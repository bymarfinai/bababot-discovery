# B27T — London -> New York Pressure Path / Stop-Semantics Audit — Preregistration

## Purpose
Audit the apparent contradiction between B27Q's high directional target-break probability and B27R/S's weak entry economics. This is a diagnostic audit only; no new signal or entry rule is promoted.

## Frozen cohort
Reuse B27Q signal identities unchanged. Primary cohort only:
- transition = LONDON_TO_NEWYORK
- side = LONG / signal_level = HIGH
- K = 1
- opp_visits_at_signal = 0
Report external, development, reference_validation, and August separately.

## Frozen structure
Previous-session H/L and 5m chronology are unchanged from B27Q. Structural target-break remains first strict 5m close > H before first strict 5m close < L; no-break by session end remains no-break.

## Diagnostic path measures
Starting strictly after signal completion and ending at the first strict close-break or active-session end, persist for every signal:
1. minimum 5m low and its range fraction `(min_low-L)/(H-L)`;
2. minimum 5m close and its range fraction;
3. whether price wicked to/below L before the eventual target close-break;
4. whether price closed below L before target close-break;
5. whether H was wick-touched before strict H close-break;
6. first timestamp each fixed fraction F80/F75/F70/F65/F60/F55/F50 was touched after signal;
7. signal next-open fraction and nominal reward:risk to H versus wick-stop at L.

## Stop-semantics comparison
For NEXT_OPEN and frozen fraction entries F80/F75/F70/F65/F60/F55/F50, compare two diagnostic outcome semantics using the same fills:
- WICK_STOP: existing B27R semantics; stop if low <= L, target if high >= H, same-5m both -> conservative stop.
- CLOSE_INVALIDATION: target if high >= H; invalidate only when a completed 5m close < L. Exit at that bar close for diagnostics. Same bar target-touch plus close<L is scored conservative invalidation.

The purpose is not to declare CLOSE_INVALIDATION tradable; it quantifies how much of the B27R degradation comes from using a stricter wick stop than the B27Q structural invalidation.

## Mandatory assertions
Abort before persistence if:
- signal identities differ from B27Q primary cohort;
- any path starts before signal_ts;
- any TARGET_BREAK signal contains an earlier close < L;
- any OPPOSITE_BREAK signal contains an earlier close > H;
- fixed fraction prices are not exact frozen range fractions;
- WICK_STOP control does not reproduce B27R K1 OPP0 fixed-fraction resolved outcomes within the same historical rows.

Research only; live BBC unchanged.