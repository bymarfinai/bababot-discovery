# BNB B34-S1 — Implementation Correction Before Outcome Observation

## Triggered run
- Failed run: `35486818719`
- Failure occurred before G1-G3 outcome tables or any development winner were produced.
- The runner downloaded derivatives metrics and formed 2,128 causal alignments from 3,014 frozen development entries, then aborted.

## Cause
The implementation contained an additional hard abort requiring >=90% raw-parent alignment in development (and >=85% in reference).

Those percentages were **not part of the frozen B34-S1 preregistration**. The preregistration explicitly defines:
- gate N and per-year N on aligned observations;
- participation against aligned G0;
- improvement against aligned G0;
- strict pre-entry causality and <=10m staleness.

The extra raw-coverage abort therefore changed executable feasibility beyond the preregistered protocol.

## Correction
Remove only the non-preregistered 90%/85% aborts.

Keep unchanged:
- frozen B33 F1LE + E1 parent;
- G1/G2/G3 definitions;
- all development thresholds;
- ranking;
- reference-opening rule;
- all reference thresholds;
- strict-before-entry alignment and <=10m staleness;
- no economics before reference pass.

Missing derivatives observations are excluded symmetrically from both a candidate gate and its aligned G0 comparator. Alignment counts by calendar year are now printed and persisted for audit.

## Anti-bias statement
At the time of this correction, no G1/G2/G3 outcome metrics, selected development gate, or reference result from B34-S1 had been observed because the failed run halted before evaluation output.
