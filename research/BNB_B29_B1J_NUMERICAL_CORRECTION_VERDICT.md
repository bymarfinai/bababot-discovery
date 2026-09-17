# BNB B29-B1J — Numerical Classification Correction Verdict

## Status
**`BNB_B29_B1J_CORRECTED_REJECT`**

This document preserves the original B1J-v1 result for auditability but supersedes its scientific PASS verdict after B2E exposed a floating-point classification defect in the B1J forward-return chaining implementation.

This is a tooling/numerical correction only. No character clause, event timestamp, cooldown, horizon, development/reference split, or gate is changed.

## Defect
B1J defined a LONG directional hit as exact forward close-to-close return `> 0`.

The accepted A1 fingerprint stores 15-minute returns. B1J reconstructed longer forward returns by multiplying chained floating-point growth factors. For two frozen winning-character events whose raw entry close and exact +60m close were equal, the chained computation produced `+2.220446049250313e-16` instead of exact zero. Those two flat outcomes were therefore incorrectly classified as WIN because `2.22e-16 > 0`.

Affected winning-character event timestamps:
- `2023-08-26 23:00:00 UTC`
- `2026-03-26 06:30:00 UTC`

A third exact-flat +60m event (`2026-06-02 05:45:00 UTC`) already reconstructed as exactly zero and was correctly classified LOSS in the original B1J implementation.

B29-B2E independently read the raw Binance Vision 5-minute endpoint closes for the exact same 451 frozen character events. Its path-oracle integrity check achieved 100% +60m coverage, zero endpoint mismatches above 5e-6, and max raw-vs-immutable endpoint difference effectively zero. Exact raw endpoint semantics therefore establish that the two epsilon-positive cases are flat, not wins.

## Corrected +60m counts
The event universe is unchanged at 451.

| Era | N | Original wins / hit | Corrected wins / hit |
|---|---:|---:|---:|
| 2022 | 97 | 59 / 60.82% | 59 / 60.82% |
| 2023 | 82 | 48 / 58.54% | 47 / 57.32% |
| 2024 | 114 | 72 / 63.16% | 72 / 63.16% |
| 2025 | 93 | 52 / 55.91% | 52 / 55.91% |
| 2026 | 65 | 38 / 58.46% | 37 / 56.92% |
| Pooled | 451 | 269 / 59.65% | **267 / 59.20%** |

Development 2022-2024:
- corrected wins: 178 / 293
- corrected hit: **60.75%**
- corrected Wilson 95% lower bound: **55.0551%**

Reference 2025+2026:
- corrected wins: 89 / 158
- corrected hit: **56.33%**

Pooled 2022-2026:
- corrected wins: 267 / 451
- corrected hit: **59.20%**
- corrected Wilson 95% lower bound: **54.6068%**

## Frozen B1J gate impact
The original B1J winner required pooled 2022-2026 Wilson 95% lower bound **>55.0%**.

Correct exact-zero classification yields **54.6068%**, so the frozen winner fails that gate.

The other two preregistered B1J reference candidates already failed their frozen reference gates and are not eligible as replacements.

Therefore the valid corrected B1J-v1 status is:

**`BNB_B29_B1J_CORRECTED_REJECT`**

## Downstream consequence
- The original B1J PASS must not be used as authorization to advance execution discovery.
- B2 was already formally REJECTED and remains rejected.
- B2S prospective shadow should be halted because its parent character no longer passes B1J after the numerical correction.
- B2E remains useful as a diagnostic of the same frozen candidate, but its result cannot rescue B1J.
- No B3 TP/SL discovery or live trading is authorized from this lineage.

## Stop rule
Do not rescue B1J-v1 by adding a tolerance that turns exact-flat outcomes into wins, lowering the pooled Wilson gate, replacing the winning candidate after reference outcomes are known, or changing character clauses. Any new character hypothesis requires a new scientific identity.