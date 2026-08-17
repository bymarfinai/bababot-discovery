# BTC Temporal Friday F6.11 — Causal Fibonacci Forensic

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — DESCRIPTIVE CAUSAL FORENSIC; FIB RELATION FOUND, NO RULE PROMOTED  
**Research only:** live BBC untouched.

## Question

Is the Friday early-sink / immediate-failure behavior related to Fibonacci structure around entry?

## Guardrail

All swing anchors use only completed 5m bars strictly before the Friday 15:00 WIB BUY entry. No future swing endpoint is used. Natural lookbacks only: 1h, 2h, 4h, 8h, 24h. Standard Fib levels only: 23.6%, 38.2%, 50%, 61.8%, 78.6%.

No Fib rule is promoted from this same sample.

## Cohorts

- All Friday parent trades: **138**
- First-5m-red: **58**
- Strict immediate sinks (first 5m red, then never trade back to entry): **10**
- First-5m-red recover/non-sink: **48**
- Frozen F6.9 EARLY10 actions: **10**

## Main finding

There **is** a causal pre-entry Fib/range relationship, strongest on the short 1h–2h structure, but it is not a simple “61.8% is bad” rule.

The strict immediate sinks tend to enter **higher in the recent range / after a shallower pullback from the recent high**.

### 2-hour structure

Strict sinks:
- median retracement depth from recent high: **32.7%**
- median range position: **67.3%** of the 2h low-to-high range
- median 2h range size: **1.39%**

First5-red recover trades:
- median retracement depth: **49.3%**
- median range position: **50.7%**
- median 2h range size: **0.815%**

Discrimination toward strict sink:
- 2h retracement depth AUC: **0.309 full / 0.288 Discovery / 0.320 Validation** (lower retracement depth = more sink-like)
- 2h range position AUC: **0.691 / 0.713 / 0.680**
- 2h range size AUC: **0.770 / 0.913 / 0.781**

Thus the clearest mechanism is:

> **large short-term expansion + BUY entry still near the upper part of that expansion + insufficient pullback = higher immediate-sink risk.**

### Natural 2h Fib zones among first5-red trades

Using nearest standard Fib level:
- nearest 23.6%: 20 trades, **5 sinks** (25.0%)
- nearest 38.2%: 9 trades, **1 sink** (11.1%)
- nearest 50%: 7 trades, **1 sink** (14.3%)
- nearest 61.8%: 7 trades, **2 sinks** (28.6%)
- nearest 78.6%: 15 trades, **1 sink** (6.7%)

This nearest-level table alone is too small/noisy to promote a discrete Fib level rule.

Using broad natural retracement depth instead:
- shallow <=38.2%: 23 first5-red trades, **5 sinks = 21.7%**
- 38.2%–61.8%: 17 trades, **4 sinks = 23.5%**
- deep >=61.8%: 18 trades, **1 sink = 5.6%**

So deep pullbacks were historically much less likely to become strict immediate sinks, but this is still descriptive and same-sample.

### Traditional bullish-swing-only 2h subset

Where the pre-entry low occurred before the pre-entry high (a conventional bullish Fib anchor), there were 30 first5-red cases and 6 sinks.

Of those 6 sinks:
- **5/6** were nearest the **23.6%** retracement level
- **1/6** nearest 38.2%
- **0/6** nearest 50%, 61.8%, or 78.6%

This is the cleanest intuitive Fib-shaped clue, but N=6 is too small to treat as a trading rule.

## 1-hour confirmation

The same general short-term idea appears at 1h:
- strict-sink median retracement depth: **38.7%**
- red-recover median retracement depth: **48.2%**
- range-position AUC: **0.713 full / 0.763 D / 0.677 V**

Again, sinks tend to occur with entry higher in the immediate pre-entry range.

## Important limitation

The relationship is **not universal across every horizon**. At the 24h horizon the geometry changes and strict sinks are not simply shallow daily retracements. Therefore the useful signal appears to be a **local 1h–2h expansion/pullback structure**, not a timeless Fib-level effect.

Also, the frozen F6.9 EARLY10 state itself is only moderately associated with these pre-entry Fib features. Fib appears more useful as an explanatory / potential early-risk context for the raw immediate-sink phenomenon than as a replacement for the +10m causal failed-acceptance detector.

## Interpretation

The Friday failure mechanism now has a plausible price-structure story:

1. price expands strongly over the prior 1–2 hours;
2. Friday BUY enters while price remains relatively high in that local range;
3. the market has not produced a meaningful retracement/support reset;
4. the first 5m loses acceptance;
5. a subset then becomes the immediate-sink cohort.

This suggests Fibonacci may be useful as a **pre-entry context layer**, especially shallow 23.6%–38.2% pullback after a large 2h expansion, but not yet as a standalone gate.

## Correct next experiment

Keep F6.9 and F6.5 frozen. If continuing this lead, test whether a pre-entry 1h/2h Fib-expansion context can identify a subset of first-5m-red trades at **+5m** that can be safely cut earlier than F6.9's +10m action, while protecting recoveries and validating D/V separately.

Do not threshold-sweep Fib levels on the same sample.

## Execution

- Workflow run: **32042518814** — success
- Artifact: `f611-output`, ID **9292213557**
- Script: `research/f611_friday_fibonacci_forensic.py`
- Workflow commit: `5da13922445b947b7f06e0d751f43d0330f2e057`
- Live BBC untouched.
