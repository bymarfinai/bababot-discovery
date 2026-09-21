# BNB B38-S25 — Weak TP1 Body Runner-Skip Validation

Frozen E2 signature: `d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267`
Frozen S24 weak-body cut: `tp1_bar_body_r <= 0.016161308565709815R`

## Overall economics

| Period | Config | + / - / 0 | Positive rate | Med +R | Exp | Total R | PF | Max DD | Max L | ΔR vs S23 | ΔR vs S20 | S23 + retained |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | BASELINE_TP1 | 325/115/0 | 73.9% | 0.224R | 0.035R | 15.312R | 1.133 | 15.588R | 5 | —R | —R | — |
| DEV | S20_IMMEDIATE | 315/125/0 | 71.6% | 0.229R | 0.047R | 20.478R | 1.190 | 12.520R | 5 | —R | —R | — |
| DEV | S23_ADAPTIVE_MAJOR_50_50_BE | 315/125/0 | 71.6% | 0.231R | 0.053R | 23.242R | 1.216 | 12.044R | 5 | —R | —R | — |
| DEV | S25_SKIP_WEAK_TP1_BODY | 315/125/0 | 71.6% | 0.231R | 0.053R | 23.181R | 1.215 | 12.002R | 5 | -0.062R | 2.703R | 315/315 |
| REF | BASELINE_TP1 | 201/71/0 | 73.9% | 0.183R | -0.002R | -0.519R | 0.993 | 10.563R | 4 | —R | —R | — |
| REF | S20_IMMEDIATE | 199/73/0 | 73.2% | 0.181R | 0.005R | 1.405R | 1.021 | 10.773R | 4 | —R | —R | — |
| REF | S23_ADAPTIVE_MAJOR_50_50_BE | 199/73/0 | 73.2% | 0.182R | 0.007R | 1.872R | 1.027 | 10.674R | 4 | —R | —R | — |
| REF | S25_SKIP_WEAK_TP1_BODY | 199/73/0 | 73.2% | 0.183R | 0.009R | 2.482R | 1.036 | 10.415R | 4 | 0.610R | 1.077R | 199/199 |

## Runner cohort after weak-body skip

| Period | Candidates | Weak-body skips | Active runners | Major hit | BE | Ambig | Open | Skip full-TP1 R | Skip old-S23 R | Skip ΔR | Old skip HIT/BE/Amb |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | 90 | 23 | 67 | 38 | 27 | 2 | 0 | 2.548R | 2.610R | -0.062R | 6/16/1 |
| REF | 56 | 25 | 31 | 19 | 12 | 0 | 0 | 1.318R | 0.707R | 0.610R | 2/22/1 |

## Annual S25 stability

| Year | Config | Exp | Total R | + / - | ΔR vs S23 |
|---:|---|---:|---:|---:|---:|
| 2022 | BASELINE_TP1 | 0.141R | 21.286R | 116/35 | —R |
| 2022 | S20_IMMEDIATE | 0.154R | 23.281R | 111/40 | —R |
| 2022 | S23_ADAPTIVE_MAJOR_50_50_BE | 0.164R | 24.732R | 111/40 | —R |
| 2022 | S25_SKIP_WEAK_TP1_BODY | 0.164R | 24.749R | 111/40 | 0.017R |
| 2023 | BASELINE_TP1 | -0.053R | -7.685R | 101/43 | —R |
| 2023 | S20_IMMEDIATE | -0.047R | -6.776R | 100/44 | —R |
| 2023 | S23_ADAPTIVE_MAJOR_50_50_BE | -0.045R | -6.551R | 100/44 | —R |
| 2023 | S25_SKIP_WEAK_TP1_BODY | -0.045R | -6.501R | 100/44 | 0.050R |
| 2024 | BASELINE_TP1 | 0.012R | 1.710R | 108/37 | —R |
| 2024 | S20_IMMEDIATE | 0.027R | 3.972R | 104/41 | —R |
| 2024 | S23_ADAPTIVE_MAJOR_50_50_BE | 0.035R | 5.061R | 104/41 | —R |
| 2024 | S25_SKIP_WEAK_TP1_BODY | 0.034R | 4.932R | 104/41 | -0.129R |
| 2025 | BASELINE_TP1 | -0.028R | -5.143R | 137/49 | —R |
| 2025 | S20_IMMEDIATE | -0.019R | -3.521R | 136/50 | —R |
| 2025 | S23_ADAPTIVE_MAJOR_50_50_BE | -0.015R | -2.727R | 136/50 | —R |
| 2025 | S25_SKIP_WEAK_TP1_BODY | -0.012R | -2.303R | 136/50 | 0.424R |
| 2026 | BASELINE_TP1 | 0.054R | 4.624R | 64/22 | —R |
| 2026 | S20_IMMEDIATE | 0.057R | 4.926R | 63/23 | —R |
| 2026 | S23_ADAPTIVE_MAJOR_50_50_BE | 0.053R | 4.599R | 63/23 | —R |
| 2026 | S25_SKIP_WEAK_TP1_BODY | 0.056R | 4.785R | 63/23 | 0.186R |

## Interpretation boundary
S25 validates exactly one frozen weak-TP1-body skip rule.
No threshold, feature combination, runner split, or target is retuned from S25 outcomes.
A promotion requires unchanged REF improvement/preservation and positive-trade retention.
