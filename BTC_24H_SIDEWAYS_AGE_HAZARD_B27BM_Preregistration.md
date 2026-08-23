# B27BM — BTC 24H SIDEWAYS Age-Hazard Audit — Preregistration

## Purpose

Audit the existing causal 4H regime detector only. The question is whether a SIDEWAYS episode has a reproducible **age-dependent exit hazard**: conditional on the episode still being SIDEWAYS at age `k`, what is the probability that the next completed 4H state resolves back to the origin directional regime, resolves to the opposite directional regime, or remains SIDEWAYS?

This is regime-state anatomy only. It does **not** define trading direction, entry, stop, target, fee, WR, PF, PnL, session preference, or live behavior.

## Frozen parent lineage

Use the exact B27BH directionally bracketed SIDEWAYS episodes from `BTC_24H_SIDEWAYS_TRANSITION_ANATOMY_B27BH_SidewaysEpisodes.csv`.

Mandatory identity before any result is accepted:

- major-partition bracketed episodes = **1,023**;
- same-direction RESUME = **527**;
- opposite-direction TRANSITION = **496**;
- BULL-origin = **532**;
- BEAR-origin = **491**.

Partitions remain exactly inherited from B27BH/B27BG. Partition boundaries are reporting boundaries only and do not redefine episode state.

## Causal age / risk-set semantics

A SIDEWAYS episode with `n_intervals = d` contains completed SIDEWAYS 4H bars numbered `1..d`.

For each age `k`:

- **risk set** = episodes with `d >= k`; these are known to have survived as SIDEWAYS through completed SIDEWAYS bar `k`;
- **RESUME exit at age k** = `d == k` and the next completed directional state equals the episode origin state;
- **TRANSITION exit at age k** = `d == k` and the next completed directional state is the opposite directional state;
- **SURVIVE after age k** = `d > k`.

Therefore, conditional next-state hazards at age `k` are:

- `h_resume(k) = resume_exit_at_k / risk_set_k`;
- `h_transition(k) = transition_exit_at_k / risk_set_k`;
- `h_survive(k) = survive_after_k / risk_set_k`.

They must sum to 1 (within floating-point tolerance).

No future price data are used to decide membership of a risk set. Final episode outcome is used only as the historical label required to estimate cause-specific exit hazards.

## Frozen ages

Primary ages are fixed before result inspection:

- age 1 = first SIDEWAYS bar / 4h;
- age 2 = second SIDEWAYS bar / 8h;
- age 3 = third SIDEWAYS bar / 12h.

Ages 4–6 (16h–24h) are secondary descriptive diagnostics only and may not rescue a failed primary gate.

## Reporting cohorts

Report hazards for:

- `external`;
- `development` (diagnostic, not required for OOS support);
- `reference_validation`;
- `POOLED_OOS = external + reference_validation`;
- `POOLED_MAJOR = external + development + reference_validation`;

separately for BULL-origin and BEAR-origin, plus combined-origin totals as descriptive context.

## Frozen primary hypothesis

The hypothesis is a **phased hazard shape**, not monotonic “older SIDEWAYS = more reversal”:

1. At age 1, quick exits should be more continuation-like than reversal-like: `h_resume(1) > h_transition(1)`.
2. By age 2 or age 3, the balance should become more transition-heavy: at least one of ages 2 or 3 has `h_transition(k) > h_resume(k)`.
3. The transition-minus-resume hazard margin must move upward from age 1 to age 2: `[h_transition(2)-h_resume(2)] > [h_transition(1)-h_resume(1)]`.

These are evaluated by origin because BULL-origin and BEAR-origin may have different levels even if the temporal shape is shared.

## Frozen support gate

Verdict `B27BM_PHASED_SIDEWAYS_HAZARD_SUPPORTED` only if **all** conditions hold:

1. Parent identity and hazard accounting assertions pass exactly.
2. For **both origins in POOLED_OOS**, age-1 `h_resume > h_transition`.
3. For **both origins in POOLED_OOS**, at least one of age 2 or age 3 has `h_transition > h_resume`.
4. For **both origins**, the transition-minus-resume hazard margin increases from age 1 to age 2 in **external and reference_validation separately**.
5. For each origin, OOS risk-set size is at least 30 at ages 1, 2, and 3.
6. No primary conclusion is rescued using ages 4–6, development-only behavior, pooled-all behavior, a changed age bucket, or a post-hoc threshold.

Otherwise verdict is `B27BM_PHASED_SIDEWAYS_HAZARD_NOT_SUPPORTED`.

## Interpretation boundary

Even a supported result validates only that SIDEWAYS age contains a reproducible cause-specific temporal structure. It does not by itself define a production `PENDING` state, a new BULL/BEAR rule, or any trading setup. Any state-machine redesign requires a separate preregistered experiment.

Research only. Live BBC unchanged.
