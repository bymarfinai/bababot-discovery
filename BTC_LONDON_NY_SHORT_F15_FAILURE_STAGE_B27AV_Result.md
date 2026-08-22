# B27AV — BTC London->NY SHORT F15 Failure-Stage Decomposition — Result

**Audit status: PASS.** Frozen B27AT E20 identities/PnL and B27AM H2/acceptance timestamps joined one-to-one before stage attribution.

Pooled-major N: **163**; realized E20-hybrid total: **$-15.058**.

## Causal stage flow before actual exit

**F15 fill 163 → H2 before exit 115 → strict close < L known by exit 97 → E20 activated 92.**

## Failure-stage economics — pooled major

| Stage bucket | N | WR | PF | Exp/trade $ | Total $ | Share of non-activated drag | F65 invalid | Time exit | Late H2 after exit | Late acceptance after exit |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PRE_H2_FAILURE | 48 | 0.0% | 0.000 | -4.266 | -204.766 | 74.9% | 33 | 15 | 5 | 4 |
| H2_NO_ACCEPTANCE | 12 | 0.0% | 0.000 | -3.198 | -38.373 | 14.0% | 4 | 8 | 0 | 0 |
| ACCEPTED_NO_E20 | 11 | 18.2% | 0.068 | -2.752 | -30.268 | 11.1% | 5 | 6 | 0 | 0 |
| E20_ACTIVATED | 92 | 92.4% | 49.134 | 2.808 | 258.349 | - | 0 | 0 | 0 | 4 |

## Same buckets by partition

| Partition | Stage bucket | N | WR | PF | Exp/trade $ | Total $ | F65 invalid | Time exit |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| external | PRE_H2_FAILURE | 13 | 0.0% | 0.000 | -3.450 | -44.847 | 4 | 9 |
| external | H2_NO_ACCEPTANCE | 5 | 0.0% | 0.000 | -3.297 | -16.487 | 2 | 3 |
| external | ACCEPTED_NO_E20 | 4 | 25.0% | 0.146 | -2.947 | -11.789 | 1 | 3 |
| external | E20_ACTIVATED | 28 | 92.9% | 83.444 | 4.233 | 118.511 | 0 | 0 |
| development | PRE_H2_FAILURE | 24 | 0.0% | 0.000 | -4.644 | -111.467 | 19 | 5 |
| development | H2_NO_ACCEPTANCE | 5 | 0.0% | 0.000 | -3.143 | -15.715 | 2 | 3 |
| development | ACCEPTED_NO_E20 | 3 | 0.0% | 0.000 | -2.080 | -6.239 | 1 | 2 |
| development | E20_ACTIVATED | 47 | 91.5% | 50.169 | 2.382 | 111.937 | 0 | 0 |
| reference_validation | PRE_H2_FAILURE | 11 | 0.0% | 0.000 | -4.405 | -48.453 | 10 | 1 |
| reference_validation | H2_NO_ACCEPTANCE | 2 | 0.0% | 0.000 | -3.086 | -6.171 | 0 | 2 |
| reference_validation | ACCEPTED_NO_E20 | 4 | 25.0% | 0.015 | -3.060 | -12.241 | 3 | 1 |
| reference_validation | E20_ACTIVATED | 17 | 94.1% | 17.877 | 1.641 | 27.901 | 0 | 0 |
| august | PRE_H2_FAILURE | 0 | - | - | - | 0.000 | 0 | 0 |
| august | H2_NO_ACCEPTANCE | 1 | 0.0% | 0.000 | -2.420 | -2.420 | 1 | 0 |
| august | ACCEPTED_NO_E20 | 0 | - | - | - | 0.000 | 0 | 0 |
| august | E20_ACTIVATED | 0 | - | - | - | 0.000 | 0 | 0 |

## Failure bucket × actual exit reason

| Stage bucket | PRE_ACT_CLOSE_INVALIDATION_F65 | PROFIT_CEILING_GAP_OPEN | PROFIT_CEILING_HIT | TIME_EXIT_SESSION_END |
|---|---:|---:|---:|---:|
| PRE_H2_FAILURE | 33 | 0 | 0 | 15 |
| H2_NO_ACCEPTANCE | 4 | 0 | 0 | 8 |
| ACCEPTED_NO_E20 | 5 | 0 | 0 | 6 |
| E20_ACTIVATED | 0 | 62 | 30 | 0 |

## Frozen diagnostic readout

Largest failure-stage PnL drag: **PRE_H2_FAILURE**, N=48, total **$-204.766**.
Non-activated total remains **$-273.407**; B27AV does not convert this attribution into a filter.

No threshold, filter, alternate stop, entry, TP, regime, candle rule, or runner parameter was selected. Research only; live BBC unchanged.
