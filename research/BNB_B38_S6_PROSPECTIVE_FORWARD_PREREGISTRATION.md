# BNB B38-S6 — Prospective Forward Shadow Preregistration

**Scientific identity:** `BNB_B38_S6_PROSPECTIVE_FORWARD_V1`

## Frozen parent policy

Exact policy: `BNB_B38_S5_ADAPTIVE_POLICY_V1`.

Freeze timestamp recorded by S5:
`2026-09-20T06:30:00Z`.

To avoid any boundary ambiguity, S6 accepts only parent demand-interaction events whose **first completed 15m retest close is strictly after the freeze timestamp**.

No historical 2025-2026 result is counted as S6 prospective evidence.

## Data

- Symbol: BNBUSDT USD-M futures.
- Canonical input: exact 5m Binance futures klines.
- Historical seed uses the same normalized B31 5m source and close-timestamp convention.
- New bars are fetched from Binance Futures REST and converted from open timestamps to the same close-timestamp convention (+5 minutes).
- Only completed 5m bars are admitted.

The historical seed is immutable after creation. A smaller bridge/forward 5m tail is appended on subsequent runs.

## Frozen structure and execution

Structure, entry, SL and target assignment are exactly B38-S5:

- IMMEDIATE_CLEAN_RECLAIM -> TP1
- IMMEDIATE_SWEEP_RECLAIM -> TP1
- DELAYED_CLEAN_RECLAIM -> TP1
- DELAYED_SWEEP_RECLAIM -> TP2

Missing required objective -> NO_POLICY_TARGET.

No substitution.

## Forward event lifecycle

Every post-freeze parent event is assigned a stable key:
`zone_id + first_touch_ts`.

Possible execution states:
- PENDING_RECLAIM
- CANCELLED_DEMAND_ACCEPTANCE
- NO_POLICY_TARGET
- PAPER_ENTRY_OPEN
- PAPER_WIN
- PAPER_LOSS
- PAPER_AMBIGUOUS_SAME_5M

For a paper entry:
- entry, SL, target and target-R are immutable after first detection;
- subsequent runs may only advance OPEN to a terminal outcome.

Target/SL ordering is resolved using completed 5m bars strictly after entry close:
- target first -> WIN
- SL first -> LOSS
- both first touched in same 5m bar -> AMBIGUOUS
- neither -> OPEN

## Forward evidence gate

The gate is frozen before observing S6 outcomes.

Support gate:
- at least **28 elapsed calendar days** from freeze; and
- at least **30 resolved WIN+LOSS paper entries**.

Before support gate: `COLLECTING_FORWARD_EVIDENCE`.

After support gate:
- expectancy R > 0;
- profit factor > 1.0;
- total realized R > 0.

All three pass:
`FORWARD_EDGE_GATE_PASS_PAPER_REVIEW`.

Otherwise:
`FORWARD_EDGE_GATE_FAIL`.

Passing this gate does not authorize live-money deployment. Fees/slippage, concurrent-position exposure, sizing, and execution plumbing remain separate.

## Persistence / immutability

Persist:
- immutable historical seed;
- bridge/forward 5m tail;
- prospective event ledger;
- latest status report;
- by-mode summary;
- run audit.

Existing terminal signal geometry may not change. Any detected mutation aborts the run.

## Schedule

Target cadence: hourly shadow refresh.

No orders are sent to Binance. Public market-data endpoints only.

## Stop rule

Do not:
- change S5 policy during S6;
- backfill pre-freeze events as forward evidence;
- optimize by mode;
- alter target assignment;
- add RR gates;
- add indicators, sessions, derivatives, funding, OI, ATR, volume or discretionary filters.
