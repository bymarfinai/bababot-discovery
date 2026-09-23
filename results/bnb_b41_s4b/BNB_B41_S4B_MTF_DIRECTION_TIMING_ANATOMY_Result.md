# BNB B41-S4B — Multi-Timeframe Direction Timing Anatomy

**Status: BNB_B41_S4B_READY_FOR_S5**

S4B signature: `acab9ae7928bdcbebc3608a1f5818a6b5eaa6a4a782f446a2cc418e8e50adcbc`

Timeframes are event-relative 5m/15m/30m/60m interaction horizons. Candidate timing is nominated on DEV only; REF is holdout validation.

## Multi-timeframe anatomy

| Period | Side | Character | Dir | TF | N180 | 60m | Hit60 | 180m | Hit180 | MFE | MAE | Fav-dom |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | UPPER | C1_CLEAN_REJECTION | SHORT | TF05 | 109 | -0.004x | 47.4% | 0.105x | 61.5% | 0.534x | 0.356x | 58.3% |
| DEV | UPPER | C1_CLEAN_REJECTION | SHORT | TF15 | 79 | 0.015x | 53.0% | 0.094x | 58.2% | 0.487x | 0.392x | 58.0% |
| DEV | UPPER | C1_CLEAN_REJECTION | SHORT | TF30 | 64 | -0.035x | 35.9% | 0.046x | 54.7% | 0.493x | 0.452x | 48.6% |
| DEV | UPPER | C1_CLEAN_REJECTION | SHORT | TF60 | 46 | -0.008x | 46.8% | 0.060x | 58.7% | 0.428x | 0.412x | 48.0% |
| DEV | UPPER | C3_ACCEPTANCE_HOLD | LONG | TF05 | 104 | 0.055x | 56.4% | 0.028x | 54.8% | 0.557x | 0.372x | 54.9% |
| DEV | UPPER | C3_ACCEPTANCE_HOLD | LONG | TF15 | 81 | 0.072x | 59.0% | -0.005x | 48.1% | 0.595x | 0.415x | 53.6% |
| DEV | UPPER | C3_ACCEPTANCE_HOLD | LONG | TF30 | 77 | -0.010x | 46.2% | 0.024x | 53.2% | 0.515x | 0.552x | 47.5% |
| DEV | UPPER | C3_ACCEPTANCE_HOLD | LONG | TF60 | 90 | -0.039x | 45.2% | -0.026x | 47.8% | 0.464x | 0.427x | 48.0% |
| DEV | LOWER | C1_CLEAN_REJECTION | LONG | TF05 | 118 | 0.039x | 54.3% | 0.026x | 55.9% | 0.415x | 0.503x | 48.5% |
| DEV | LOWER | C1_CLEAN_REJECTION | LONG | TF15 | 81 | 0.030x | 56.3% | 0.028x | 54.3% | 0.382x | 0.349x | 52.8% |
| DEV | LOWER | C1_CLEAN_REJECTION | LONG | TF30 | 64 | 0.051x | 60.9% | 0.025x | 51.6% | 0.381x | 0.366x | 53.5% |
| DEV | LOWER | C1_CLEAN_REJECTION | LONG | TF60 | 46 | 0.041x | 56.9% | 0.034x | 60.9% | 0.385x | 0.400x | 46.2% |
| DEV | LOWER | C2_RECLAIM_AFTER_CLOSE | LONG | TF15 | 42 | 0.037x | 56.2% | 0.152x | 66.7% | 0.447x | 0.433x | 44.9% |
| DEV | LOWER | C2_RECLAIM_AFTER_CLOSE | LONG | TF30 | 56 | 0.019x | 54.0% | 0.068x | 60.7% | 0.303x | 0.367x | 43.8% |
| DEV | LOWER | C2_RECLAIM_AFTER_CLOSE | LONG | TF60 | 76 | 0.034x | 55.7% | 0.122x | 64.5% | 0.390x | 0.344x | 54.2% |
| REF | UPPER | C1_CLEAN_REJECTION | SHORT | TF05 | 53 | 0.044x | 54.5% | 0.075x | 54.7% | 0.430x | 0.482x | 51.7% |
| REF | UPPER | C1_CLEAN_REJECTION | SHORT | TF15 | 32 | 0.014x | 57.6% | 0.150x | 78.1% | 0.541x | 0.265x | 63.6% |
| REF | UPPER | C1_CLEAN_REJECTION | SHORT | TF30 | 29 | 0.013x | 58.6% | 0.110x | 65.5% | 0.504x | 0.388x | 55.2% |
| REF | UPPER | C1_CLEAN_REJECTION | SHORT | TF60 | 25 | 0.058x | 60.0% | 0.087x | 68.0% | 0.481x | 0.445x | 48.0% |
| REF | UPPER | C3_ACCEPTANCE_HOLD | LONG | TF05 | 62 | 0.009x | 50.7% | -0.109x | 38.7% | 0.407x | 0.488x | 50.0% |
| REF | UPPER | C3_ACCEPTANCE_HOLD | LONG | TF15 | 43 | 0.013x | 52.2% | -0.079x | 39.5% | 0.452x | 0.567x | 49.0% |
| REF | UPPER | C3_ACCEPTANCE_HOLD | LONG | TF30 | 47 | -0.031x | 46.2% | -0.026x | 48.9% | 0.351x | 0.379x | 46.4% |
| REF | UPPER | C3_ACCEPTANCE_HOLD | LONG | TF60 | 46 | -0.009x | 48.0% | -0.056x | 45.7% | 0.423x | 0.462x | 51.9% |
| REF | LOWER | C1_CLEAN_REJECTION | LONG | TF05 | 58 | 0.034x | 54.2% | 0.094x | 63.8% | 0.539x | 0.384x | 54.8% |
| REF | LOWER | C1_CLEAN_REJECTION | LONG | TF15 | 32 | 0.037x | 60.6% | 0.011x | 50.0% | 0.592x | 0.394x | 47.2% |
| REF | LOWER | C1_CLEAN_REJECTION | LONG | TF30 | 23 | 0.033x | 60.9% | -0.035x | 43.5% | 0.545x | 0.307x | 52.0% |
| REF | LOWER | C1_CLEAN_REJECTION | LONG | TF60 | 19 | -0.023x | 42.1% | -0.066x | 42.1% | 0.413x | 0.442x | 47.4% |
| REF | LOWER | C2_RECLAIM_AFTER_CLOSE | LONG | TF15 | 27 | 0.048x | 55.6% | 0.114x | 63.0% | 0.596x | 0.401x | 59.3% |
| REF | LOWER | C2_RECLAIM_AFTER_CLOSE | LONG | TF30 | 40 | 0.009x | 52.5% | 0.095x | 60.0% | 0.532x | 0.429x | 55.0% |
| REF | LOWER | C2_RECLAIM_AFTER_CLOSE | LONG | TF60 | 42 | -0.025x | 46.5% | 0.029x | 57.1% | 0.578x | 0.365x | 54.5% |
| ALL | UPPER | C1_CLEAN_REJECTION | SHORT | TF05 | 162 | -0.000x | 49.7% | 0.085x | 59.3% | 0.492x | 0.393x | 56.2% |
| ALL | UPPER | C1_CLEAN_REJECTION | SHORT | TF15 | 111 | 0.014x | 54.3% | 0.099x | 64.0% | 0.521x | 0.380x | 59.5% |
| ALL | UPPER | C1_CLEAN_REJECTION | SHORT | TF30 | 93 | -0.016x | 43.0% | 0.053x | 58.1% | 0.494x | 0.440x | 50.5% |
| ALL | UPPER | C1_CLEAN_REJECTION | SHORT | TF60 | 71 | 0.013x | 51.4% | 0.074x | 62.0% | 0.459x | 0.418x | 48.0% |
| ALL | UPPER | C3_ACCEPTANCE_HOLD | LONG | TF05 | 166 | 0.033x | 54.2% | -0.011x | 48.8% | 0.443x | 0.418x | 53.0% |
| ALL | UPPER | C3_ACCEPTANCE_HOLD | LONG | TF15 | 124 | 0.035x | 56.6% | -0.058x | 45.2% | 0.547x | 0.445x | 51.9% |
| ALL | UPPER | C3_ACCEPTANCE_HOLD | LONG | TF30 | 124 | -0.020x | 46.2% | 0.007x | 51.6% | 0.423x | 0.458x | 47.1% |
| ALL | UPPER | C3_ACCEPTANCE_HOLD | LONG | TF60 | 136 | -0.020x | 46.2% | -0.031x | 47.1% | 0.459x | 0.438x | 49.3% |
| ALL | LOWER | C1_CLEAN_REJECTION | LONG | TF05 | 176 | 0.039x | 54.3% | 0.052x | 58.5% | 0.449x | 0.445x | 50.5% |
| ALL | LOWER | C1_CLEAN_REJECTION | LONG | TF15 | 113 | 0.033x | 57.5% | 0.028x | 53.1% | 0.457x | 0.389x | 51.2% |
| ALL | LOWER | C1_CLEAN_REJECTION | LONG | TF30 | 87 | 0.043x | 60.9% | -0.004x | 49.4% | 0.463x | 0.359x | 53.1% |
| ALL | LOWER | C1_CLEAN_REJECTION | LONG | TF60 | 65 | 0.012x | 52.9% | 0.027x | 55.4% | 0.412x | 0.406x | 46.5% |
| ALL | LOWER | C2_RECLAIM_AFTER_CLOSE | LONG | TF15 | 69 | 0.048x | 56.0% | 0.150x | 65.2% | 0.468x | 0.431x | 50.0% |
| ALL | LOWER | C2_RECLAIM_AFTER_CLOSE | LONG | TF30 | 96 | 0.018x | 53.4% | 0.072x | 60.4% | 0.404x | 0.374x | 48.1% |
| ALL | LOWER | C2_RECLAIM_AFTER_CLOSE | LONG | TF60 | 118 | 0.028x | 52.5% | 0.095x | 61.9% | 0.435x | 0.344x | 54.3% |

