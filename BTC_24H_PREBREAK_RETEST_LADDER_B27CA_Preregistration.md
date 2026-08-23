# B27CA — BTC 24H Pre-Break Retest Ladder + Adaptive Pre-L2 SHORT Anatomy — Preregistration

## Purpose
Return to the exact pre-break architecture that mirrors B27W/B27AK:

**Low Touch #1 / K1 -> causal leave -> optional retrace SHORT entry before the next Low return -> then either direct Low break on that return OR genuine Low #2 -> later Low break.**

B27CA explicitly does NOT use the B27BZ post-break retest architecture.

This experiment answers two separate questions:
1. Before the previous-4H Low finally close-breaks, how many distinct Low-touch episodes occurred?
2. Does the best pre-return retrace fraction differ by 4H clock block, or is fixed F15 still the most stable choice?

Structural anatomy only. No trading stop, TP, RR, fee, PF, PnL, leverage, or live BBC change.

## Frozen source cohort
Reuse exactly persisted B27BE K1+OPP0 rows from `BTC_24H_4H_REGIME_SHORT_ATLAS_B27BE_Detail.csv`.

Primary universe: external / development / reference_validation.
Mandatory identities:
- external 862;
- development 1,264;
- reference_validation 641;
- pooled major 2,767;
- BULL 1,146; BEAR 1,122; SIDEWAYS 499.

Six fixed UTC observation blocks remain 00-04 / 04-08 / 08-12 / 12-16 / 16-20 / 20-00. Each uses the immediately previous completed 4H High `H` and Low `L`.

## Distinct Low-touch / break semantics
Use exact B27BE raw-5m semantics:
- Low touch: `low <= L` and `close >= L`;
- consecutive Low-touch bars are one touch episode;
- a new Low touch after at least one non-touch bar is a new distinct visit;
- Low break: first completed raw-5m `close < L`;
- opposite break: first completed raw-5m `close > H`;
- scanning ends at first boundary close-break or block end.

For every eventual Low-break row, report the number of distinct Low visits completed before the break: 1 / 2 / 3 / 4+.

## Exact pre-return chronology
K1 is Low Touch #1.

Consume the complete contiguous K1 episode. A clean causal leave requires a completed 5m bar after K1 that:
- is not a Low touch;
- has not strict-close-broken L or H.

Entry eligibility begins on the NEXT raw 5m bar after that leave completes.

After the leave, the first later interaction with L can be one of two different events:
- `BREAK_BEFORE_GENUINE_L2`: completed raw-5m `close < L`; this is a favorable downside break and is NOT counted as a genuine second touch episode;
- `GENUINE_L2`: first later distinct Low-touch episode with `low <= L` and `close >= L`.

First strict `close > H` or block end can terminate the pre-return window as well. The terminal return/break/opposite-break bar itself is never fill-eligible.

This distinction is mandatory because B27W-style second arrival may itself be a breakout arrival; B27CA must not discard a Low break merely because it occurs before a genuine Low #2 bounce/retest forms.

## Frozen retrace grid
Normalize previous-4H range Low=0 / High=1. Freeze exactly:
- F05 = `L + 0.05*(H-L)`
- F10 = `L + 0.10*(H-L)`
- F15 = `L + 0.15*(H-L)`
- F20 = `L + 0.20*(H-L)`
- F25 = `L + 0.25*(H-L)`

A candidate SHORT limit fill occurs only on an eligible raw-5m bar strictly after causal leave and strictly before the first later L interaction / opposite break / block-end terminal, when the bar spans the exact candidate price.

No additional fractions may be added after results are seen.

## Structural outcomes after fill
For each valid pre-return fill, classify the later block outcome using exact B27BE chronology:

1. `BREAK_BEFORE_GENUINE_L2`: first later L interaction is a strict Low close-break. This counts as eventual Low-break success after fill.
2. `GENUINE_L2_THEN_BREAK`: a genuine second Low-touch episode forms first, and a later strict `close < L` occurs before strict `close > H` / block end. This also counts as eventual Low-break success after fill.
3. `GENUINE_L2_NO_BREAK`: genuine L2 forms but no later Low break before opposite break / block end.
4. `NO_L_RETURN_OR_OPPOSITE`: no favorable Low break and no genuine L2 before opposite break / block end.

Thus the primary candidate metric is:

`EVENTUAL_LOW_BREAK_AFTER_FILL = BREAK_BEFORE_GENUINE_L2 + GENUINE_L2_THEN_BREAK`.

Also report the genuine-L2 branch separately, including later Low-break probability after genuine L2.

For each fraction report:
- clean-leave N;
- fills before first later L interaction;
- break-before-genuine-L2 N/rate among fills;
- genuine-L2 N/rate among fills;
- later Low-break-after-L2 N;
- Low-break-after-L2 / genuine-L2 rate;
- eventual Low-break-after-fill N/rate.

None of these structural rates may be called trading WR.

## Required retest-ladder reporting
For each major partition, each pooled-major regime, and each pooled-major clock block report:
- K1 N;
- eventual Low-break N/rate;
- among Low breaks: break after exactly 1 / 2 / 3 / 4+ distinct Low visits;
- among setups reaching genuine L2: probability of later Low break.

This anatomy must be kept separate from candidate-entry metrics.

## Fixed-F15 primary readout
F15 remains the primary transfer rule because it is the exact B27W F85 mirror and the B27AK structural winner.

F15 fill identities must reproduce B27BY for the major partitions: external 441 / development 589 / reference_validation 228. B27CA then decomposes B27BY's broad L-return milestone into direct-break-before-genuine-L2 versus genuine-L2 branches.

Report F15 separately for external / development / reference_validation and for every clock/regime.

## Clock-adaptive fraction selection — development only
To test whether entry geometry differs by clock without post-hoc OOS selection:

For EACH of the six clock blocks independently:
1. use development rows only;
2. eligible candidate requires >=20 fills;
3. score candidate by highest `eventual_low_break_after_fill_rate`;
4. ties within 1e-12: higher genuine-L2 rate, then higher fill N, then nearest to F15, then lower fraction;
5. freeze exactly one selected fraction for that clock.

Then evaluate those six frozen clock-specific selections on external and reference_validation separately. External/validation may NOT alter the selected fractions.

Also compute an OOS aggregate of the six selected clock rules and compare it with fixed F15 using the same external+validation rows.

## Frozen adaptive support gate
`B27CA_CLOCK_ADAPTIVE_CANDIDATE_SUPPORTED` only if ALL hold:
1. exact B27BE identities reproduce;
2. F15 major-partition fill identities reproduce B27BY;
3. every selected clock has an eligible development candidate;
4. external selected-clock aggregate has >=100 fills;
5. reference_validation selected-clock aggregate has >=60 fills;
6. adaptive eventual-Low-break-after-fill rate is >= fixed-F15 rate in BOTH external and reference_validation;
7. adaptive pooled-OOS eventual-Low-break-after-fill rate exceeds fixed-F15 pooled-OOS by >=3.0 percentage points;
8. no future regime state, stop/TP economics, session relabeling, or post-hoc fraction change is used.

If the gate fails, verdict is `B27CA_CLOCK_ADAPTIVE_NOT_SUPPORTED`.
If it passes, verdict is `B27CA_CLOCK_ADAPTIVE_CANDIDATE_SUPPORTED`, which only permits a separately preregistered economic backtest.

B27BZ remains a separate exploratory branch and is not used to choose B27CA fractions.
