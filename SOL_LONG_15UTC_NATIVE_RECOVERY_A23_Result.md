# SOL LONG 15:00 UTC Native Recovery — A23 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A23 calibrates one bounded recovery visit natively inside the A20-supported R360/15 habitat. H2/H3/H4 are Development candidates; only one may be frozen for OOS.

## Central Development

| Lane | N | WR | PF | Exp | Net | 5bps PF | 5bps Exp | 5bps Net | Rescue raw/stress | Overlay PF raw/stress | Overlay net raw/stress | +blocks raw/stress | Pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|
| REC_H2 | 223 | 27.8% | 1.76 | $0.78 | $173.84 | 1.44 | $0.53 | $118.09 | 25.1%/24.7% | 1.35/1.19 | $512.75/$306.75 | 4/4 | YES |
| REC_H3 | 176 | 21.6% | 1.10 | $0.13 | $23.48 | 0.92 | $-0.12 | $-20.52 | 18.8%/18.8% | 1.25/1.11 | $362.39/$168.14 | 3/2 | NO |
| REC_H4 | 126 | 22.2% | 1.47 | $0.46 | $58.13 | 1.18 | $0.21 | $26.63 | 19.8%/19.0% | 1.30/1.15 | $397.04/$215.29 | 4/4 | NO |

Frozen Development winner: **REC_H2**.

## Frozen OOS

| Role | Partition | Cell | Lane | N | PF | Net | 5bps PF | 5bps Net | Overlay PF raw/stress | Overlay net raw/stress |
|---|---|---|---|---:|---:|---:|---:|---:|---|---|
| CENTRAL | external | R360/15 | REC_H2 | 117 | 0.55 | $-219.57 | 0.51 | $-248.82 | 1.16/1.08 | $200.26/$100.76 |
| CENTRAL | reference_validation | R360/15 | REC_H2 | 122 | 1.29 | $37.20 | 1.04 | $6.70 | 1.50/1.28 | $300.53/$185.78 |
| CLOCK_SUPPORT | external | R360/16 | REC_H2 | 121 | 0.76 | $-97.63 | 0.70 | $-127.88 | 1.24/1.14 | $274.18/$175.68 |
| CLOCK_SUPPORT | reference_validation | R360/16 | REC_H2 | 129 | 1.17 | $24.77 | 0.96 | $-7.48 | 1.45/1.23 | $252.89/$143.39 |
| REF_SUPPORT | external | R300/15 | REC_H2 | 107 | 0.65 | $-149.84 | 0.60 | $-176.59 | 1.39/1.29 | $443.53/$344.78 |
| REF_SUPPORT | reference_validation | R300/15 | REC_H2 | 134 | 1.40 | $51.47 | 1.12 | $17.97 | 1.58/1.33 | $328.40/$208.90 |

Validation: **central_ok=False; support positive raw=2/4; support positive 5bps=1/4**.

## Decision

**Status: SOL_LONG_15UTC_NATIVE_RECOVERY_A23_REJECTED_OOS**

A rejected A23 leaves the A20 15:00 habitat parent-only. No OOS retuning.

Research only. Live Baba Bot remains unchanged.