## DEV-only nominations -> REF holdout

| Side | Character | Dir | Nom TF | DEV N180 | DEV 180m | DEV hit | DEV fav-dom | REF N180 | REF 180m | REF hit | REF fav-dom | Validated |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| UPPER | C1_CLEAN_REJECTION | SHORT | TF05 | 109.0 | 0.105x | 61.5% | 58.3% | 53.0 | 0.075x | 54.7% | 51.7% | YES |
| UPPER | C3_ACCEPTANCE_HOLD | LONG | NO_NOMINATION | — | — | — | — | — | — | — | — | NO |
| LOWER | C1_CLEAN_REJECTION | LONG | NO_NOMINATION | — | — | — | — | — | — | — | — | NO |
| LOWER | C2_RECLAIM_AFTER_CLOSE | LONG | TF60 | 76.0 | 0.122x | 64.5% | 54.2% | 42.0 | 0.029x | 57.1% | 54.5% | YES |

## Validated-class pooled detector

| Period | N | N180 | 180m | Hit180 | MFE | MAE | Fav-dom |
|---|---:|---:|---:|---:|---:|---:|---:|
| DEV | 203 | 185 | 0.119x | 62.7% | 0.465x | 0.349x | 56.7% |
| REF | 102 | 95 | 0.052x | 55.8% | 0.461x | 0.443x | 52.9% |
| ALL | 305 | 280 | 0.091x | 60.4% | 0.465x | 0.364x | 55.4% |

## Gate
- REF-validated LONG class exists: **YES**.
- REF-validated SHORT class exists: **YES**.
- Final S4B gate: **READY FOR B41-S5 ENTRY GEOMETRY**.

No entry, stop, target, trade WR, PF, expectancy, or PnL was optimized.
