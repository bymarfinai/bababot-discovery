# BNB F85/F15 Transfer — M4 Path Diagnostics — B27EG Result

Raw BNB 5m coverage: **100.0000%**. B27EF reproduction: **PASS (176 candidates; 170 pooled-major accepted)**. B27EE structural join: **PASS one-to-one**.

This is path diagnosis only. Frozen B27EF exits/PnL were not changed; diagnostic paths continue to the original execution-window end.

## Core contradiction

- Economic losers that nevertheless reached structural H2: **69.7%** (46/66).
- Among all accepted H2 trades, later E10/E20/E30/E50 reach: **83.9% / 71.8% / 59.7% / 44.3%**.

## Source diagnosis

| Source | Accepted | Losses | Loss→H2 | H2-loss→E20 | E20 before exit | E20 after exit | Diagnosis |
|---|---:|---:|---:|---:|---:|---:|---|
| ALT_0330 | 55 | 21 | 76.2% | 18.8% | 0.0% | 18.8% | H2_WITHOUT_EXTENSION |
| RAW_0530 | 51 | 24 | 70.8% | 29.4% | 17.6% | 11.8% | H2_WITHOUT_EXTENSION |
| SHORT_2000 | 64 | 21 | 61.9% | 30.8% | 0.0% | 30.8% | H2_WITHOUT_EXTENSION |

## Winner vs loser path distribution

| Source | Cohort | N | H2 | MFE p25/med/p75 R | MAE p25/med/p75 R | Pre-H2 MAE med R | Post-H2 ext med R | H2→E10/E20/E30/E50 | End return med R |
|---|---|---:|---:|---|---|---:|---:|---|---:|
| ALT_0330 | ALL | 55 | 90.9% | 0.255/0.394/0.706 | 0.316/0.582/0.943 | 0.158 | 0.323 | 86.0%/68.0%/54.0%/34.0% | -0.177 |
| ALT_0330 | WIN | 34 | 100.0% | 0.378/0.544/0.920 | 0.287/0.379/0.579 | 0.176 | 0.413 | 100.0%/91.2%/73.5%/47.1% | 0.140 |
| ALT_0330 | LOSS | 21 | 76.2% | 0.123/0.202/0.259 | 0.823/0.968/1.351 | 0.112 | 0.111 | 56.2%/18.8%/12.5%/6.2% | -0.605 |
| RAW_0530 | ALL | 51 | 86.3% | 0.184/0.448/1.217 | 0.258/0.551/1.187 | 0.149 | 0.461 | 79.5%/68.2%/61.4%/47.7% | -0.087 |
| RAW_0530 | WIN | 27 | 100.0% | 0.455/0.895/1.407 | 0.174/0.300/0.782 | 0.107 | 0.783 | 92.6%/92.6%/81.5%/63.0% | 0.190 |
| RAW_0530 | LOSS | 24 | 70.8% | 0.095/0.184/0.239 | 0.522/1.076/1.493 | 0.328 | 0.128 | 58.8%/29.4%/29.4%/23.5% | -0.417 |
| SHORT_2000 | ALL | 64 | 85.9% | 0.230/0.425/0.892 | 0.128/0.305/0.548 | 0.118 | 0.518 | 85.5%/78.2%/63.6%/50.9% | 0.162 |
| SHORT_2000 | WIN | 43 | 97.7% | 0.368/0.732/1.026 | 0.107/0.251/0.399 | 0.126 | 0.638 | 97.6%/92.9%/76.2%/64.3% | 0.232 |
| SHORT_2000 | LOSS | 21 | 61.9% | 0.081/0.124/0.244 | 0.337/0.672/1.023 | 0.089 | 0.092 | 46.2%/30.8%/23.1%/7.7% | -0.067 |

## Mechanistic readout

- **ALT_0330**: losses=21, H2-losses=16; among H2-losses E20 before/at frozen exit=0, only after frozen exit=3, never by execution end=13. Diagnosis: **H2_WITHOUT_EXTENSION**.
- **RAW_0530**: losses=24, H2-losses=17; among H2-losses E20 before/at frozen exit=3, only after frozen exit=2, never by execution end=12. Diagnosis: **H2_WITHOUT_EXTENSION**.
- **SHORT_2000**: losses=21, H2-losses=13; among H2-losses E20 before/at frozen exit=0, only after frozen exit=4, never by execution end=9. Diagnosis: **H2_WITHOUT_EXTENSION**.

**Status: B27EG_BNB_PATH_DIAGNOSTICS_COMPLETE**

B27EG stops here. No BNB-native target/stop/runner optimization and no decision rule is executed automatically.
