# ETH LONG Entry Optimization Audit E2 — Preregistration

## Purpose
Audit whether the current ETH LONG F75 entry is economically optimal/robust while preserving the already-selected structural DNA. This is an entry-only audit; no exit, clock, session, cohort, fee, sizing, or runner rescue is permitted.

## Frozen structure
- Pair: ETHUSDT, 5m.
- Cohort: LONDON_TO_NEWYORK / LONG / K1 / OPP0.
- Causal window semantics: exactly the persisted ETH B27W-Adapt windows.
- Fixed economics: E10 target and D60/F15 completed-close invalidation.
- Notional: $500 fixed.
- Round-trip fee allowance: $0.40.
- No runner.
- Partitions remain external / development / reference_validation / august.

## Entry depth grid
F65, F67.5, F70, F72.5, F75, F77.5, F80.

## Executable entry modes
1. `BLIND_LIMIT`: resting limit at the selected F-level; fill at the level on first causal touch. Same-bar TP is not credited because fill-vs-high ordering is unknown.
2. `BLIND_NEXT_OPEN`: after first causal touch, enter at the next 5m open.
3. `SAME_BAR_REJECTION_NEXT_OPEN`: first touch bar must close back above the F-level; enter next 5m open.
4. `EARLY_RECLAIM_NEXT_OPEN`: after first touch, first completed pre-terminal close above the F-level; enter next 5m open.
5. `NEXT_BAR_CONFIRM_NEXT_OPEN`: the bar immediately after the touch must complete above the F-level without a prior terminal event; enter the following 5m open.

Diagnostic only, never selectable for promotion:
- `SAME_BAR_REJECTION_CLOSE_DIAG`: assumes fill at the confirming close.
- `EARLY_RECLAIM_CLOSE_DIAG`: assumes fill at the confirming close.

All confirmation-based entries must be based only on completed information. A next-open entry at the start of the later H2/opposite-break bar is causal and allowed; an entry after the terminal bar start is not.

## Fixed exit
- Target: H + 0.10R (E10).
- Invalidation: first completed 5m close below L + 0.15R (F15/D60), executed at that completed close.
- Otherwise exit at active-session end open.
- For next-open entries, E10 may trigger intrabar from the entry bar because the position exists at bar open.
- For BLIND_LIMIT, E10 on the fill bar is not credited.

## Development-only selection
Reference-validation is not used to choose depth or mode.

A development center candidate must have:
- N >= 30,
- WR >= 70%,
- PF >= 1.20,
- expectancy > 0.

Plateau requirement within the same executable mode:
- at least one immediately adjacent depth also has N >= 30,
- WR >= 68%,
- PF >= 1.10,
- expectancy > 0.

For each eligible center, robustness score is the minimum PF of center and its qualifying adjacent depth. Rank by robustness score, then minimum expectancy, then center PF, then center expectancy. No external or validation metric participates in selection.

## One-shot validation gate
After the development winner is frozen, evaluate the selected center and qualifying development neighbor(s) on reference_validation.

Center must have:
- N >= 15,
- WR >= 70%,
- PF >= 1.20,
- expectancy > 0.

At least one selected adjacent neighbor must have:
- N >= 15,
- WR >= 65%,
- PF >= 1.00,
- expectancy > 0.

External partition is reported as corroboration only and is not used to select or rescue the winner.

## Interpretation
- If the plateau and one-shot validation gates pass, freeze that pair-specific entry surface for the next ETH LONG milestone.
- If no development plateau exists or the frozen winner fails one-shot validation, ETH LONG entry remains unresolved. Do not retune using reference-validation.

Research only. No live-trading changes.