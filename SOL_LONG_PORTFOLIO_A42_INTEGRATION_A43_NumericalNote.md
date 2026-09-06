# A43 Numerical Equality Note

A43's persisted audit flags `development.dd_stress_not_worse = False` because the baseline and overlay max-drawdown values differ only at floating-point machine precision:

- baseline: `201.10662274226883`
- overlay: `201.10662274226917`
- absolute difference: approximately `3.4e-13`

At the precision of the underlying PnL ledger, these values are economically and mathematically equivalent for the intended strict no-degradation rule. This is a floating-point comparison artifact, not a substantive drawdown increase.

This note does **not** change the A43 preregistered gate, any trading parameter, or the final A43 verdict. A43 remains `SOL_LONG_PORTFOLIO_A42_INTEGRATION_A43_NOT_SUPPORTED` because genuine weekly-hit-rate degradations remain:

- external raw positive-week rate decreases;
- external 5bps positive-week rate decreases;
- reference-validation raw positive-week rate decreases;
- pooled raw positive-week rate decreases.

Research only. Live Baba Bot remains unchanged.
