# ETH London F85 — Breakout Entry Trading Test M3D — Result

Raw ETH 5-minute coverage: **100.0000%**.
Trading rule: confirmed breakout -> next 5m open entry; target E20; completed close below F35 invalidates; otherwise exit at session end.
Illustrative notional **$500**, round-trip fee **$0.40**.

## Hasil trading

| Periode | Trade | Win | Loss | WR | PF | Net | Rata-rata / trade | Loss beruntun maks |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020-2021 | 40 | 32 | 8 | 80.0% | 1.28 | $+11.33 | $+0.28 | 2 |
| 2022-2024 | 43 | 29 | 14 | 67.4% | 0.42 | $-45.13 | $-1.05 | 4 |
| 2025-Jul 2026 | 22 | 19 | 3 | 86.4% | 3.56 | $+22.51 | $+1.02 | 1 |
| Semua periode utama | 105 | 80 | 25 | 76.2% | 0.91 | $-11.28 | $-0.11 | 4 |

## Cara trade berakhir

| Akhir trade | Jumlah |
|---|---:|
| Target E20 kena | 84 |
| Close di bawah F35 | 8 |
| Masih terbuka sampai sesi selesai | 13 |

## Sensitivitas slippage 5 bps

| Trade | WR | PF | Net | Loss beruntun maks |
|---:|---:|---:|---:|---:|
| 105 | 60.0% | 0.55 | $-63.79 | 6 |

Skipped breakout cases: ENTRY_OPEN_AT_OR_ABOVE_TARGET=14, NO_NEXT_BAR_INSIDE_SESSION=1.

**Status: ETH_LONDON_F85_BREAKOUT_ENTRY_M3D_COMPLETED**

Research only. No parameter optimization and no live BBC change. Stop after M3D.
