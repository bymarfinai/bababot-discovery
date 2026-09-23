# BNB B41-S5 — Entry Geometry Discovery

**Status: BNB_B41_S5_READY_FOR_S6**

S5 signature: `5f2e2977c746c47b6c16eda35c72afc7993fe123713f5b011ad281c1317f5241`

Direction and timeframe are frozen from S4B. Limit candidates are judged against market-at-detector with a fixed detector+180m endpoint.

## Candidate geometry

| Period | Side | Dir | TF | Candidate | Fill | N180 | 180m | Hit180 | MFE | MAE | Fav-dom | Missed baseline wins |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | UPPER | SHORT | TF05 | E0_MARKET | 100.0% | 109 | 0.105x | 61.5% | 0.271x | 0.263x | 55.0% | 0.0% |
| DEV | UPPER | SHORT | TF05 | E1_R25 | 92.5% | 101 | 0.133x | 61.4% | 0.282x | 0.214x | 55.4% | 9.0% |
| DEV | UPPER | SHORT | TF05 | E2_R50 | 89.2% | 97 | 0.146x | 61.9% | 0.293x | 0.211x | 56.7% | 11.9% |
| DEV | UPPER | SHORT | TF05 | E3_WALL | 72.5% | 81 | 0.105x | 61.7% | 0.299x | 0.277x | 51.9% | 31.3% |
| DEV | LOWER | LONG | TF60 | E0_MARKET | 100.0% | 76 | 0.122x | 64.5% | 0.254x | 0.224x | 50.0% | 0.0% |
| DEV | LOWER | LONG | TF60 | E1_R25 | 74.7% | 57 | 0.105x | 63.2% | 0.249x | 0.201x | 54.4% | 32.7% |
| DEV | LOWER | LONG | TF60 | E2_R50 | 56.6% | 45 | 0.104x | 62.2% | 0.243x | 0.190x | 48.9% | 51.0% |
| DEV | LOWER | LONG | TF60 | E3_WALL | 31.3% | 24 | 0.083x | 66.7% | 0.282x | 0.292x | 54.2% | 77.6% |
| REF | UPPER | SHORT | TF05 | E0_MARKET | 100.0% | 53 | 0.075x | 54.7% | 0.275x | 0.196x | 62.3% | 0.0% |
| REF | UPPER | SHORT | TF05 | E1_R25 | 89.7% | 47 | 0.001x | 51.1% | 0.285x | 0.221x | 57.4% | 20.7% |
| REF | UPPER | SHORT | TF05 | E2_R50 | 84.5% | 44 | 0.000x | 50.0% | 0.284x | 0.271x | 56.8% | 31.0% |
| REF | UPPER | SHORT | TF05 | E3_WALL | 77.6% | 40 | 0.010x | 52.5% | 0.278x | 0.284x | 52.5% | 44.8% |
| REF | LOWER | LONG | TF60 | E0_MARKET | 100.0% | 42 | 0.029x | 57.1% | 0.310x | 0.262x | 57.1% | 0.0% |
| REF | LOWER | LONG | TF60 | E1_R25 | 81.8% | 35 | 0.072x | 60.0% | 0.259x | 0.236x | 57.1% | 12.5% |
| REF | LOWER | LONG | TF60 | E2_R50 | 68.2% | 29 | 0.102x | 55.2% | 0.222x | 0.206x | 55.2% | 33.3% |
| REF | LOWER | LONG | TF60 | E3_WALL | 45.5% | 19 | 0.018x | 57.9% | 0.254x | 0.163x | 57.9% | 62.5% |
| ALL | UPPER | SHORT | TF05 | E0_MARKET | 100.0% | 162 | 0.085x | 59.3% | 0.273x | 0.226x | 57.4% | 0.0% |
| ALL | UPPER | SHORT | TF05 | E1_R25 | 91.6% | 148 | 0.091x | 58.1% | 0.283x | 0.218x | 56.1% | 12.5% |
| ALL | UPPER | SHORT | TF05 | E2_R50 | 87.6% | 141 | 0.095x | 58.2% | 0.293x | 0.232x | 56.7% | 17.7% |
| ALL | UPPER | SHORT | TF05 | E3_WALL | 74.2% | 121 | 0.062x | 58.7% | 0.286x | 0.279x | 52.1% | 35.4% |
| ALL | LOWER | LONG | TF60 | E0_MARKET | 100.0% | 118 | 0.095x | 61.9% | 0.265x | 0.225x | 52.5% | 0.0% |
| ALL | LOWER | LONG | TF60 | E1_R25 | 77.2% | 92 | 0.078x | 62.0% | 0.253x | 0.220x | 55.4% | 26.0% |
| ALL | LOWER | LONG | TF60 | E2_R50 | 60.6% | 74 | 0.103x | 59.5% | 0.243x | 0.197x | 51.4% | 45.2% |
| ALL | LOWER | LONG | TF60 | E3_WALL | 36.2% | 43 | 0.059x | 62.8% | 0.255x | 0.252x | 55.8% | 72.6% |

## DEV nomination -> REF holdout -> final entry

| Side | Dir | TF | DEV nomination | DEV fill | DEV 180m | DEV hit | DEV MAE | DEV missed wins | REF fill | REF 180m | REF hit | REF MAE | REF missed wins | Final |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| UPPER | SHORT | TF05 | E1_R25 | 92.5% | 0.133x | 61.4% | 0.214x | 9.0% | 89.7% | 0.001x | 51.1% | 0.221x | 20.7% | **E0_MARKET** |
| LOWER | LONG | TF60 | E0_MARKET | 100.0% | 0.122x | 64.5% | 0.224x | 0.0% | 100.0% | 0.029x | 57.1% | 0.262x | 0.0% | **E0_MARKET** |

## Final frozen-entry pooled evidence

| Period | Signals | Filled | Fill | N180 | 180m | Hit180 | MFE | MAE | Fav-dom |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | 203 | 203 | 100.0% | 185 | 0.119x | 62.7% | 0.263x | 0.226x | 53.0% |
| REF | 102 | 102 | 100.0% | 95 | 0.052x | 55.8% | 0.293x | 0.224x | 60.0% |
| ALL | 305 | 305 | 100.0% | 280 | 0.091x | 60.4% | 0.271x | 0.225x | 55.4% |

## Gate
Each validated S4B direction class now has a frozen final entry geometry.
**READY FOR B41-S6 STRUCTURAL INVALIDATION / SL DISCOVERY.**

S5 did not optimize stop, target, trade WR, PF, expectancy, leverage, or PnL.
