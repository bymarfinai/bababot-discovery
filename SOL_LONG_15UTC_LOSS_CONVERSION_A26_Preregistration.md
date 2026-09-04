# SOL LONG 15:00 UTC Loss Conversion Anatomy — A26 Preregistration

## Frozen habitat
- SOLUSDT 5m
- Central habitat: R360 / 15:00 UTC
- Frozen parent: E0_RESTING_H -> E40
- Parent lifecycle is unchanged from A20/A24.
- A23 recovery H2/H3/H4 is rejected and MUST NOT be inherited.

## Objective
Forensic only. Study every frozen parent loss and identify which losses are still structurally recoverable to E40 after the frozen exit, then identify causal path differences observable before that later E40 recovery.

## Recovery observation window
- 720 minutes after frozen parent exit, bounded by partition end.
- A loss is `LATENT_RECOVERABLE` if H+0.40R is touched after frozen exit inside this window.
- Otherwise it is `TRUE_FAILURE_PROXY`.
- This label is future-defined and may be used only for anatomy, never directly as a trading rule.

## Fixed loss taxonomy
- L0_NEVER_BREAK_REFERENCE_INVALIDATION
- L1_NEVER_BREAK_TIME
- L2_BREAK_FAST_FAIL_5M
- L3_BREAK_FAST_FAIL_10M
- L4_BREAK_FAIL_30M
- L5_BREAK_FAIL_LATE
- L6_BREAK_TIME_OR_OTHER

## Fixed causal observations
Parent path:
- MFE_R / MAE_R
- hold minutes
- entry->break and break->failure timing

Post-exit:
- first completed close > H (reclaim)
- reclaim minutes
- E40 after reclaim
- target visit number using resting-H touch episodes
- fixed snapshots +5/+10/+15/+30/+60m after frozen exit:
  - close_R
  - running MFE_R
  - running MAE_R
  - closes above H
  - closes <= H
  - reclaim by snapshot

## Replication cells
- Central: R360/15
- Clock support: R360/16
- Reference support: R300/15
- Development is discovery/anatomy only.
- Central External + Central RefVal are mandatory directional replication.
- 4 support cells are secondary replication.

## Support gate for next stage
A26 may support A27 only if:
1. Central Development has >=80 latent-recoverable losers and >=80 true-failure proxies, OR each cohort is >=25% of Central Development losers.
2. Latent recoverability is economically material: >=20% of parent losers or >=20% of parent gross-loss dollars.
3. At least 5 fixed causal feature/snapshot dimensions show a non-zero Development separation whose direction replicates in both Central External and Central RefVal.
4. At least 3 of those dimensions also replicate direction in >=3/4 support cells.

No thresholds are optimized in A26. No trade economics are changed. No live bot changes.