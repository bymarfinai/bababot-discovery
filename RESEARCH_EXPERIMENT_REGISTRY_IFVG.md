# BabaBot Research Registry — Failed / Inversion FVG Track

Purpose: prevent repeating, renaming, or post-hoc rescuing failed-FVG / inversion-FVG continuation studies generated from the AMD/FVG track.

## IFVG1 — completed far-edge failure close -> retest -> trade toward manipulation extreme — REJECT

Frozen mechanism:
- BTCUSDT USD-M perpetual, completed 1H only;
- inherits exact AMD1 3H accumulation, first-session manipulation, and exact immediate 3-candle opposite FVG;
- fixed session opens only: Asia 07:00 WIB, London 14:00 WIB, New York 20:00 WIB;
- search first 6 completed H1 candles after FVG confirmation for objective failure acceptance;
- original bearish FVG fails only on completed H1 close strictly above far/upper FVG edge -> inversion LONG candidate;
- original bullish FVG fails only on completed H1 close strictly below far/lower FVG edge -> inversion SHORT candidate;
- wick-through alone is not failure;
- after failure close, wait max 6 completed H1 candles for first retest of the failed far edge from the opposite side;
- entry = failed far edge;
- inversion LONG SL = original bearish FVG near/lower edge; TP = manipulation HIGH;
- inversion SHORT SL = original bullish FVG near/upper edge; TP = manipulation LOW;
- only modeled net-RR>=1:1 after 0.15% fee is executable;
- max hold 6H; fill-candle TP not credited; fill-candle SL and later same-bar ambiguity adverse-first.

Coverage: 2020-01-01 through available 2026-08-18 completed H1 archive, 58,128 rows, 253 exact AMD+FVG events.

Failure / retest behavior:
- development: 57/125 failure closes = 45.60%; 50/57 retested = 87.72%; 32 RR-eligible trades;
- reference validation: 17/47 failures = 36.17%; 14/17 retested = 82.35%; 7 eligible;
- historical robustness 2020-2021: 29/79 failures = 36.71%; 22/29 retested = 75.86%; 20 eligible;
- August: 1/2 failure, 1 retest, 1 eligible TIME trade.

Execution evidence:
- development: 3TP/29SL/0TIME, decisive WR9.38%, PnL -$24.50, expectancy -$0.77/trade, median risk0.12%, median net RR2.42;
- reference validation: 0TP/7SL/0TIME, WR0.00%, PnL -$12.18, expectancy -$1.74/trade, median risk0.19%, median net RR1.92;
- historical robustness: 6TP/14SL/0TIME, WR30.00%, PnL +$13.69, expectancy +$0.68/trade, median risk0.22%, median net RR3.04;
- August: 1 TIME, +$0.07.

Historical robustness chronological blocks:
- B1 N5: 0TP/5SL, WR0%, PnL -$6.17;
- B2 N5: 0TP/5SL, WR0%, PnL -$19.76;
- B3 N5: 3TP/2SL, WR60%, PnL +$27.55;
- B4 N5: 3TP/2SL, WR60%, PnL +$12.07.
Strong regime instability; no promotion.

Validation fixed cells all failed decisively: every RR-eligible inversion trade across the fixed session/side cells was a loss (7/7 SL). External positive cells are therefore non-promotable descriptive artifacts.

Verdicts:
- `IFVG1_SUPPORTED=FAIL`
- `IFVG1_80_CANDIDATE=FAIL`

Interpretation: AMD4's high stop-side hit rate cannot be converted into a robust reverse trade simply by waiting for a completed close through the FVG and then retesting the failed far edge. Although objective FVG failures are fairly common (about 36% OOS) and retests after failure are frequent (about 76-82% OOS), the failed edge itself remains a poor tight-risk entry: price often continues through the original FVG near edge after retest before reaching the manipulation extreme. The old observation `AMD4 stop is hit often` is therefore not equivalent to `trade the stop direction`.

Anti-rescue lock: do not enter immediately on failure close, downgrade acceptance to wick-through, add close buffers, alter retest depth, interpolate stop placement, change target, widen timing windows, or isolate a side/session after seeing IFVG1. Any future failed-FVG study must introduce genuinely new causal information rather than invert or retune IFVG1 on the same evidence.