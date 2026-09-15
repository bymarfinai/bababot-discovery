# BNB B29-B2 — Entry Discovery — Frozen Stop Verdict

**Final status: `BNB_B29_B2_ENTRY_DISCOVERY_REJECT`**

B2-v1 is frozen after a valid preregistered run on the immutable accepted B29-A1 artifact and the unchanged B1J winning character.

## Reproducibility identity
- Branch: `bnb-b29-walkforward-reset`
- Preregistration commit: `9dbaae90908bf34415d685e5e931fd2c95bee730`
- Valid dedicated run: `34938306619`
- Valid run head: `ea4061721a5594eb46ad3159de8b4e6e21f22eea`
- Persisted evidence commit: `653435d98eca36772a68597421aeab8bff9484ed`
- Reproducibility artifact: `10383539874`
- Artifact digest: `sha256:27d071a0bd8700b538407ddb53dde2441d1ec24c35e0a782e6af6e75573eb6c5`
- Accepted A1 source artifact: `10336102957`
- Accepted A1 fingerprint SHA256: `eae8f278d45e7c3035b03900b30e315b16a241c1fbc5fda39231681390c25cfa`
- Frozen B1J character events: 451, with era counts 97 / 82 / 114 / 93 / 65 for 2022 / 2023 / 2024 / 2025 / 2026.

## Valid scientific result
Exactly one of the 10 preregistered entry policies passed every development gate:

`E0_EVENT_CLOSE`

Development 2022-2024:
- N = 293
- participation = 100%
- primary event-anchor +60m hit = 61.09%
- Wilson 95% lower bound = 55.40%
- worst development-era hit = 58.54%
- 2022 = 60.82%
- 2023 = 58.54%
- 2024 = 63.16%
- event-anchor +120m hit = 58.02%
- entry+60m hit = 61.09%
- BH-FDR q = 0.000291258

All delayed/conditional policies were rejected by at least one frozen development gate. In particular, waiting did not provide a sufficiently robust improvement after accounting for sample size and auxiliary-horizon behaviour.

Reference validation for `E0_EVENT_CLOSE`:
- 2025: N=93, hit=55.91%
- 2026: N=65, hit=58.46%
- combined reference N=158
- combined reference primary hit = **56.96%**
- reference event-anchor +120m hit = 58.23%
- reference entry+60m hit = 56.96%
- pooled 2022-2026 N=451
- pooled primary hit = 59.65%
- pooled Wilson 95% lower bound = 55.05%
- every era is >50%

The reference primary-hit gate was preregistered at **>=57.00%**. The observed 56.96% therefore fails the gate. Numerically this is 90 wins out of 158 reference observations; 91 wins would have been 57.59%, but the observed result must not be rounded or rescued after the fact.

Therefore **no B2-v1 entry policy is promoted to TP/SL discovery**.

## Interpretation
The historical evidence still says something useful:
- the B1J character remains structurally robust;
- the earliest causal entry, the event close, is the only entry mechanism that survived the entire development screen;
- waiting 15-30 minutes generally did not improve robustness enough and sometimes materially damaged the edge;
- B2 failed on a frozen reference threshold by a very small margin rather than by structural collapse.

This does **not** authorize relaxing the 57% gate or treating `E0_EVENT_CLOSE` as a passed entry rule.

## Stop rule
Do not rescue B2-v1 by:
- changing 57.00% to 56.96% or rounding the result;
- changing the B1J character;
- dropping 2025 or 2026;
- selecting a delayed policy that failed development;
- adding hour/session filters;
- changing the primary anchor;
- adding TP/SL and calling the result a continuation of B2-v1.

Any further execution work must be a new scientific identity with a materially different hypothesis, or use genuinely new future shadow observations to test the provisional event-close behavior without reusing historical outcomes to relax B2-v1.

No live orders were placed.
