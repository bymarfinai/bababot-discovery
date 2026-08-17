# BTC Temporal Friday F6.9 — Early-Sink Candidate Robustness

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — **SAME-SAMPLE ROBUST PASS**  
**Important:** candidate was discovered after F6.8 exploratory inspection; this is **not independent OOS confirmation**.  
**Research only:** live BBC untouched.

## Frozen candidate

At Friday +10m, exit the BUY at the actual +10m open only when all are true:

1. first completed 5m candle closed below entry;
2. position is still alive at +10m;
3. second completed 5m candle high remains below entry (no trade reclaim);
4. second completed 5m candle closes below EMA7;
5. second completed 5m candle body ratio is **<50%** of its candle range.

No threshold or EMA variant was changed during this robustness audit.

## Standalone economics

Parent Friday strategy:
- 138 trades
- 66W / 72L = **47.83% WR**
- PnL **+$64.630**
- PF **1.266**
- max DD **$56.530**

With the frozen +10m early-sink candidate:
- 138 trades
- WR remains **47.83%** because no winning trade is converted; this is loss-size management
- PnL **+$81.987**
- PF **1.364**
- max DD **$46.952**

Change:
- **+$17.357 PnL**
- Discovery **+$2.317**
- Validation **+$15.040**
- DD improvement **$9.577**

## Action cohort

- **10 actions**
- parent winners cut: **0**
- 8 actions improve / 2 worsen
- action-cohort parent PnL **-$35.387**
- after +10m cuts **-$18.030**
- rescued loss **+$17.357**

The ten acted trades contain:
- seven strict F6.6 immediate sinks;
- three additional parent losers;
- zero parent winners.

## Jackknife robustness

Remove each one of the ten actions one at a time:
- every leave-one-out variant remains positive;
- remaining aggregate improvement range **+$14.419 to +$19.520**.

Thus the result does not depend on one rescue trade.

## Chronological robustness — 4 blocks

Every action-bearing 4-way block is positive:
- B1: 2 actions, **+$1.979**
- B2: 2 actions, **+$0.338**
- B3: 3 actions, **+$6.950**
- B4: 3 actions, **+$8.090**

Fine 8-way blocks include two small negative micro-blocks corresponding to the two individually adverse actions, but the broad chronology remains positive and the candidate improves both frozen Discovery and Validation halves.

## Layered with frozen F6.5

The early +10m candidate and the frozen +60m `FAILURE_60 + dominant upper wick` cut have **zero overlap** in the historical action set.

Layering priority:
1. apply the +10m early-sink cut if triggered;
2. otherwise keep trade alive and, if applicable, apply frozen F6.5 at +60m.

Combined result:
- early actions: **10**
- later F6.5 actions: **6**
- overlap: **0**
- PnL **+$64.630 -> +$90.683**
- total improvement **+$26.052**
- Discovery **+$3.347**
- Validation **+$22.705**
- PF **1.266 -> 1.419**
- max DD **$56.530 -> $39.317**
- DD improvement **$17.213**

## Interpretation

This is the strongest evidence so far that Friday losses can be managed in multiple causal failure layers:

> **early failed acceptance around +10m -> cut early**  
> **later true rejection around +60m -> cut later**

The +10m candidate is especially valuable because it catches trades that often never recover to entry and would otherwise proceed toward the full -0.7% stop.

However, because the exact `below EMA7 + body<50%` recovery guard was identified after F6.8 exploratory inspection, it must remain labeled **same-sample provisional**. It should not be promoted to live solely from this 971-day result.

## Frozen next step

Do not retune the 50% body threshold or EMA choice on the same sample. Freeze the exact +10m candidate for:
- genuinely unseen Friday observations / future OOS extension;
- or a separately held-out historical extension if data beyond the current cutoff becomes available.

## Execution

- Workflow run: **32041463535** — success
- Artifact: `f69-output`, ID **9292031936**
- Script: `research/f69_friday_early_sink_candidate_robustness.py`
- Workflow commit: `d67b78045a2956b5ca6f656ef6c74f642b1299f5`
- Live BBC untouched.
