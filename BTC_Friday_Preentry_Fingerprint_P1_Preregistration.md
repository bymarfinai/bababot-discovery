# BTC Friday Pre-entry Fingerprint P1 — Frozen Fallback Discovery Protocol

**FROZEN BEFORE P0 RESULT. Run only if P0 fails the 80% candidate gate. Research-only; live BBC untouched.**

## Objective
Find one interpretable, strictly pre-entry BTC Friday candle fingerprint with observed WR >=80% that survives chronological validation, before any cross-pair transfer is attempted.

## Canonical outcome
Same canonical Friday parent as P0 / F5.17:
- BTCUSDT Friday 08:00 UTC LONG
- entry at 08:00 5m open
- TP +2.00%, SL -0.70%, max hold 360m
- $500 notional; 0.15% round-trip fee
- adverse-first same-bar ambiguity

## Information set
Only four completed 5m candles `[T-20m,T)` at entry T. Use exactly the pre-existing F6.37 geometry definitions plus the exact F6.38 balance boolean. No new numeric thresholds.

Frozen Boolean atoms:
1. `last_red`
2. `last_upper_gt_lower`
3. `upper_gt_prev1`
4. `upper_gt_prev2max`
5. `upper_localmax4`
6. `body_lt_prev1`
7. `body_contract3median`
8. `upper_share_gt_prev3median`
9. `rejection_expansion_composite`
10. `wick_dominant`
11. `f636_morphology`
12. `balance_gate` (exact F6.38 inequality)

Candidate grammar is frozen to:
- every single literal `atom=True` or `atom=False`;
- every two-literal AND involving two different atoms, each literal independently True/False.
No three-way rules, no continuous cutoffs, no OR rules, no time shifts.

## Selection / validation
Canonical chronology remains first 82 Fridays discovery, remaining 56 validation.

Discovery eligibility:
- candidate N >= 12;
- observed WR >= 80%;
- positive PnL and PF > 1.

If multiple candidates qualify, choose exactly ONE by this frozen ordering:
1. highest discovery WR;
2. then largest discovery N;
3. then highest discovery PF;
4. then lexical rule string.

Validation is performed only on that one selected rule.

## Promotion gate
`BTC_FRIDAY_80_CANDIDATE` only if:
- discovery N >=12 and WR >=80%;
- validation N >=8 and WR >=80%;
- validation expectancy >0 and PF >1;
- combined N >=20 and WR >=80%;
- at least 3/4 chronological full-history blocks containing qualifying trades have positive PnL;
- validation WR exceeds the unconditional validation baseline.

Otherwise `REJECT_P1_80_CANDLE_IDENTIFIER`.

## Multiple-testing disclosure
P1 is a discovery exercise over a fixed grammar, not pristine proof. The exact number of candidate rules evaluated must be reported. Cross-pair transfer, if P1 passes, is the next external validation and must use the fingerprint unchanged.

## Anti-overfit guardrail
After P1 output, do not try the second-best candidate, alter atom definitions, add a third condition, invert a condition, change entry time, or tune TP/SL on the same BTC history. A failed P1 closes this morphology grammar.