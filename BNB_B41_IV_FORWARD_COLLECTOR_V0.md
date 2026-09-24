# BNB/SOL IV Forward Collector v0

Each scheduled run must perform exactly these steps:

1. Read `BNB_B41_IV_LEVEL_V0_FREEZE.md` and `BNB_B41_IV_HOD_LOD_FORWARD_PREREG.md`.
2. Evaluate the immediately previous stored forecast only if its full +60m 5m-bar window is complete.
3. Obtain BNBUSDT and SOLUSDT completed 5m futures bars needed for that previous window.
4. Score every frozen level strictly by the preregistered touch/reaction definitions.
5. Persist the scored previous forecast; never edit its frozen prices.
6. Retrieve a fresh live BNB/SOL options chain, all option mark IV/Greeks, underlying index, 120 daily candles, and 40 weekly candles through the Binance connector.
7. Apply the frozen `IV_LEVEL_ENGINE_V0` method. Do not change thresholds or trim rules.
8. Persist a new forecast snapshot stamped with the actual source timestamp.
9. Update append-only raw and de-duplicated summary ledgers.
10. If the sample gate is not reached, status remains `FORWARD_VALIDATION_ACCUMULATING`.
11. Do not promote, tune, or create trading rules from interim results.

Infrastructure rule:
- Binance Options REST from GitHub-hosted Actions is currently blocked by HTTP 451.
- Live data acquisition must use the available Binance connector (or a separately approved accessible collector).
- GitHub is used for append-only persistence/evaluation artifacts, not direct live Binance Options collection.


## BNB-only scope amendment

The later `BNB_B41_IV_HOD_LOD_FORWARD_BNB_ONLY_AMENDMENT.md` controls asset scope.

From that amendment onward:
- collect and score **BNBUSDT only**;
- do not create new SOLUSDT forecasts;
- do not score SOLUSDT for headline research;
- preserve existing SOL artifacts unchanged;
- apply BNB-only sample and quality gates from the amendment.
