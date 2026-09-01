# ETH B27DX — S7F Bearish K1 Touch-Bar Quality — Preregistration

## Purpose
Test one final scale-free candle-rejection discriminator inside the current B27DX event-quality family: whether the first H-side K1 touch bar itself closes bearish (`close < open`).

S7E found bearish leave-bar quality close to, but below, the frozen promotion gate at 09:00. S7F does not combine filters and does not relax any gate.

## Frozen strategy
LONG; R300/X360; clocks 05:00,09:00,10:00,16:00 UTC; F75 entry; E25 target; F20 completed-close invalidation; same data, partitions, fees, notional, weekdays, causal grammar, and one-position semantics as S7A-S7E.

## Filter
`BEARISH_K1_BAR`: the completed first K1 H-touch candle has `close < open`.

K1 completes before the later causal leave and before any legal entry. No body/wick magnitude threshold is tested.

## Development gate
N>=20; retention>=50%; WR>=75%; PF>=1.50; expectancy>=+$0.80/trade; net>0.

## Replication gate
Only Development-promoted clocks are opened in External and Reference Validation. Each requires N>=10; retention>=40%; WR>=70%; PF>=1.20; expectancy>0; net>0.

## Portfolio / BTC diagnostic
Replicated clocks only; rerun global lock at 0 and 5 bps. BTC-quality requires pooled WR>=71.9%, PF>=2.22, expectancy>=+$1.26, all major partitions PF>1/net>0, and pooled 5bps PF>=1/net>=0.

## Statuses
- `ETH_S7F_CAUSAL_AUDIT_FAILED`
- `ETH_S7F_NO_DEV_BEARISH_K1_FILTER`
- `ETH_S7F_DEV_FILTERS_NOT_REPLICATED`
- `ETH_S7F_BEARISH_K1_FILTERS_REPLICATED_BELOW_BTC`
- `ETH_S7F_BEARISH_K1_PORTFOLIO_BTC_QUALITY_SUPPORTED`

If S7F does not promote, do not continue adding candle-shape filters inside this family. Research only.