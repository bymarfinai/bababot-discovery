# BNB B29-B1 — Event-Conditioned Structural Transition — Frozen Stop Verdict

**Final status: `BNB_B29_B1_EVENT_TRANSITION_REJECT`**

This verdict freezes B29-B1-v1 after a valid run against the immutable accepted B29-A1 fingerprint artifact.

## Reproducibility identity
- Branch: `bnb-b29-walkforward-reset`
- Valid dedicated run: `34924493721`
- Reproducibility artifact: `10378979892`
- Accepted A1 source artifact: `10336102957`
- Accepted A1 fingerprint SHA256: `eae8f278d45e7c3035b03900b30e315b16a241c1fbc5fda39231681390c25cfa`
- A1 fingerprint rows: 229,267
- Forward outcomes were reconstructed only from the immutable A1 `ret_15` sequence on exact 15-minute clock paths; horizons crossing the 13 known A1 history gaps were not evaluated.
- B1 event clauses, directions, 60-minute same-family cooldown, primary +60m horizon, auxiliary horizons, and promotion gates were unchanged from preregistration.

## Valid scientific result
No preregistered event family met every frozen promotion gate; therefore **no family is promoted to B2 execution discovery from B1-v1**.

The strongest family was `SWEEP_LOW_RECLAIM -> LONG`:
- N = 8,084
- pooled +60m directional hit = 54.13%
- Wilson 95% lower bound = 53.04%
- median signed +60m return = +0.03%
- positive +60m fold count = 5/5
- worst fold = 52.66%
- 2025 = 52.66%
- 2026 = 53.00%
- auxiliary horizons >=52% = 4/4
- max era share = 22.22%

It remains **REJECT** because the preregistered primary +60m hit gate was >=55.0%. The gate must not be relaxed after observing 54.13%.

Other families also remain rejected. In particular, `COMPRESSION_EXPAND_UP -> LONG` had a high pooled hit but only N=37 and weak 2026 behaviour, so it does not satisfy evidence-size or recent-robustness requirements.

## Stop rule
Do not rescue B1-v1 by:
- lowering the 55% primary hit gate;
- switching the primary horizon after seeing auxiliary results;
- reducing the 60-minute cooldown;
- narrowing a failed family by hour, regime, state, or outcome-derived subset on these same results;
- adding/removing event clauses and retaining the B1-v1 identity;
- proceeding to entry, TP, or SL discovery for any B1-v1 rejected family.

Any later investigation inspired by B1 must be declared a **new scientific identity** and treated as development, not as validation of B1-v1.

## Data policy for subsequent B29 work
Do not rebuild accepted A1 history from a fresh Binance Vision download when a frozen A1-derived experiment can operate from artifact `10336102957`. Fresh historical downloads were observed to reproduce the same row count/timestamps while producing a different A1 fingerprint hash. Subsequent frozen B29 experiments should consume the immutable A1 artifact directly wherever possible, and must explicitly prevent event/outcome calculations from crossing its known timestamp gaps.

No live orders were placed.
