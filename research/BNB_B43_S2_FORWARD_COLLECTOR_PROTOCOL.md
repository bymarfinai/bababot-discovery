# BNB B43 Forward Collector Protocol

Active asset: **BNBUSDT only**.

Each run:

1. Read:
   - `research/BNB_B43_S1_OPTIONS_IV_LEVEL_MAP_SPEC.md`
   - `research/BNB_B43_S2_FORWARD_IV_HODLOD_PREREGISTRATION.md`

2. Evaluate previous promotion-eligible snapshots whose +1h / +4h / +24h horizons are now complete using BNBUSDT 5m futures candles.

3. If a canonical daily snapshot's UTC day has completed, evaluate its actual UTC-day high/low.

4. Persist evaluations without modifying frozen level prices.

5. Capture a fresh live BNB options snapshot using the connected Binance tools:
   - options exchange information;
   - BNBUSDT option mark price / Ask IV / Mark IV / Greeks;
   - BNBUSDT options index price.

6. Apply the frozen B43-S1 ATM rule and expected-move formula unchanged.

7. Persist the new snapshot under:
   `results/bnb_b43_s2/forecasts/`

8. Append/update:
   - `BNB_B43_S2_FORECAST_LEDGER.jsonl`
   - `BNB_B43_S2_EVALUATION_LEDGER.jsonl`
   - `BNB_B43_S2_DAILY_LEDGER.jsonl`
   - `BNB_B43_S2_STATUS.json`

9. Keep status `BNB_B43_S2_FORWARD_ACCUMULATING` until preregistered sample gates are reached.

## Infrastructure

- Use the Binance connector for live options data.
- Do not call Binance Options REST directly from GitHub-hosted Actions; prior direct EAPI access returned HTTP 451.
- If the all-options mark response is large, filter BNB rows inside orchestration before emitting/persisting.
- Never reuse stale IV after a failed capture.
- Do not backfill synthetic historical Ask IV.
