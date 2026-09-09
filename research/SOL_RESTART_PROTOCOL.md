# SOL Restart Protocol

> Restart-safe operating procedure for continuing the SOL pair-native discovery lineage without carrying the full chat or experiment history into working context.

## Purpose

GitHub is the permanent research memory. ChatGPT or any other research worker is disposable execution context.

A fresh research session must be able to continue SOL from the current checkpoint by reading a small canonical state, not by replaying A1 through the latest experiment.

## Canonical authority order

Read in this order:

1. `research/SOL_DISCOVERY_STATE.md` — **authoritative active scientific checkpoint**.
2. `research/SOL_L0_L5_CONTRACT.md` — frozen SOL loss-taxonomy semantics and namespace rules.
3. `research/SOL_DECISION_LOG.md` — what is accepted, rejected, constrained, or still open.
4. `research/SOL_NEGATIVE_RESULTS.md` — routes that must not be casually retested.
5. `research/SOL_EVIDENCE_LOG.md` — compact audit trail for result/verdict evidence.
6. `PAIR_NATIVE_DISCOVERY_PROTOCOL.md` — reusable discovery grammar when a genuinely new hypothesis is being designed.

If documents appear to conflict, `SOL_DISCOVERY_STATE.md` controls the current frontier, while the original preregistration, deterministic result artifact, and scientific verdict remain authoritative for the exact experiment.

## Minimal fresh-session bootstrap

Use this instruction in a new research session:

> Continue SOL discovery on branch `research/sol-long-structure-a1-run`. Read `research/SOL_DISCOVERY_STATE.md`, then the SOL restart/taxonomy/decision/negative-result documents. Continue exactly from the latest scientific checkpoint. Do not reopen a locked or closed route unless its documented reopen condition is met. Do not copy BTC or another pair's coordinates. Do not assign a hypothesis to the next experiment ID until it is separately preregistered.

## Context-budget rule

Default working context should contain only:

- locked/current knowledge relevant to the current question;
- the current scientific frontier;
- one proposed next experiment and its preregistration;
- the minimum evidence needed to falsify or support that experiment.

Do **not** preload full raw output, old chat transcripts, or all historical experiments.

Retrieve older artifacts only when one of these conditions is true:

- an audit requires exact numbers;
- a claimed prior decision cannot be resolved from the state/logs;
- a proposed hypothesis may duplicate a previously rejected route;
- an implementation invariant must be checked against an earlier experiment.

## Experiment lifecycle

Every result-bearing experiment must follow the repository scientific protocol:

1. define one falsifiable question;
2. freeze data/cohort, causal semantics, finite search family, metrics, support rules, and gates;
3. commit preregistration **before** result inspection;
4. implement and run deterministically;
5. persist result artifacts;
6. write a separate scientific verdict;
7. update `SOL_EVIDENCE_LOG.md`;
8. update `SOL_DECISION_LOG.md` and, when applicable, `SOL_NEGATIVE_RESULTS.md`;
9. only then advance `SOL_DISCOVERY_STATE.md`.

A CI pass is not a scientific result. A result artifact without a separate verdict does not advance state.

## Status lifecycle

Use exactly these research-decision states:

- `OPEN` — question has not been resolved.
- `PROVISIONAL` — evidence is promising but not sufficient to lock.
- `LOCKED` — conclusion is accepted for this lineage under its frozen scope.
- `REJECTED` — preregistered candidate/family failed its gate; no post-hoc rescue.
- `INCONCLUSIVE` — evidence did not establish the claim; the exact tested family is closed unless a reopen condition is met.

`LOCKED` never means production-ready unless the production/deployment stage is explicitly completed.

## Reopen discipline

A closed route can be reopened only when the log states a concrete reason such as:

- materially new independent data;
- a discovered implementation/data-integrity defect that invalidates the old result;
- a genuinely different causal mechanism, not a neighboring threshold or feature rename;
- an explicitly preregistered parent recalibration lineage.

Not valid reopen reasons:

- a nicer-looking OOS slice;
- moving a threshold after seeing validation;
- changing a horizon to rescue a failed premise;
- adding leverage, TP/SL, or sizing before directional/mechanism support exists;
- importing a coordinate because it worked on BTC/ETH/BNB.

## Current restart checkpoint

At the time this protocol was introduced:

- latest completed SOL experiment: `A68`;
- next available identifier: `A69`;
- `A69` has **no pre-approved hypothesis**;
- frozen long parent remains `R360 / 15UTC / E0_RESTING_H -> E40`;
- live intervention remains prohibited;
- current frontier is the manual post-A68 directional reset defined in `SOL_DISCOVERY_STATE.md`.

This section is descriptive. The active state file must always be checked for a newer checkpoint before work begins.
