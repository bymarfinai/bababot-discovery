# BNB B29-B2S — Parent Invalidation Halt

**Status: BNB_B29_B2S_HALTED_PARENT_REJECTED**

B2S was created only to prospectively confirm the frozen B1J character + B2 E0 event-close entry after the original B1J PASS.

B29-B2E subsequently exposed a numerical classification defect in B1J: two exact-flat +60m outcomes had been counted as wins because chained floating-point returns produced +2.22e-16. Exact raw close semantics correct the winning character from 269/451 (59.65%) to 267/451 (59.20%), lowering its pooled Wilson 95% lower bound from just above 55% to 54.6068%, below the frozen B1J >55% gate.

The authoritative correction is documented in `research/BNB_B29_B1J_NUMERICAL_CORRECTION_VERDICT.md`, with corrected status `BNB_B29_B1J_CORRECTED_REJECT`.

Therefore B2S is halted rather than allowed to validate a parent character that no longer passes its own preregistered gate. The prospective ledger is preserved for audit but must not be used to rescue B1J-v1.

No B3 TP/SL discovery and no live trading are authorized from this lineage.