# B27BL — 24H Temporal Transition Resolution Audit

**Source:** `BTC_24H_TEMPORAL_TRANSITION_RESOLUTION_B27BL_Result.md`

**Audit:** PASS. **Frozen verdict: `B27BL_TEMPORAL_PENDING_STATE_NOT_SUPPORTED`.**

**Purpose:** test whether SIDEWAYS ambiguity is better modeled temporally as an unresolved `PENDING` state rather than forcing a final regime decision on the first completed 4H SIDEWAYS bar. No trading direction or economics were used.

**Exact parent identity:** 1,023 B27BH directionally bracketed SIDEWAYS episodes = 527 RESUME + 496 TRANSITION; BULL-origin 532; BEAR-origin 491.

### Pooled OOS temporal resolution

- +4h: **44.0%** resolved; 56.0% still pending; pending eventual transition rate **56.3%**.
- +8h: **72.6%** resolved.
- +12h: **83.8%** resolved.
- +24h: **91.7%** resolved.

### One-bar SIDEWAYS survival effect

Remaining SIDEWAYS beyond the first 4H bar increased eventual transition probability in every OOS origin/partition cell, but the pooled lift was below the frozen +10pp promotion gate:

- BULL pooled OOS: baseline **43.8%** -> pending **52.2%** = **+8.5pp**.
- BEAR pooled OOS: baseline **54.1%** -> pending **61.8%** = **+7.7pp**.
- External: BULL +6.3pp; BEAR +4.9pp.
- Reference validation: BULL +14.2pp; BEAR +11.8pp.

**Frozen gate outcome:** identity PASS; +8h resolution PASS; positive OOS sign PASS; sample-size PASS; +12h resolution PASS; pooled one-bar transition lift >=10pp for both origins FAIL.

**Interpretation:** temporal age is informative and most SIDEWAYS episodes resolve naturally within 8-12 hours, but the exact preregistered evidence was not strong enough to promote `PENDING` as the new detector state. Do not relax the +10pp gate post hoc. A new experiment is required for any alternative temporal state-machine design.

Observable CI: run `32618502009`, job `97142952212`, success. Exact CSV outputs are preserved in artifact `9487667797`.

Research only. Live BBC unchanged.
