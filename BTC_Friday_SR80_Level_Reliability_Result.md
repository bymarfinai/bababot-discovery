# BTC Friday SR80 — Support/Resistance Level Reliability Result

**Verdict: REJECT_SR80_LEVEL_IDENTIFIER**

**Protocol:** frozen before result; research-only; live BBC untouched.

## Dataset / integrity

- Friday dates with touched frozen levels: **137**
- First-touch events: **484**
- Resolved HOLD/BREAK events: **307**
- Outcomes: **179 HOLD / 128 BREAK / 175 ambiguous-touch-bar / 1 ambiguous-later-bar / 1 unresolved**
- Discovery: **95 Friday dates / 222 resolved levels**
- Validation: **42 Friday dates / 85 resolved levels**
- Integrity violations: **0**

## Unconditional level reliability

| Cohort | N | HOLD | BREAK | HOLD rate | Wilson 95% |
|---|---:|---:|---:|---:|---:|
| Discovery | 222 | 128 | 94 | **57.66%** | 51.1%–64.0% |
| Validation | 85 | 51 | 34 | **60.00%** | 49.4%–69.8% |
| Full | 307 | 179 | 128 | **58.31%** | 52.7%–63.7% |

## Discovery-selected high-confidence rule

Exact frozen tree leaf:

`distance_open_atr <= 1.8548097 AND atr_pct <= 0.0093200146 AND approach_ret60_toward > 0.0053614364`

Interpretation only (not a rule change): the frozen level is no farther than about 1.85 ATR from Friday open, Friday-start 1H ATR is no more than about 0.932% of price, and the market has moved more than about 0.536% toward the level over the completed 60 minutes before first touch.

| Cohort | N | HOLD | BREAK | HOLD rate | Wilson 95% |
|---|---:|---:|---:|---:|---:|
| Discovery | 38 | 34 | 4 | **89.47%** | 75.9%–95.8% |
| Validation | 11 | 7 | 4 | **63.64%** | 35.4%–84.8% |
| Full | 49 | 41 | 8 | **83.67%** | 71.0%–91.5% |

### Chronological blocks

| Block | N | HOLD | BREAK | HOLD rate |
|---|---:|---:|---:|---:|
| B1 | 11 | 10 | 1 | **90.91%** |
| B2 | 17 | 15 | 2 | **88.24%** |
| B3 | 13 | 10 | 3 | **76.92%** |
| B4 | 8 | 6 | 2 | **75.00%** |

- Source families represented: **PDAY, SWING, W7**
- Selected support/resistance observations: **25 / 24**
- Positive (>50% HOLD) chronological blocks: **4/4**

## Why it is rejected

The preregistered SR80 promotion gate required validation resolved N >= 12 **and** validation HOLD rate >=80%. The selected leaf produced only **11 validation observations** and **63.64% HOLD**, so it fails both validation requirements. Full-history 83.67% is not sufficient because it is dominated by the discovery sample used to select the leaf.

No threshold retuning, support-only/resistance-only rescue, deeper tree, or runner-up validation is allowed after this result.

This study measures historical first-touch level behavior, not guaranteed future support/resistance and not trade profitability.
