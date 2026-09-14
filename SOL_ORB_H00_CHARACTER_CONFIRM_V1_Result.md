# SOL ORB H00 Character Confirmation v1

- Confirmation period: **2020-01-01 to 2021-12-31** (External only)
- Reference Validation 2025–2026: **CLOSED / NOT USED**
- Anchor: **17:00 UTC / 00:00 WIB**
- Frozen character: 15m ORB range >= 0.50% -> upside break -> bullish retest reaction above anchored VWAP -> small BOS above VWAP -> BOS close >= 0.50% above ORB High -> next-5m-open LONG.
- Exit: fixed +60 minutes; roundtrip cost 0.15%; notional USD 500.

## Overall confirmation

| N | Net WR | Net PnL | Exp | PF | Max DD | Max LS | Verdict |
|---:|---:|---:|---:|---:|---:|---:|---|
| 12 | 16.67% | $-55.24 | $-4.60 | 0.091 | $55.65 | 9 | **FAIL** |

## Year diagnostics

| Year | N | Net WR | Net PnL | Exp | PF | Max DD | Max LS |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 0 | nan% | $nan | $nan | nan | $nan | 0 |
| 2021 | 12 | 16.67% | $-55.24 | $-4.60 | 0.091 | $55.65 | 9 |

## Frozen decision gate

- PASS requires N >= 10, net WR >= 60%, net PnL > 0, and PF > 1.0.
- N < 10 is INCONCLUSIVE.
- No threshold/hour/exit tuning is permitted from this run.

## Verdict: **FAIL**

This candidate is rejected. Do not retune the 0.50%/0.50% thresholds against External confirmation. Reference Validation remains closed.
