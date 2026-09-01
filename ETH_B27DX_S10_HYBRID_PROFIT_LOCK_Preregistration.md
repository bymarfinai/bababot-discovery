# ETH B27DX — S10 Hybrid Profit-Lock — Preregistration

## Purpose
Test the user's BTC-hybrid hypothesis on the frozen ETH-native portfolio without another global runner sweep: keep fixed E25 exits on habitats where runner behavior was not historically consistent, and use a live-executable B27DQ-style ratcheting profit floor only on the one habitat that previously showed positive E10 runner economics in all three major partitions.

This is an exploratory engineering test because the 10:00 runner habitat was identified from previously inspected S5A history. It is not pristine unseen OOS confirmation.

## Frozen signal universe
- LONG only.
- R300 / X360.
- F75 entry.
- F20 completed-close pre-arm invalidation.
- Execution clocks: 05:00, 09:00, 10:00, 16:00 UTC.
- Global one-position chronological lock exactly as S4.
- Partitions: External, Development, Reference Validation.
- $500 research notional and $0.40 fee.

## Frozen hybrid management map
- 05:00 UTC: fixed E25 target, exactly S4.
- 09:00 UTC: fixed E25 target, exactly S4.
- 10:00 UTC: B27DQ-style live-executable E10 profit-lock runner, exactly S5A E10 semantics.
- 16:00 UTC: fixed E25 target, exactly S4.

No alternate runner habitat is allowed in S10.

## Why 10:00 is frozen as the runner habitat
Prior S5A E10 per-clock anatomy was already inspected. 10:00 was the only habitat whose E10 runner remained positive (PF>1, expectancy>0, net>0) in External, Development, and Reference Validation. This historical selection makes S10 exploratory; S10 will not reinterpret the other clocks after results.

## Frozen 10:00 runner semantics
Identical to S5A/B27DQ:
1. Before arm, F20 completed-close invalidation remains active.
2. Touch of E10 (`H + 0.10R`) arms the runner.
3. Initial desired floor is H (one 0.10R breathing step behind arm).
4. A floor learned from completed bar N becomes active only from bar N+2.
5. During N+1 the previously active floor remains the only live floor; before first floor activation, F20 completed-close invalidation remains available.
6. Once active before a bar starts: open <= floor exits at open; otherwise low <= floor exits at floor.
7. Ratchet ladder is fixed at 0.10R steps: close >= E20 schedules floor E10; close >= E30 schedules floor E20; close >= E40 schedules floor E30; etc.
8. Floor never decreases.
9. If no runner/fixed/invalidation exit occurs, execution-end exit is at execution-end bar open.

No arm/gap/step sweep is allowed.

## Stress
- Primary: 0 bps.
- Diagnostic: 5 bps adverse execution stress using the already frozen S4/S5A scoring semantics.
- Stress may not change event chronology.

## Required parity/audit
- Rebuild the S4 fixed candidate universe.
- Rebuild S5A E10 candidates for 10:00.
- Assert candidate identity, entry timestamp, entry price, H and L parity for every 10:00 candidate before substituting exit management.
- Assert zero S5A early-floor violations for the substituted runner candidates.
- Re-lock the complete hybrid candidate stream globally per partition after exit timestamps change.

## Frozen decision gate
`ETH_S10_HYBRID_PROFIT_LOCK_SUPPORTED` only if all are true:
- parity / causal audit passes;
- every major partition at 0 bps has PF>1 and net>0;
- pooled 5 bps PF>1 and net>0;
- pooled 0 bps WR >= S4 pooled WR;
- pooled 0 bps PF > S4 pooled PF;
- pooled 0 bps expectancy > S4 pooled expectancy;
- pooled 0 bps net > S4 pooled net;
- accepted N >= 95% of S4 accepted N.

BTC-class quality is a separate diagnostic: WR >= 71.9%, PF >= 2.22, expectancy >= +$1.26/trade with all major partitions positive and 5 bps survival.

## Guardrails
- No S9A freshness cancellation.
- No S9B early scratch.
- No geometry, clocks, leverage, fees, entry, target, stop, arm, gap, or ratchet-step optimization.
- No live BBC code/config change.
