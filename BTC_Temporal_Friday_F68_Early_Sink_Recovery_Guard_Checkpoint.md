# BTC Temporal Friday F6.8 — +10m Early-Sink Recovery Guard

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — NO ROBUST ACTION RULE YET; STRONG FEATURE LEADS FOUND  
**Research only:** live BBC untouched

## Frozen +10m base state

From F6.7:

`first 5m red + still alive + second completed 5m has not traded back to entry`

- N **29**
- strict hindsight sinks **9**
- eventual parent winners **8**

## Stable causal feature separation toward strict sink

The strongest D/V-consistent continuous feature was the morphology of the second completed 5m candle:

- `bar2_upper_wick`: AUC full / Discovery / Validation = **0.767 / 0.857 / 0.812**

Other D/V-consistent clues:
- `low_sofar`: **0.344 / 0.357 / 0.396**
- `bar2_body`: **0.261 / 0.429 / 0.104** (smaller body is more sink-like)
- `high2_gap`: **0.239 / 0.286 / 0.104** (farther below entry is more sink-like)
- `progress10`: **0.222 / 0.071 / 0.208** (deeper negative progress is more sink-like)

## Predeclared natural mechanism tests

None of the five predeclared sign/structure conjunctions passed both chronology halves.

- H1 continuation: delta **-$25.174**
- H2 seller pressure: **-$5.239**; Discovery -$18.668 / Validation +$13.429
- H3 structure pressure: **-$16.499**
- H4 failed bounce: **-$8.187**; Discovery -$22.388 / Validation +$14.201
- H5 full pressure: **-$5.239**

Thus simple directional pressure rules still clip recoverers, especially in Discovery.

## Important research lead

The feature atlas shows that **weak/indecisive candle structure below entry** is more promising than simple continuous selling. This motivated a post-F6.8 exploratory search for a recovery guard combining:

- no entry reclaim by +10m;
- short-term EMA acceptance failure;
- weak candle body.

Any candidate emerging from that exploration must be labeled post-hoc same-sample and independently frozen before future OOS.

## Execution

- Workflow run: **32041251779** — success
- Artifact: `f68-output`, ID **9291994191**
- Script: `research/f68_friday_early_sink_recovery_guard.py`
- Workflow commit: `39a2c2918698106a0b1a7cc35ca9152e7bce6b27`
- Live BBC untouched.
