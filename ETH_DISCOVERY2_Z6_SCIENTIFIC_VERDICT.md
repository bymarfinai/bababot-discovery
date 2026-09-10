# ETH Discovery 2 — Z6 Scientific Verdict

**Verdict: CANDIDATE NOT REPLICATED.**

Z6 translated the supported Z5 L06 entry into a preregistered 150-configuration coarse money-geometry search using fixed $500 notional, $0.75 round-trip cost, no compounding, and R-normalized TP/SL/hold parameters.

## Development-selected configuration
**F95 / TP 0.60R / SL 0.30R / hold 120m**

Development:
- 48 trades.
- Net WR 45.83%.
- Net PnL +$35.41.
- Expectancy +$0.74/trade.
- PF 1.395.
- Max DD $13.96.
- Max loss streak 5.
- 3/4 positive chronological blocks.

The selected TP sat on the upper search boundary, but no boundary extension is permitted because the candidate failed holdout replication.

## Historical replication
- External: 35 trades, 31.43% WR, **-$51.12**, expectancy -$1.46/trade, PF 0.480, max DD $51.97 — FAIL.
- Reference Validation: 22 trades, 45.45% WR, +$16.50, expectancy +$0.75/trade, PF 1.440 — PASS.
- Pooled holdout: 57 trades, 36.84% WR, **-$34.62**, expectancy -$0.61/trade, PF 0.745 — FAIL.

All historical partitions combined were approximately flat: 105 trades, +$0.79 net, 40.95% WR, PF 1.004, max DD $54.89.

## Scientific meaning
The Z5 L06 entry geometry is structurally supported, but a single static entry-relative TP/SL/hold geometry selected from Development does not translate robustly across historical partitions. The failure is especially concentrated in External and cannot be rescued by choosing another Z6 grid configuration after holdout inspection or by extending the TP boundary.

The next lineage must use an independently motivated management mechanism. The strongest available pair-native basis is the already-replicated Z5 checkpoint structure (C20/C30/C40), not post-hoc retuning of the failed Z6 winner.

Research/shadow only. No live promotion.
