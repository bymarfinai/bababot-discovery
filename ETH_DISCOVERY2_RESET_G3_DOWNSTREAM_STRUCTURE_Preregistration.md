# ETH Discovery 2 Reset — G3 Downstream Structure Preregistration

**PREREGISTERED before result-bearing execution.**

## Frozen parent
G3 inherits only the historically supported G2 pair-native geometry:
- ETHUSDT Binance Futures raw 5m;
- direction **LONG**;
- reference start **01:30 UTC (08:30 WIB)**;
- reference duration **180m**;
- execution horizon **720m** immediately after the reference;
- reference = 01:30–04:30 UTC / 08:30–11:30 WIB;
- execution = 04:30–16:30 UTC / 11:30–23:30 WIB.

The G2 first-high-side pressure grammar is frozen. Old Z2/Z3 retest rules and old Z5 L06 entry are historical evidence only and are not inherited.

## Scientific question
> After a valid G2 first-high-side pressure event, what **causal pre-breakout path structure**, if any, produces a repeatable clean post-breakout continuation that can later support entry discovery?

G3 is structure-only. There is **no entry price, TP, SL, fee, leverage, PnL, or economics**.

## Data partitions
Reuse the frozen historical partitions:
- External: 2020-01-01 to 2022-01-01;
- Development: 2022-01-01 to 2025-01-01;
- Reference Validation: 2025-01-01 to 2026-07-30.

August 2026 remains descriptive only. Candidate selection reads Development only. External and Reference Validation remain closed until one Development structure is frozen.

## Frozen parent pressure signal
For each complete G2 session:
- H = maximum reference high;
- L = minimum reference low;
- R = H-L;
- LONG pressure signal = first valid HIGH-side touch during execution with completed close <= H, before a LOW-side touch, strict close outside H/L, or both-boundary ambiguity, exactly as in G1/G2.

Only sessions with that frozen parent pressure signal enter the G3 downstream analysis.

## Candidate path family
All candidate events are evaluated only **after** the completed parent pressure-signal bar.

### P0 — DIRECT
The first strict completed close > H after pressure, provided it occurs before any strict completed close < L or both-boundary ambiguity. That close is B00.

### P1 — LEAVE
Before B00, require at least one completed causal leave bar whose **high < H**. After that leave, the first strict completed close > H before strict close < L / ambiguity is B00.

### P2 — LEAVE → TOP-BAND RETEST → B00
After a completed leave (`high < H`), require a later completed bar that closes inside the top `dR` of the reference range:

`H - dR <= close <= H`

The retest must occur before strict close < L / ambiguity. After the retest, the first strict completed close > H before strict close < L / ambiguity is B00.

Frozen retest-depth grid:
- d = 0.01
- 0.02
- 0.05
- 0.10
- 0.15
- 0.20
- 0.30
- 0.40

`d=0.01` and `d=0.40` are explicit outer sentinels. They remain eligible for Development ranking, but if a RETEST winner lands on either sentinel, that depth family is declared boundary-open and holdouts are not opened.

Total Development structures = **10**: DIRECT, LEAVE, and 8 RETEST depths.

## B00 is not counted as success
G3 must not tautologically call a breakout trigger a winning continuation.

For every B00, define its completed close price `B` and inspect only bars **strictly after** the B00 bar.

Clean post-B00 extensions are:
- X05: price reaches `B + 0.05R` before a completed close back below H;
- X10: price reaches `B + 0.10R` before a completed close back below H;
- X20: price reaches `B + 0.20R` before a completed close back below H.

If target reach and close-back-below-H first occur on the same 5m bar, ordering is unknowable and the checkpoint is conservatively **not counted as success**. If neither occurs by execution end, it is not a success.

Thus all reported extension success happens after the causal B00 trigger and cannot be known at trigger time.

## Metrics per candidate
Report independently by partition:
- parent pressure signals;
- B00 trigger count;
- trigger participation = B00 / parent pressure signals;
- X05, X10, X20 successes and rates among B00 triggers;
- Wilson 95% lower bound for X10;
- median pressure-signal → B00 minutes;
- median B00 → X10 minutes among X10 successes.

## Development chronological stability
Sort parent pressure sessions chronologically and split into four near-equal blocks. For every candidate report B00 N, X10 rate, and X20 rate in each block.

A positive Development block requires:
- >=10 B00 triggers;
- X10 >=45%;
- X20 >=25%.

## Development gate
A candidate must satisfy ALL:
- >=60 B00 triggers;
- participation >=25% of parent pressure signals;
- X10 >=50%;
- X20 >=30%;
- Wilson 95% lower bound for X10 >=40%;
- >=3 of 4 positive Development blocks.

These gates test whether the structure is both executable often enough and capable of meaningful post-trigger extension; they do not optimize money outcomes.

## Retest-depth local stability
DIRECT and LEAVE have no tunable depth and need no coordinate-neighbor test.

For a RETEST candidate, its immediately adjacent preregistered depth values are supportive if they have:
- >=50 B00 triggers;
- X10 >=45%;
- X20 >=25%.

A RETEST candidate must have at least one supportive adjacent depth. This prevents promotion of an isolated depth spike.

## Development-only selection
Among candidates passing the Development gate and applicable local-stability gate, rank lexicographically by:
1. highest Wilson 95% lower bound for X10;
2. highest minimum block X10 among blocks with >=10 B00 triggers;
3. highest X20 rate;
4. highest X10 rate;
5. highest B00 trigger count;
6. shortest median pressure→B00 time;
7. simpler structure as deterministic tie-break: DIRECT, then LEAVE, then RETEST;
8. for RETEST ties, shallower retest depth first.

External and Reference Validation are not read during selection.

## Historical replication
Freeze the selected structure unchanged.

Each holdout must independently satisfy:
- >=25 B00 triggers;
- participation >=20%;
- X10 >=45%;
- X20 >=25%;
- Wilson 95% lower bound for X10 >=30%.

Both External and Reference Validation must pass. Pooled holdout is descriptive only and cannot rescue a failed individual partition.

## Decision rules
- If no Development candidate passes, status = `ETH_DISCOVERY2_RESET_G3_NO_DEV_CANDIDATE`.
- If selected RETEST depth lies on d=0.01 or d=0.40 sentinel, status = `ETH_DISCOVERY2_RESET_G3_RETEST_BOUNDARY_OPEN`; do not open holdouts.
- If the frozen interior/non-depth candidate fails either historical holdout, status = `ETH_DISCOVERY2_RESET_G3_CANDIDATE_NOT_REPLICATED`; no rescue or second-best substitution.
- If both holdouts pass, status = `ETH_DISCOVERY2_RESET_G3_SUPPORTED`.

A SUPPORTED G3 validates only a downstream structural trigger on frozen G2 geometry. It does not validate an entry. The next stage must rediscover entry timing/price on the frozen G2+G3 structure; old L06 may appear only as a historical comparator and must re-earn selection.

Research/shadow only. No live promotion.
