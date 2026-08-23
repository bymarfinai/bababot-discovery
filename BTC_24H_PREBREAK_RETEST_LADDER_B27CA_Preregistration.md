# B27CA — BTC 24H Pre-Break Retest Ladder + Adaptive Pre-L2 SHORT Anatomy — Preregistration

## Purpose
Return to the exact pre-break architecture that mirrors B27W/B27AK:

**Low Touch #1 / K1 -> causal leave -> optional retrace SHORT entry between Low #1 and genuine Low #2 -> Low #2 -> later Low break.**

B27CA explicitly does NOT use the B27BZ post-break retest architecture.

This experiment answers two separate questions:
1. Before the previous-4H Low finally close-breaks, how many distinct Low-touch episodes occurred?
2. Does the best pre-L2 retrace fraction differ by 4H clock block, or is fixed F15 still the most stable choice?

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

## Exact pre-L2 chronology
K1 is Low Touch #1.

Consume the complete contiguous K1 episode. A clean causal leave requires a completed 5m bar after K1 that:
- is not a Low touch;
- has not strict-close-broken L or H.

Entry eligibility begins on the NEXT raw 5m bar after that leave completes.

`GENUINE_L2` is the first later distinct Low-touch episode under B27BE semantics (`low <= L` and `close >= L`). A bar with `close < L` is a Low break, not L2.

Before genuine L2, first strict `close < L`, first strict `close > H`, or block end terminates the pre-L2 window. The terminal bar itself is never fill-eligible.

## Frozen retrace grid
Normalize previous-4H range Low=0 / High=1. Freeze exactly:
- F05 = `L + 0.05*(H-L)`
- F10 = `L + 0.10*(H-L)`
- F15 = `L + 0.15*(H-L)`
- F20 = `L + 0.20*(H-L)`
- F25 = `L + 0.25*(H-L)`

A candidate SHORT limit fill occurs only on an eligible raw-5m bar strictly after causal leave and strictly before genuine L2 / boundary break / block-end terminal, when the bar spans the exact candidate price.

No additional fractions may be added after results are seen.

## Post-L2 structural outcome
For a candidate that filled before genuine L2:
- if genuine L2 never occurs, full-chain success is false;
- once genuine L2 occurs, continue exact B27BE chronology through the same 4H block;
- success = first later strict `close < L` before strict `close > H` or block end;
- a later third/fourth Low touch may occur before the break and is allowed;
- `LOW_BREAK_AFTER_L2` is structural only, not a TP.

For each fraction report:
- clean-leave N;
- fills before L2;
- genuine-L2 N after fill and L2/fill rate;
- later Low-break-after-L2 N;
- Low-break-after-L2 / L2 rate;
- full-chain success / fill rate = fill -> genuine L2 -> later Low break.

## Required retest-ladder reporting
For each major partition, each pooled-major regime, and each pooled-major clock block report:
- K1 N;
- eventual Low-break N/rate;
- among Low breaks: break after exactly 1 / 2 / 3 / 4+ distinct Low visits;
- among setups reaching genuine L2: probability of later Low break.

This anatomy must be kept separate from candidate-entry metrics.

## Fixed-F15 primary readout
F15 remains the primary transfer rule because it is the exact B27W F85 mirror and the B27AK structural winner.

Report F15 separately for external / development / reference_validation and for every clock/regime. Do not call any F15 structural rate trading WR.

## Clock-adaptive fraction selection — development only
To test whether entry geometry differs by clock without post-hoc OOS selection:

For EACH of the six clock blocks independently:
1. use development rows only;
2. eligible candidate requires >=20 fills and >=10 genuine-L2 arrivals after fill;
3. score candidate by highest `full_chain_success_rate = LOW_BREAK_AFTER_L2 / fills`;
4. ties within 1e-12: higher L2/fill rate, then higher fill N, then nearest to F15, then lower fraction;
5. freeze exactly one selected fraction for that clock.

Then evaluate those six frozen clock-specific selections on external and reference_validation separately. External/validation may NOT alter the selected fractions.

Also compute an OOS aggregate of the six selected clock rules and compare it with fixed F15 using the same external+validation rows.

## Frozen adaptive support gate
`B27CA_CLOCK_ADAPTIVE_CANDIDATE_SUPPORTED` only if ALL hold:
1. exact B27BE identities reproduce;
2. every selected clock has an eligible development candidate;
3. external selected-clock aggregate has >=100 fills;
4. reference_validation selected-clock aggregate has >=60 fills;
5. adaptive full-chain success rate is >= fixed-F15 full-chain rate in BOTH external and reference_validation;
6. adaptive pooled-OOS full-chain success exceeds fixed-F15 pooled-OOS by >=3.0 percentage points;
7. no future regime state, stop/TP economics, session relabeling, or post-hoc fraction change is used.

If the gate fails, verdict is `B27CA_CLOCK_ADAPTIVE_NOT_SUPPORTED`.
If it passes, verdict is `B27CA_CLOCK_ADAPTIVE_CANDIDATE_SUPPORTED`, which only permits a separately preregistered economic backtest.

B27BZ remains a separate exploratory branch and is not used to choose B27CA fractions.
