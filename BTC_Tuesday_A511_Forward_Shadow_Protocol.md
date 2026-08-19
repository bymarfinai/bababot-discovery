# BTC Tuesday A5.11 — True Forward Shadow Protocol

**Status: FROZEN FOR FORWARD OBSERVATION — research/shadow only.**

**Live BBC must remain untouched. No exchange order is created by this system.**

## Purpose
Accumulate pristine forward Tuesday observations after the G0–G7 research family was closed for same-sample Tuesday modification.

The shadow system records telemetry before the Tuesday outcome is known, then settles the frozen A5.11 paper path after the 6-hour horizon. It is an evidence-collection system, not a new optimizer.

## Frozen Tuesday opportunity
- Symbol: BTCUSDT perpetual.
- Opportunity: every Tuesday exactly 06:00 WIB = Monday 23:00 UTC.
- Direction: SELL.
- Paper entry anchor: BTCUSDT 5m candle open at the opportunity timestamp.
- Reference notional: $500 ($10 margin x 50 leverage reference only).
- Round-trip fee assumption: 0.15% of notional.

## Frozen A5.11 execution/management
Unchanged canonical rules:
- TP 1.35%.
- SL 0.80%.
- Max hold 6h.
- A5.2 selective +0.20% protection after first +0.50% MFE only under the frozen weak-close/cum-MAE condition.
- A5.9 FastMR +0.20% lock under the frozen EMA20/giveback condition.
- A5.11 EMA7 bearish-rejection runner recovery can cancel the FastMR lock only before lock touch and with frozen progress requirement.
- Completed 5m bars only for management decisions.
- Existing canonical same-bar TP/SL ordering and fee treatment remain unchanged.

Historical parity anchor remains:
- 139 trades.
- 89 wins.
- PnL +$130.328521 approximately.
- A5.2 actions 7.
- FastMR actions 12.
- A5.11 recoveries 4.

## Frozen G1 telemetry model
The forward shadow model is the final G1 multinomial logistic model trained once on the frozen G0 pooled dataset ending **2026-07-30 UTC cutoff**.

Training universe:
- 23,304 hourly BTC market states.
- Same 17 G0 causal pre-entry features.
- Median imputation.
- StandardScaler.
- L2 logistic regression, C=1, lbfgs, random_state=7.
- Classes: BUY_COMPATIBLE / NEUTRAL / SELL_COMPATIBLE.

After its model-state artifact is frozen, the forward runner must perform inference from that immutable state. It must not refit from future data.

## Frozen G6 slow telemetry
For each Tuesday opportunity T:
- Score exactly the 168 completed hourly states T-168h through T-1h using the same frozen G1 model.
- `weekly_sell_health = mean(pSELL - frozen historical SELL prior)`.
- Also record `mean_pSELL_168h`.

No alternative lookback is allowed inside this forward protocol.

## G7 diagnostic only
Record:
`diagnostic_weight = min(1.0, mean_pSELL_168h / frozen historical SELL prior)`.

This number is telemetry only. G7 failed promotion and may not change paper or live exposure.

## Two-phase evidence lock
### Phase A — SNAPSHOT
Scheduled for Tuesday 06:00 WIB.

The runner must:
1. use only completed 5m bars strictly before T for all model features;
2. record G1 pBUY/pNEUTRAL/pSELL and argmax class;
3. record 168h weekly health and G7 diagnostic weight;
4. record the frozen model fingerprint;
5. append one immutable PENDING_SETTLEMENT row to the forward ledger;
6. never inspect the subsequent six-hour outcome before writing the snapshot.

A workflow delay after 06:00 does not permit post-entry bars to enter features; data use is explicitly capped at T-5m.

### Phase B — SETTLEMENT
Run only after T+6h has completed.

The runner may then:
1. replay the frozen A5.11 paper path from the actual T open;
2. record parent and A5.11 outcome, MFE/MAE and which frozen layer acted;
3. record the G0 50bp/6h oracle label for diagnosis only;
4. mark the row SETTLED.

Settlement must never rewrite the snapshot probabilities, weekly-health values, model fingerprint, or snapshot timestamp.

## Forward ledger integrity
Canonical ledger:
`BTC_Tuesday_A511_Forward_Shadow_Ledger.csv`

One row per Tuesday. Snapshot fields are write-once. Settlement fields are write-once after the horizon. Re-running a job must be idempotent.

The first truly new forward opportunity after this protocol is Tuesday **2026-08-25 06:00 WIB**.

August 4/11/18 may be used only as implementation parity fixtures; they are not new forward evidence.

## Explicit prohibitions
During this forward phase do not:
- retrain G1 using new Tuesday outcomes;
- retrain G1 using new hourly outcomes;
- change feature definitions;
- change 168h lookback;
- tune pSELL thresholds;
- tune risk weights;
- alter A5.11 TP/SL/hold/management;
- promote G1/G6/G7 into production decisions;
- call Binance order endpoints;
- modify `bbc_live.py`, `bbc_live_endpoint.py`, or active BBC configs from this workflow.

Any later research change requires a new named protocol/version and must not rewrite prior forward ledger rows.

## Promotion philosophy
The purpose is to observe, not to force a pass. Future production decisions must be made from accumulated pristine forward evidence plus live-parity engineering evidence, not from another same-sample optimization cycle.
