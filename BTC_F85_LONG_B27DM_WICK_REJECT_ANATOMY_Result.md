# B27DM Wick-Reject Anatomy

Accepted pooled-major wick-reject trades: **92**.

## Where the E20 wick-reject candle closed

| Close area | N | Share |
|---|---:|---:|
| E10–E20 (masih sangat dekat TP) | 59 | 64.1% |
| H–E10 (masih di atas H) | 20 | 21.7% |
| F85–H (profit area, di bawah H) | 9 | 9.8% |
| Net-BEP–F85 | 0 | 0.0% |
| Entry–Net-BEP (gross +, net ~0/-) | 0 | 0.0% |
| Di bawah entry (gross loss) | 4 | 4.3% |

## Key thresholds

- Close still **above H**: **79/92 (85.9%)**.
- Close still **at/above F85**: **88/92 (95.7%)**.
- Close still **at/above entry price**: **87/92 (94.6%)**.
- Close still **at/above net-BEP price** (fee-adjusted): **82/92 (89.1%)**.
- Exit is still **net profitable after $0.40 fee**: **82/92 (89.1%)**.
- Exit ends **below entry (gross loss)**: **5/92 (5.4%)**.

## Distribution statistics

- Median close location: **E+14.0** relative to H (where H=E0, E20=+0.20R).
- Mean close location: **E+9.9**.
- Median give-back from E20: **6.0% of R**.
- Mean give-back from E20: **10.1% of R**.
- Median exit vs entry: **+0.391%**.
- Median exit vs E20: **-0.111%**.
- Median net PnL of wick rejects: **$+1.55**.
- Mean net PnL of wick rejects: **$+1.76**.

## Per-zone wick-reject location

| Zone | N | Above H | Above entry | Above net-BEP | Net profitable | Median ext vs H | Median net PnL |
|---|---:|---:|---:|---:|---:|---:|---:|
| ALT_0330 | 32 | 81.2% | 90.6% | 87.5% | 87.5% | E+12.6 | $+1.18 |
| RAW_0530 | 22 | 90.9% | 100.0% | 90.9% | 90.9% | E+15.4 | $+1.71 |
| LONDON | 26 | 84.6% | 96.2% | 88.5% | 88.5% | E+13.6 | $+2.06 |
| RAW_2330 | 12 | 91.7% | 91.7% | 91.7% | 91.7% | E+13.6 | $+1.54 |
