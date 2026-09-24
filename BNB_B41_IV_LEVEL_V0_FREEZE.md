# BNB B41 — IV Level Engine v0 Freeze

Status: **METHOD_FROZEN_FOR_PROTOTYPE_REPLAY**

This is not a trading preregistration and makes no performance claim.

Frozen v0 inputs:
- current BNB/SOL option chain snapshot;
- option bidIV/askIV/markIV and Greeks;
- current underlying index;
- prior 120 daily futures candles;
- prior 40 weekly futures candles.

Frozen formulas:
- expected move = spot × askIV × sqrt(horizon_days / 365);
- paired ATM askIV = mean of call and put askIV at nearest strike having both sides;
- target expiries = closest listed expiry to 1d, 7d and 30d, with >6h remaining preferred;
- surface askIV = equal-weight mean among ±10% moneyness contracts with |delta| 0.15–0.85 and askIV 0.05–5.0;
- normal daily range = median high/open and open/low excursion over prior 60 completed days;
- normal weekly range = same over prior 26 completed weeks;
- q75 weekly levels are reported diagnostically;
- confluence = at least two projected levels within 0.75% of spot.

The v0 surface-average level is diagnostic. Outlier ask quotes are not trimmed beyond the frozen bounds above; later robustness changes require a new version.

No entry, direction, SL, TP, WR, PF, PnL, or HOD/LOD capture claim.
