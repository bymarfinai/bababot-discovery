# B27DB — BTC 24H Fresh-Pipeline Historical Parity Audit — Preregistration

**Purpose:** verify that the exact reconstruction path used by B27DA is not silently dropping valid historical F05 SHORT setups.

This is an implementation/error audit only. No trading rule, model, feature, threshold, clock, regime, entry, TP, SL, or live file is changed.

## Frozen parity requirements
Using the historical 698,112-row BTCUSDT 5m source and the persisted B27BE 4H block atlas:

1. Re-run the same K1 OPP0 -> direct Low break -> first retest -> `RETEST_RECLAIMED` reconstruction semantics used by B27DA via B27BZ `evaluate_one`.
2. The reclaimed eligible source cohort must exactly reproduce B27CE major counts:
   - external: 202
   - development: 333
   - reference_validation: 194
   - pooled major: 729
3. Execute exact B27CS `BASE_H` F05 fill semantics on the reconstructed source cohort.
4. Executable F05 fills must exactly reproduce B27CV counts:
   - external: 183
   - development: 297
   - reference_validation: 172
   - pooled major: 652
5. Compare event identity, not only counts, against persisted B27CE eligible sources and B27CV/B27CS executable trade identifiers using partition + observation/reclaim timestamps where available.

Any count or identity mismatch => `B27DB_PIPELINE_PARITY_FAIL`.
Exact parity => `B27DB_PIPELINE_PARITY_PASS`.

No result from B27DB changes strategy economics or authorizes live changes.

<!-- workflow trigger only; no semantic change -->
