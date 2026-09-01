# ETH B27DX — S9A Stale Entry Cancellation — Preregistration

## Purpose
Test whether delayed F75 retrace fills are a causal source of avoidable losses.

This experiment tests exactly one entry-freshness rule. No cutoff sweep is allowed.

## Frozen baseline
- LONG only.
- R300 / X360.
- Entry F75.
- Target E25.
- Completed-close invalidation F20.
- Execution clocks: 05:00, 09:00, 10:00, 16:00 UTC.
- Global one-position lock exactly as S4.
- Partitions: External, Development, Reference Validation.
- 0 bps primary and 5 bps stress.

## S9A rule — frozen before results
A setup remains eligible only when the F75 fill occurs on the **first eligible raw 5m bar after the completed K1 leave bar**.

Formally:
- `eligible_start = leave_bar_start + 5 minutes`.
- Accept candidate iff `fill_ts == eligible_start`.
- Any later fill is cancelled as stale; there is no second chance inside that execution window.

No 10m/15m/20m freshness alternatives will be tested in S9A.

## Portfolio accounting
The freshness rule is applied to the full S4 candidate universe **before** global one-position locking.
The portfolio is then re-locked from scratch using the same S4 causal tie/lock rules. This allows later candidates that were previously blocked by a stale candidate to become executable.

## Primary hypothesis
If stale fills are causally harmful, first-eligible-only cancellation should improve executable loss quality without requiring any geometry or exit change.

## Frozen promotion gate
S9A is called `SUPPORTED` only if all are true:
1. Candidate reconstruction / eligible-bar chronology audit passes.
2. Filtered 0 bps portfolio has PF > 1 and net > 0 in External, Development, and Reference Validation separately.
3. Filtered pooled-major 5 bps PF > 1 and net > 0.
4. Filtered pooled-major accepted-trade retention is at least 50% of S4 baseline accepted trades.
5. Filtered pooled-major WR, PF, and expectancy are each strictly higher than S4 baseline 0 bps.

BTC-quality is reported only as a diagnostic benchmark; it is not required for S9A support.

## Required outputs
- candidate-level immediate/stale classification and delay bars,
- baseline vs filtered portfolio metrics by partition and pooled-major,
- accepted-trade retention and trades/week,
- loss rate for immediate vs stale candidates under the original S4 lock,
- number of newly freed executable trades after re-lock,
- 5 bps stress,
- causal/parity audit,
- written verdict.

## Guardrails
- No alternate freshness cutoff.
- No new entry/target/stop/runner values.
- No leverage or position-sizing change.
- No live-code change.
- No selecting clocks after seeing S9A results.
