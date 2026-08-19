# Tuesday A5.11 Forward Evaluator — Synthetic Gate Test

**Status: PASS**

No market data is used. These fixtures only verify the preregistered decision-state implementation.

| Case | Rows | Expected | Actual | Result |
|---|---:|---|---|---|
| F0_empty | 0 | `OBSERVE_ONLY` | `OBSERVE_ONLY` | PASS |
| F1_12_supportive | 12 | `EARLY_SUPPORTIVE` | `EARLY_SUPPORTIVE` | PASS |
| F2_26_strong_positive | 26 | `CANDIDATE_REVIEW_ELIGIBLE` | `CANDIDATE_REVIEW_ELIGIBLE` | PASS |
| F3_52_strong_positive | 52 | `LIVE_ENGINEERING_REVIEW_ELIGIBLE` | `LIVE_ENGINEERING_REVIEW_ELIGIBLE` | PASS |
| F3_52_strong_negative | 52 | `FORWARD_EDGE_REJECTED` | `FORWARD_EDGE_REJECTED` | PASS |
| integrity_bad_fingerprint | 12 | `DATA_INTEGRITY_HOLD` | `DATA_INTEGRITY_HOLD` | PASS |
| integrity_duplicate_date | 12 | `DATA_INTEGRITY_HOLD` | `DATA_INTEGRITY_HOLD` | PASS |

A PASS does not provide trading evidence; it only proves the evaluator maps fabricated states to the frozen protocol decisions correctly.
