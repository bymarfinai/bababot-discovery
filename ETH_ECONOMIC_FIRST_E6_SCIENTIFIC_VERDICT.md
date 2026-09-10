# ETH Economic-First E6 — Scientific Verdict

**Status: `ETH_ECONOMIC_FIRST_E6_NO_DEV_CANDIDATE`.**

E6 froze the E5 economic substrate:

**17:00 UTC / lookback360m / causal strength B0_20 / MOMENTUM / exact-open entry**

and tested 336 fee-adjusted TP × SL × hold management cells.

## Formal preregistered verdict
No candidate passed the full preregistered gate requiring simultaneously:
- WR >=55%;
- expectancy >=+$0.75/trade;
- PF>=1.20;
- DD<=$100;
- loss streak<=8;
- 3/4 positive blocks;
- local support.

Therefore E6 is formally closed and its threshold is not relaxed post hoc.

## Critical management finding
The grid nevertheless reveals a strong **high-WR positive-economic no-SL harvest ridge**, materially different from the tiny-TP high-WR/negative-PnL cells.

### E6 ridge seed
**TP 0.60% / SL NONE / hold720m**
- N153
- WR **78.43%**
- net **+$64.30**
- expectancy **+$0.4203/trade**
- PF **1.321**
- max DD **$44.43**
- max loss streak **4**
- positive blocks **4/4**
- TP exit rate **76.47%**
- time-exit rate **23.53%**

This cell fails E6 only because expectancy is below the preregistered +$0.75 floor. It is not promoted under E6.

Nearby no-SL / hold720 cells demonstrate the WR-payoff frontier:
- TP0.40%: WR85.62%, exp+$0.107, PF1.112, DD$31.56;
- TP0.60%: WR78.43%, exp+$0.420, PF1.321, DD$44.43;
- TP0.80%: WR69.93%, exp+$0.419, PF1.238, DD$36.31;
- TP1.00%: WR64.05%, exp+$0.457, PF1.220, DD$46.60;
- TP2.00%: WR52.29%, exp+$0.596, PF1.214, DD$93.79.

The very small TP cells prove that WR alone can be misleading: TP0.20% / no-SL / hold720 reached WR90.20% but net -$83.84 and PF0.292 because the $0.75 fee leaves only ~$0.25 net on each TP win while a small number of large time-exit losses erase many winners.

Numeric static stops generally degraded the 0.60% TP economics, confirming that the favorable ridge is specifically a **no-SL early-harvest + bounded time-exit** shape.

## Next justified experiment
Do not lower E6's gate and do not rerun the full 336-cell grid. Instead preregister a new, bounded **E7 high-WR harvest-ridge refinement** around the discovered no-SL TP0.60% / hold720m seed, with External and Reference Validation still closed until one Development rule is frozen.

E7 should answer whether this ridge is locally stable and historically replicable, not whether another arbitrary static bracket can be found.

Research/shadow only. No live promotion or profit guarantee.
