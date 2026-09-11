# ETH E13C — E12 Native-Hold One-Position Sequential Audit — Preregistration

## Purpose
Audit what the completed E12 24-hour ETH LONG character map actually becomes under the intended live constraint: **only one position may be active at a time**.

This experiment does **not** discover a new TP, SL, profit floor, entry rule, lookback, hour, or hold. It preserves the E12 representative rule, lookback, and fixed hold for each hour exactly as already observed in Development and only changes the execution accounting from independent/overlapping opportunities to chronological one-position execution.

## Critical correction versus E13A/E13B
E12 never used a TP. E12 winners/near-misses used fixed holding horizons (60/120/240/360/720/960 minutes). Therefore E13C must preserve those native E12 holds. E13A/E13B are separate diagnostics and are not the continuation of this lineage.

## Data / partition
- ETHUSDT 5m source identical to E12.
- Development only.
- OOS/holdouts remain closed.
- LONG only.
- Same $500 notional and $0.75 round-trip fee used by E12.
- Entries and exits use the exact E12 causal timestamps and fixed-hold semantics.

## Frozen 24-hour representative map
For PASS hours use the formal E12 winner. For FAIL hours use the already-persisted strongest representative clue used in the completed 24-hour map. No coordinate may be changed after this preregistration.

| WIB hour | E12 | Formal | Rule | LB | Hold |
|---:|---|---|---|---:|---:|
| 00 | E12L | PASS | EFF_LOW__RANGE_HIGH | 30 | 720 |
| 01 | E12M | PASS | EFF_HIGH__RV_LOW | 240 | 960 |
| 02 | E12N | FAIL | EFF_HIGH__RV_HIGH | 360 | 720 |
| 03 | E12O | PASS | RV_HIGH__RANGE_MID | 360 | 240 |
| 04 | E12P | FAIL | EFF_HIGH__RV_HIGH | 120 | 960 |
| 05 | E12Q | FAIL | RV_HIGH__RANGE_MID | 360 | 960 |
| 06 | E12R | FAIL | EFF_LOW__RANGE_MID | 60 | 720 |
| 07 | E12S | FAIL | EFF_MID__RANGE_LOW | 240 | 720 |
| 08 | E12T | FAIL | EFF_LOW__RANGE_MID | 360 | 720 |
| 09 | E12U | FAIL | EFF_LOW__RANGE_HIGH | 15 | 720 |
| 10 | E12V | FAIL | DRIVE_UP__STR_B80_100 | 120 | 960 |
| 11 | E12W | FAIL | EFF_MID__RANGE_HIGH | 360 | 720 |
| 12 | E12X | FAIL | DRIVE_UP__STR_B80_100 | 240 | 360 |
| 13 | E12A | FAIL | DRIVE_DOWN__RV_HIGH | 60 | 360 |
| 14 | E12B | FAIL | DRIVE_UP__STR_B80_100 | 360 | 360 |
| 15 | E12C | FAIL | DRIVE_UP__EFF_HIGH | 360 | 960 |
| 16 | E12D | FAIL | DRIVE_UP__STR_B20_40 | 240 | 960 |
| 17 | E12E | FAIL | EFF_HIGH__EXT_LOW | 30 | 960 |
| 18 | E12F | FAIL | DRIVE_DOWN__RANGE_MID | 60 | 720 |
| 19 | E12G | FAIL | DRIVE_UP__RV_HIGH | 240 | 960 |
| 20 | E12H | FAIL | RV_LOW__RANGE_HIGH | 15 | 960 |
| 21 | E12I | FAIL | RV_HIGH__RANGE_MID | 240 | 960 |
| 22 | E12J | FAIL | RV_MID__RANGE_HIGH | 120 | 960 |
| 23 | E12K | PASS | DRIVE_UP__STR_B60_80 | 60 | 720 |

Every hour uses its four quarter-hour anchors (:00/:15/:30/:45) exactly as E12.

## Two frozen execution policies
### P1 — FORMAL_PASS_ONLY
Only the four formal PASS hours are eligible: 23, 00, 01, 03 WIB. Their exact rules/LB/holds above are preserved.

### P2 — ALL_HOURLY_REPRESENTATIVES
All 24 frozen hourly representatives above are eligible. This is diagnostic: FAIL-hour representatives are not promoted merely because sequentialization may improve their aggregate path.

## One-position chronological rule
For each policy independently:
1. Build all causal eligible opportunities in Development using the frozen E12 coordinate for that hour.
2. Sort opportunities by entry timestamp.
3. If no position is active, take the opportunity.
4. Exit exactly at `entry_ts + native_hold` using the same E12 fixed-hold price semantics.
5. While the position is active, skip every later opportunity regardless of hour/rule quality.
6. At the exact exit timestamp the engine is re-armed; an opportunity timestamped at that same time may be taken after the prior position closes.
7. No pyramiding, no concurrent positions, no TP, no SL, no first-positive-close exit, no profit floor.

## Frozen outputs
For each policy report:
- raw eligible opportunities before sequential locking;
- executed trades;
- skipped/busy opportunities and skip rate;
- WR, net PnL, expectancy, PF, max DD, max win/loss streak;
- 2022/2023/2024 executed metrics;
- trade-duration distribution from the native holds;
- executed-trade count by source WIB hour;
- executed vs skipped opportunities by source hour;
- full chronological executed-trade ledger.

## Interpretation rules
- This is an **execution accounting audit**, not a new character search.
- A FAIL-hour E12 clue cannot become a formal character merely because P2 aggregate metrics improve.
- A PASS-hour E12 character remains Development-only.
- Do not tune coordinates, drop losing trades, change hour priority, or change holds after seeing E13C.
- Do not expose OOS.
- Any later TP/exit discovery must be a separately preregistered experiment after this audit.

## Scientific question
Does enforcing the actual live constraint of one active position materially change the realized trade set and risk/economic profile of the E12 temporal map when the **original E12 fixed holds are preserved exactly**?
