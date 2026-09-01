# ETH B27DX — S11B 16:00 Stale-Cancel Hybrid — Preregistration

## Purpose
Test one frozen habitat-specific freshness rule suggested by S11A while preserving the supported S10 hybrid management map.

## Frozen portfolio
- 05:00 UTC: fixed E25.
- 09:00 UTC: fixed E25.
- 10:00 UTC: S10 B27DQ-style E10 profit-lock runner, unchanged.
- 16:00 UTC: fixed E25 management, but entry is accepted only if F75 fills on the first eligible raw 5m bar after completed causal leave.
- R300/X360, F75 entry, F20 invalidation, fee/notional/stress conventions and global one-position chronological lock remain unchanged.

## Frozen 16:00 freshness rule
- IMMEDIATE only: delay_bars == 0.
- Any 16:00 fill one or more raw 5m bars after eligible_start is cancelled.
- No alternate 1/2/3-bar cutoff is allowed.
- Freshness is determined before entry and is therefore causal.

## Comparison baseline
Exact S10 hybrid portfolio.

## Frozen decision gate
S11B is supported only if all are true:
1. candidate/parity/freshness causal audit passes;
2. every major partition at 0 bps has PF > 1 and net > 0;
3. pooled 5 bps has PF > 1 and net > 0;
4. accepted N is at least 80% of S10;
5. pooled executable frequency is at least 1.10 trades/week;
6. pooled 0 bps WR, PF, expectancy, and net are all strictly higher than S10.

BTC-class WR/PF/expectancy remains diagnostic only.

## Evidence label
Exploratory/engineering validation. The 16:00 freshness hypothesis was formed after inspecting S11A across historical partitions; S11B is not pristine unseen OOS confirmation.

## Restrictions
No alternate freshness cutoff, geometry, target, stop, runner arm/gap/step, clock, leverage, fee, or live-code change.
