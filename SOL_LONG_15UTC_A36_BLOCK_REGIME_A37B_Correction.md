# A37B Correction — Support Counting

A37's first report accidentally counted non-central Development support cells in `support_same_direction`, producing impossible displays such as `5/4`. This violates the A37 preregistration, which defines topology support as exactly four cells: CLOCK_SUPPORT External, CLOCK_SUPPORT Reference Validation, REF_SUPPORT External, and REF_SUPPORT Reference Validation.

A37B changes **only** this support-count implementation. It reuses the exact persisted A37 trade/anatomy ledger and all Development/OOS medians. No feature, threshold, outcome, or sample is changed. A38 is not authorized unless the corrected A37B report still has at least two strong replicated features under the original preregistered grammar.
