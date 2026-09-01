# ETH B27DX — S5B Live-Executable Runner Breathing-Gap Geometry — Preregistration

## Purpose
After S5A found no supported arm milestone with the frozen 0.10R breathing gap, test whether the runner's **breathing gap** is the missing ETH-native management coordinate.

S5B changes breathing gap only. Arm and ratchet step are frozen.

## Frozen signal/portfolio layer
- LONG only;
- R300 / X360;
- F75 entry;
- F20 pre-arm completed-close invalidation;
- clocks 05:00, 09:00, 10:00, 16:00 UTC;
- exact B27DX corrected causal grammar;
- same global one-position lock and S4 tie rule;
- $500 notional, $0.40 round-trip fee;
- same major partitions.

## Deterministic runner freeze
S5A did not produce a supported arm family, so S5B does not select an arm by performance.

Freeze arm at **E25**, the same extension coordinate as the S4 fixed target and the median/central coordinate used in the prior static geometry sequence.

Freeze ratchet step at **0.10R**.

All B27DQ-style N+2 floor activation semantics remain unchanged.

## Breathing-gap grid — only changing dimension
Test:

`G05, G10, G15, G20, G25`

where `Gxx` means initial active floor is `arm - xx%R` after the causal N+2 placement buffer.

At E25 arm this corresponds to initial floors:
- G05 -> E20;
- G10 -> E15;
- G15 -> E10;
- G20 -> E05;
- G25 -> E00 (= H).

After arm, completed-close ratchets remain spaced by the frozen 0.10R step and advance the floor by 0.10R per milestone. The selected breathing gap remains the offset between the milestone ladder and protective floor.

No other gap may be added after results are seen.

## Causal runner semantics
Identical to S5A/B27DQ:
- pre-arm F20 close invalidation;
- high touch of E25 arms runner;
- newly learned floor from completed bar N activates only from N+2;
- previous floor remains during N+1;
- initial buffer retains F20 completed-close invalidation;
- active floor gap-open / low-touch execution only when floor was already active before the scored bar;
- floor never decreases;
- execution-end exit at execution-end open.

## Portfolio rescore
Every gap variant rebuilds runner exit timestamps and reruns the full chronological global one-position lock. Do not reuse the S4 accepted list.

## Promotion gate
Same demanding runner gate as S5A. A gap is SUPPORTED only if 0-bps Pooled Major has:
- net > S4 baseline +$385.75;
- PF >= 1.80;
- WR >= 70%;
- expectancy > +$0.81/trade;
- accepted N >= 80% of 478;
- every major partition net > 0 and PF > 1.0;
- zero early-floor activation violations;
- 5 bps Pooled Major PF >= 1.0 and net >= 0.

## Gap-family topology
A native breathing-gap family requires at least 2 adjacent SUPPORTED gap values on the 5-point grid.

## BTC-quality diagnostic
Report whether each gap reaches:
- WR >= 71.9%;
- PF >= 2.22;
- expectancy >= +$1.26/trade;
with all major partitions positive and 5 bps stress surviving.

## Decision states
- `ETH_S5B_NATIVE_GAP_FAMILY_SUPPORTED`
- `ETH_S5B_SUPPORTED_GAP_ISOLATED`
- `ETH_S5B_NO_SUPPORTED_GAP`
- `ETH_S5B_CAUSAL_AUDIT_FAILED`

## Guardrails
- Breathing gap is the only tuned dimension.
- Arm E25 and step 0.10R are frozen.
- No structure, entry, stop, clock, leverage, fee, or live-code changes.
