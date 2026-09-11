# ETH Temporal A1 — Scientific Verdict

## Status
COMPLETE. Development-only. OOS remained closed.

## Main finding
A primitive unconditional ETH time-of-day bias is **not economically sufficient** under the frozen assumptions.

Across 24 UTC hours × 2 directions × 6 fixed holds (288 combinations), the best robustness-ranked representative for every clock hour remained net-negative after the frozen $0.75 round-trip fee. Zero of 24 hourly representatives were positive-net in all three Development years (2022, 2023, 2024).

## Key metrics
- Data coverage: 100.000000%
- Hourly representatives with all three years net-positive: 0/24
- Representative direction split: LONG 14 / SHORT 10
- Robustness-ranked global representative: 16:00 WIB / LONG / H240
  - N 1096
  - WR 41.97%
  - net -$580.80
  - expectancy -$0.5299
  - PF 0.766
  - DD $593.22
  - max loss streak 9
  - minimum yearly expectancy -$0.5691
- Best pooled-expectancy hourly representative visible in the 24h map: 19:00 WIB / SHORT / H240
  - N 1096
  - WR 46.35%
  - net -$418.38
  - expectancy -$0.3817
  - PF 0.873
  - DD $498.46
  - max loss streak 8
  - still negative and therefore not an economic winner.

## Cross-check against prior ETH character work
Prior E12 found formal LONG character passes concentrated at 23:00–00:00, 00:00–01:00, 01:00–02:00, and 03:00–04:00 WIB after structural/state filtering. Temporal A1 deliberately removed those structure filters. The corresponding primitive hourly representatives in this same broad overnight habitat are all negative.

Therefore the evidence supports the following distinction:

> ETH does not appear to have a sufficient **unconditional clock-hour edge**. Its profitable Development behavior is conditional on market state / structure inside particular temporal habitats.

This does not invalidate E12. It clarifies what E12 was actually discovering: **time is a habitat prior, not the trading rule itself**.

## What should carry forward
- Do not search for a production strategy using hour + direction + fixed hold alone.
- Preserve pair-native structural conditioning.
- The next temporal-first stage, if pursued, should use time as the outer habitat and then discover a minimal causal state discriminator inside each habitat rather than reintroducing the entire 90-rule grammar at once.
- OOS remains closed.
