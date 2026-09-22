# SOL Options Liquidity Map V1 — First Prospective Snapshot

**Status: OPTIONS_MAP_CAPTURE_READY**

- Snapshot: **2026-09-22T02:29:31.999Z**
- SOL options index: **117.6657**
- Expiries used: **260922, 260923, 260925**
- Complete chain rows used: **108**

## IV expected-move bands

| Expiry | ATM strike | ATM mark IV | Expected move | Floor | Ceiling |
|---|---:|---:|---:|---:|---:|
| 260922 | 118.00 | 0.7571 | 2.234 | 115.432 | 119.900 |
| 260923 | 118.00 | 0.7939 | 5.422 | 112.244 | 123.087 |
| 260925 | 118.00 | 0.7266 | 8.042 | 109.624 | 125.708 |

## Lower map — put concentration

| Rank | Strike | Score | Mean OI share | Mean gamma share | Nearest IV band | Distance |
|---:|---:|---:|---:|---:|---|---:|
| 1 | 116.00 | 0.4437 | 0.3449 | 0.5426 | 260922 | 0.483% |
| 2 | 110.00 | 0.1070 | 0.0635 | 0.1504 | 260925 | 0.320% |
| 3 | 100.00 | 0.1019 | 0.1628 | 0.0410 | 260925 | 8.179% |

## Upper map — call concentration

| Rank | Strike | Score | Mean OI share | Mean gamma share | Nearest IV band | Distance |
|---:|---:|---:|---:|---:|---|---:|
| 1 | 120.00 | 0.5081 | 0.4610 | 0.5551 | 260922 | 0.085% |
| 2 | 122.00 | 0.0995 | 0.1147 | 0.0843 | 260923 | 0.924% |
| 3 | 130.00 | 0.0714 | 0.0785 | 0.0643 | 260925 | 3.648% |

## Guardrail

This is the first prospective map. It is descriptive only and is not a validated SOL trade filter.
Gamma × OI is treated as concentration magnitude only, not dealer GEX.
