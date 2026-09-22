# SOL Options Liquidity Map V1 — Two-Snapshot Stability Audit

## Status

**PILOT_STABILITY_SUPPORTED — NOT VALIDATED AS A TRADE FILTER**

This audit compares the first two prospectively captured SOL Options Liquidity Map V1 snapshots. It does not alter the frozen V1 calculation and does not authorize a trade rule.

## Snapshots

- A: 2026-09-22T02:29:31.999Z, spot 117.66567841
- B: 2026-09-22T03:49:00.999Z, spot 116.79553659
- Elapsed: ~79.48 minutes
- Spot change: -0.7395%
- Expiry set unchanged: 260922, 260923, 260925

## Concentration-wall stability

All top-three strikes preserved both membership and rank.

### Lower put concentration

| Rank | Strike | Score A | Score B | Score change | OI change | Gamma concentration change |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 116 | 0.443725 | 0.442589 | -0.256% | +0.358% | +18.891% |
| 2 | 110 | 0.106963 | 0.111263 | +4.020% | -0.014% | +16.988% |
| 3 | 100 | 0.101867 | 0.101190 | -0.665% | +0.009% | +1.266% |

### Upper call concentration

| Rank | Strike | Score A | Score B | Score change | OI change | Gamma concentration change |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 120 | 0.508059 | 0.503110 | -0.974% | +1.047% | -5.868% |
| 2 | 122 | 0.099523 | 0.087421 | -12.161% | 0.000% | -42.248% |
| 3 | 130 | 0.071388 | 0.069391 | -2.797% | +0.001% | -6.669% |

Interpretation: the rank structure was stable while gamma concentration moved materially intraday. OI was especially stable. This is encouraging for the positioning-map concept, but two snapshots are insufficient for validation.

## IV layer behavior

The same-day expiry was much less stable than the later expiries.

| Expiry | ATM strike A→B | ATM IV change | Expected-move change |
|---|---|---:|---:|
| 260922 | 118 → 116 | +43.070% | +23.761% |
| 260923 | 118 → 116 | +0.069% | -2.926% |
| 260925 | 118 → 116 | -0.232% | -1.820% |

The 116 lower wall changed from IV_CONFLUENT to NO_IV_CONFLUENCE even though its concentration score moved only -0.256% and its OI increased slightly. Therefore V1 keeps IV confluence as a descriptive overlay only. The current pilot does not support using the 1% confluence label as a trading gate.

## Forward price path after Snapshot A

From 2026-09-22T02:30Z through 03:49Z, SOLUSDT spot traded approximately:

- High: 118.09
- Low: 116.30
- End close: 116.81

Neither primary wall was touched:
- lower top-1 = 116
- upper top-1 = 120

Therefore there is no valid wall-reaction outcome yet.

## Current conclusion

1. The options positioning map passes its first basic stability sanity check.
2. OI-defined wall location is more stable than the near-expiry IV overlay in this pilot.
3. No claim of support/resistance efficacy can be made until a prospectively recorded wall is actually touched.
4. Historical SOL detector trades ending before the first options snapshot must not be joined to these maps.
5. Continue only with causal forward wall-touch observations and future detector events timestamped after the map snapshot.
