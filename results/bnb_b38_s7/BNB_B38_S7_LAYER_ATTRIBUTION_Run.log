# BNB B38-S7 — Detector → Zone → Entry → SL → TP Attribution Audit

**NO SUB-FILTER. NO TRADE REMOVAL. FROZEN B38-S5 EXECUTION.**

Data through **2026-08-27 00:00:00+00:00**.

## 1. Is the demand zone itself producing a meaningful rebound?

| Period | Parent N | +1ZW before demand acceptance failure | +2ZW |
|---|---:|---:|---:|
| DEV | 788 | 494 / 62.7% | 386 / 49.0% |
| REF | 463 | 284 / 61.3% | 227 / 49.0% |

## 2–4. Frozen entry population and loss attribution

| Period | Entries | Resolved | W-L | WR | Entry-pop zone +1ZW valid | Need loss→win for 70% | Current losses on valid zones | Zone fail | Entry late | False SL | TP/path |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | 690 | 677 | 353-324 | 52.1% | 71.6% | 121 | 148 | 176 | 39 | 42 | 67 |
| REF | 402 | 399 | 212-187 | 53.1% | 70.6% | 68 | 80 | 107 | 20 | 20 | 40 |

## Loss attribution meaning
- **Zone fail:** underlying demand never produced +1ZW before 15m close acceptance below demand_low.
- **Entry late:** +1ZW rebound was already achieved before the frozen entry.
- **False SL:** entry was timely and the zone later reached +1ZW, but frozen SL was touched first.
- **TP/path:** entry was timely, SL survived until +1ZW, but the frozen selected structural TP still eventually lost.

## By execution mode

| Period | Mode | N | WR | Zone +1ZW valid | Need for 70 | Valid-zone losses | Zone fail | Late | False SL | TP/path |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | DELAYED_CLEAN_RECLAIM | 137 | 59.1% | 67.9% | 15 | 16 | 40 | 1 | 9 | 6 |
| DEV | DELAYED_SWEEP_RECLAIM | 64 | 51.6% | 75.3% | 12 | 17 | 14 | 5 | 3 | 9 |
| DEV | IMMEDIATE_CLEAN_RECLAIM | 411 | 49.9% | 72.3% | 83 | 100 | 106 | 24 | 29 | 47 |
| DEV | IMMEDIATE_SWEEP_RECLAIM | 65 | 52.3% | 70.8% | 12 | 15 | 16 | 9 | 1 | 5 |
| REF | DELAYED_CLEAN_RECLAIM | 91 | 59.3% | 70.3% | 10 | 15 | 22 | 2 | 4 | 9 |
| REF | DELAYED_SWEEP_RECLAIM | 35 | 54.3% | 78.9% | 6 | 9 | 7 | 4 | 0 | 5 |
| REF | IMMEDIATE_CLEAN_RECLAIM | 235 | 48.1% | 66.0% | 52 | 47 | 75 | 11 | 15 | 21 |
| REF | IMMEDIATE_SWEEP_RECLAIM | 38 | 68.4% | 92.1% | 1 | 9 | 3 | 3 | 1 | 5 |

## 70% fixed-N diagnostic
The audit does not convert any historical loss into a win. It only checks whether enough current losses occurred on objectively rebounding (+1ZW-valid) demand events to make a fixed-trade-count 70% WR mechanically conceivable through execution improvement.
If the valid-zone-loss count is smaller than the required conversions, the detector/zone layer itself is the hard ceiling under this +1ZW diagnostic.
