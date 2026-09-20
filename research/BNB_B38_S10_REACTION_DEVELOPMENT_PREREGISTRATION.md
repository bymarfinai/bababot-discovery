# BNB B38-S10 — Reaction Development Entry State Machine

**Scientific identity:** `BNB_B38_S10_REACTION_DEVELOPMENT_V1`

## Purpose

Replace "reclaim = immediate entry" with a causal reaction-development state machine:

`DEMAND TOUCH -> RECLAIM -> REACTION DEVELOPMENT -> LOCAL EXPANSION -> ENTRY`

Every parent event is followed until either:
- its required state develops and an entry is emitted; or
- a completed 15m close below demand_low invalidates the event before entry.

This is not a session/indicator filter.

## Parent

Exact B38 H1-demand / 15m visual family:
- DEV 2022-2024 = 788 events
- REF 2025-2026* = 463 events

## Reclaim state

Reclaim is the first completed 15m close > demand_high at or after first touch, before any completed 15m close < demand_low.

The first-touch bar itself can establish reclaim.

## Frozen state-machine candidates

### E1 RECLAIM_HIGH_BREAK
After reclaim:
- track lowest low from first touch through entry;
- entry = first later completed 15m close > reclaim candle high;
- if a completed 15m close < demand_low occurs first: NO_ENTRY_INVALIDATED.

Meaning: reclaim must generate a new local expansion beyond its own interaction candle.

### E2 RECLAIM_HOLD_THEN_BREAK
After reclaim:
- require one separate later completed 15m bar that closes >= demand_high without invalidation;
- call that the HOLD bar;
- entry = first later completed 15m close > max(reclaim_high, hold_high);
- demand close invalidation before entry cancels.

Meaning: proximal reclaim must first survive one completed bar, then expand.

### E3 PROTECTED_LOW_THEN_BREAK
After reclaim:
- require a strict 2-left/2-right 15m pivot low whose pivot_ts > reclaim_ts and confirm_ts is known causally;
- no completed 15m close below demand_low before confirmation;
- entry = first completed 15m close after pivot confirmation > reclaim_high;
- demand close invalidation before entry cancels.

Meaning: a post-reclaim protected low must form and then price must expand beyond the reclaim candle.

## Candidate execution geometry

At candidate entry:
- entry reference = candidate 15m close;
- structural SL reference = lowest observed 15m low from first touch through candidate entry;
- target = nearest already-known structural overhead objective (TP1) from the exact B38-S3 causal objective ladder, rebuilt at candidate entry;
- if no objective exists above entry: NO_TARGET.

Outcome ordering:
- exact 5m bars strictly after entry;
- target touch before SL touch = WIN;
- SL before target = LOSS;
- same 5m = AMBIGUOUS.

No close-based SL is used in S10; this isolates the state-machine effect from S8 close-invalidation.

## Baseline preservation

Baseline reference = exact resolved B38-S5 trades.

For each candidate report:
- parent events;
- entries;
- invalidated-before-entry;
- no-state-by-end;
- no-target;
- actual W/L and WR;
- expectancy / PF;
- baseline WIN events that still receive an entry;
- baseline WIN events that remain WIN under candidate geometry;
- baseline LOSS events avoided before entry;
- genuine-zone-failure baseline losses avoided before entry.

## Stop rule

Do not:
- scan numeric thresholds;
- add session filters;
- add RR gates;
- change candidate definitions after results;
- call rejected trades converted wins;
- hide lost baseline winners.
