# BNB LONG Reset V1 — H00 Primary Verdict

Status: **PRIMARY_FAIL**

## Provenance

- GitHub Actions run: `34743590945`
- Workflow: `BNB LONG Reset V1 H00 Primary Discovery`
- Execution commit: `c00c5f6b5b8fa4d622c2c72aa862246266ba7491`
- Artifact id: `10313443314`
- Artifact digest: `sha256:84da8713bb47d6d33f74f0288887b685aa25799fda4754974817f0d035ab91fa`
- Data coverage: **100.0000%**
- Development H00 events: **4384**
- Primary candidates evaluated: **34**
- Full-gate passers: **0**
- OOS 2025+ was **not downloaded and not evaluated**.

## Verdict

No single-feature structural state in H00 (00:00–01:00 WIB) passed the preregistered pooled + fixed-horizon + cross-year + quarter-hour-anchor gates.

This is a valid market-character rejection, not a tooling/data failure.

## Strongest Near-Passers

| Rule | N | WR | Mean consensus return | PF | Horizons | Anchors | Years >55% | Pooled | Horizon | Era | Anchor | Final |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|
| `range_location_240m__LOW` | 1365 | 56.70% | +0.0641% | 1.239 | 3/3 | 4/4 | 2/3 | PASS | PASS | **FAIL** | PASS | FAIL |
| `drive_240m__LOW` | 1391 | 57.08% | +0.0788% | 1.284 | 3/3 | 4/4 | 2/3 | PASS | PASS | **FAIL** | PASS | FAIL |
| `ema20_ema50_spread__LOW` | 1374 | 57.28% | +0.0704% | 1.255 | 3/3 | 4/4 | 2/3 | PASS | PASS | **FAIL** | PASS | FAIL |
| `rv_ratio_60_240__HIGH` | 1464 | 54.92% | +0.0407% | 1.156 | 1/3 | 3/4 | 1/3 | FAIL | FAIL | FAIL | PASS | FAIL |
| `ema20_reclaim__TRUE` | 312 | 55.13% | +0.0434% | 1.178 | 2/3 | 2/4 | 2/3 | FAIL | PASS | FAIL | FAIL | FAIL |

## Why the three strongest fail

### `range_location_240m__LOW`

Pooled economics, all three diagnostic horizons, and all four quarter-hour anchors are supportive. It fails the preregistered cross-year gate because 2022 is not supportive: WR **52.19%**, mean **+0.0049%**, PF **1.013** (PF is below the required 1.05).

2023 and 2024 are supportive, but the rule requires every Development year to clear the minimum robustness floor.

### `drive_240m__LOW`

Pooled WR **57.08%**, PF **1.284**, 3/3 horizons and 4/4 anchors all pass. It fails the era gate because 2022 is negative: WR **50.12%**, mean **-0.0057%**, PF **0.984**.

### `ema20_ema50_spread__LOW`

Pooled WR **57.28%**, PF **1.255**, 3/3 horizons and 4/4 anchors pass. It fails the era gate because 2022 is negative: WR **51.81%**, mean **-0.0086%**, PF **0.977**.

## Locked interpretation

H00 contains signs of a later-era LONG tendency when BNB is low in its 4-hour range / weak on the 4-hour drive / below the EMA20-EMA50 regime, but that tendency is **not stable across 2022–2024** under the reset methodology. Therefore it must not be promoted as a primary character.

No threshold is relaxed. No pairwise secondary filter is allowed to rescue H00 after this result. No OOS is opened.

## Next state

Per Reset V1, H00 is now a persisted negative structural map. The next eligible discovery habitat is **H01 = 01:00–02:00 WIB**, using the same preregistered baseline unchanged.