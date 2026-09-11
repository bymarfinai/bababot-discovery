# ETH E14A — 24H Daily Campaign Scientific Verdict

**Status:** Development-only. OOS CLOSED. No live authorization.

## Frozen experiment
All 24 E12 hourly representative LONG characters were temporarily treated as eligible signal sources inside one campaign day from 23:00 WIB to next 23:00 WIB. Maximum campaign notional remained $500. Architectures tested 1–4 equal tranches under SEQUENTIAL_ANY, PRICE_IMPROVEMENT, and DISTINCT_HOUR_CONFIRM. All campaigns were forcibly flattened at the next 23:00 WIB boundary.

## Formal result
**ETH_E14A_NO_ROBUST_WR_PRESERVING_ARCHITECTURE**

No architecture passed the preregistered ROBUST + WR-preservation rules. No OOS was exposed.

## Daily single-entry baseline exposes the main problem
SEQUENTIAL_ANY_K1:
- N 886 campaigns
- WR 51.24%
- net +$513.57
- expectancy +$0.58/campaign
- PF 1.109
- DD $419.99
- max loss streak 6
- 2022 WR 52.58%, exp +$0.07
- 2023 WR 49.01%, exp +$0.57
- 2024 WR 52.22%, exp +$1.09

This daily-flat baseline is materially weaker than the native-hold E12/E13 evidence. Therefore E14A does **not** establish that the 24-hour characters or scale-in concept are invalid. The fixed 23:00 daily exit itself is a major architecture change and appears incompatible with the payoff horizons previously discovered (H240/H360/H720/H960).

## What scale-in did show

### PRICE_IMPROVEMENT_K2 — strongest balanced raw improvement versus daily k=1
- N 886
- WR 54.40%
- net +$583.84
- expectancy +$0.66
- PF 1.160
- DD $322.08
- LS 6
- avg entries 1.67
- capital utilization 83.63%
- average weighted-entry improvement +0.26%
- 2022 WR 57.04%, exp +$0.61
- 2023 WR 52.65%, exp +$0.53
- 2024 WR 53.58%, exp +$0.83

Relative to the daily k=1 baseline, K2 price-improvement raises WR, net, expectancy and PF while reducing DD with unchanged LS. However it fails the frozen ROBUST gate because pooled PF <1.20 and only one of three years reaches WR>=55%. It is therefore a **diagnostic raw pooled improvement**, not a formal winner.

### PRICE_IMPROVEMENT_K4 — highest campaign WR
- WR 56.09%
- net +$466.77
- expectancy +$0.53
- PF 1.181
- DD $249.52
- LS 5
- avg entries 2.49
- utilization 62.19%
- average entry improvement +0.46%

This confirms that requiring a better price before adding can lift campaign WR and reduce path risk, but increasing tranche count further sacrifices total economics under the fixed daily close.

### Unfiltered scale-in increases net but sacrifices WR
SEQUENTIAL_ANY_K4:
- WR 50.34%
- net +$695.56
- exp +$0.79
- PF 1.189
- DD $313.42
- LS 6

DISTINCT_HOUR_CONFIRM_K3:
- WR 49.77%
- net +$656.36
- exp +$0.74
- PF 1.189
- DD $310.00
- LS 7

These higher-net architectures are rejected for the current objective because they obtain economics by allowing campaign WR to deteriorate.

## Scientific interpretation
1. **Do not conclude that DCA/scale-in failed.** Price-improvement scale-in clearly improves several metrics relative to the daily-flat single-entry control.
2. **Do conclude that a universal 23:00 daily flat is not supported.** It discards the pair-native payoff-horizon information discovered in E12.
3. Blind or confirmation-only multi-entry is not acceptable because it can increase total PnL while degrading WR.
4. The most credible aggregation mechanism from E14A is **signal-required + price-improvement scale-in**, especially the two-entry form, but it must be retested with exit semantics that preserve native payoff horizons.

## Clean next scientific question
A follow-up experiment should isolate aggregation from exit distortion: retain the 24 hourly entry characters and fixed $500 campaign budget, but allow accepted tranches to preserve their frozen native E12 payoff horizons (or otherwise preregister a native-horizon campaign exit rule) rather than forcibly flattening at 23:00 WIB.

E14A itself is frozen as a failed daily-flat architecture screen and must not be retrospectively rescued by changing its exit rule.
