# BabaBot Research Registry — AMD / FVG Track

Purpose: prevent repeating or renaming accumulation-manipulation-distribution and FVG sequence studies.

## AMD1 — H1 Accumulation -> first-session Manipulation -> exact 3-candle opposite FVG -> Distribution — REJECT

Frozen design:
- BTCUSDT USD-M perpetual;
- completed 1H candles only;
- fixed session opens only: Asia 00:00 UTC / 07:00 WIB, London 07:00 UTC / 14:00 WIB, New York 13:00 UTC / 20:00 WIB;
- accumulation = exactly three completed H1 bars immediately before session open;
- manipulation = first H1 session candle only;
- bearish candidate: high sweeps accumulation high, no low sweep, closes back inside range -> SHORT;
- bullish candidate: low sweeps accumulation low, no high sweep, closes back inside range -> LONG;
- FVG triplet fixed as manipulation candle + next two H1 candles;
- bearish FVG requires middle candle bearish and `high(third) < low(manipulation)`;
- bullish FVG requires middle candle bullish and `low(third) > high(manipulation)`;
- no later FVG search, no minimum gap/body/ATR/EMA/volume/OI/taker filter;
- AMD baseline entry = next H1 open after manipulation;
- AMD+FVG entry = next H1 open after third FVG candle closes;
- structural SL = manipulation extreme;
- TP sized for modeled net RR1:1 after 0.15% round-trip fee; max hold 6H; same-hour ambiguity adverse-first.

Evidence coverage: 2020-01-01 through available 2026-08-18 completed H1 archive, 58,128 rows.
Manipulation events: 2,157. Exact FVG confirmations: 253, conversion 11.73%.

Aggregate +3H directional rate:
- reference development: AMD baseline N1031 54.22%; AMD+FVG N125 52.00%;
- reference validation: baseline N443 52.82%; FVG N47 55.32%;
- untouched external 2020-2021: baseline N661 51.44%; FVG N79 50.63%;
- August 2026 available data: baseline N21 61.90%; FVG N2 0.00%.

External FVG blocks: 47.37%, 45.00%, 65.00%, 45.00% +3H. No stable directional support.

Fixed validation cells that appeared high-WR were too small and failed transfer:
- ASIA_OPEN SHORT FVG validation 4/5 = 80.00%, external 7/12 = 58.33%;
- NEW_YORK_OPEN SHORT FVG validation 8/10 = 80.00%, external 8/16 = 50.00%.
These are explicitly non-promotable and must not be isolated post-hoc.

Executable net-RR1:1 was substantially worse after waiting for the exact FVG:
- validation FVG N47 decisive WR19.15%, PnL -$226.20, expectancy -$4.81/trade, median structural risk 1.09%;
- external FVG N79 decisive WR16.46%, PnL -$786.02, expectancy -$9.95/trade, median structural risk 1.99%;
- August FVG N2, WR0%, PnL -$11.83.

Verdicts:
- `AMD1_FVG_DIRECTION_SUPPORTED=FAIL`
- `AMD1_80_CANDIDATE=FAIL`
- `AMD1_EXECUTION_SUPPORTED=FAIL`

Interpretation: the exact screenshot-style sequence (3H accumulation, first-session sweep/reclaim, immediate opposite H1 FVG, then entry) is rare and does not robustly improve directional accuracy. Waiting three H1 bars for a strict FVG materially worsens structural entry geometry: price is often already far from the manipulation extreme, expanding the stop distance and making net 1:1 execution poor.

Do not rescue AMD1 by post-hoc isolating Asia/NY SHORT, loosening the FVG definition, searching later FVGs, changing accumulation length, adding minimum FVG size, or retuning execution on the same evidence. Any future AMD/FVG study must use a materially different causal mechanism and be preregistered independently.

## AMD2 — exact AMD1 FVG -> first mitigation/retest entry -> opposite accumulation boundary Distribution TP — REJECT

Materially different mechanism from AMD1:
- retain the exact frozen AMD1 accumulation, first-session manipulation and exact 3-candle opposite FVG;
- after FVG confirmation, wait max 6 completed H1 candles for first touch of the near FVG boundary;
- SHORT entry = bearish FVG lower/near boundary; LONG entry = bullish FVG upper/near boundary;
- structural SL remains manipulation extreme;
- primary Distribution TP = opposite side of original 3H accumulation range;
- primary trade only exists when that TP provides modeled net RR >=1:1 after 0.15% fee;
- secondary diagnostic uses synthetic fixed net1R target;
- max hold 6H from mitigation fill;
- conservative fill-candle handling: fill-candle SL counts adverse-first; fill-candle TP is not credited because target may have occurred before the limit fill intrabar.

Coverage: 2020-01-01 through available 2026-08-18 completed H1 archive, 58,128 rows; exact FVG events 253.

Mitigation fill behavior:
- development: 83/125 filled = 66.40%;
- reference validation: 28/47 = 59.57%;
- external 2020-2021: 61/79 = 77.22%;
- August: 2/2 = 100%.
Thus FVG retests are common enough, but the opposite accumulation boundary almost never offers minimum net RR1:1 from the first-touch entry.

Primary Distribution RR-eligible counts / result:
- development: only 7/125 eligible; 0TP/4SL/3TIME, decisive WR0%, PnL -$19.85;
- reference validation: only 1/47 eligible; 0TP/0SL/1TIME, PnL -$0.14;
- external: only 3/79 eligible; 1TP/1SL/1TIME, decisive WR50%, PnL +$5.28;
- August: 0/2 eligible.
This means the screenshot-style `FVG entry -> opposite accumulation boundary as Distribution TP` usually has insufficient geometric reward relative to the manipulation-extreme stop once fee is included.

Secondary fixed net1R diagnostic on structurally valid FVG mitigation fills:
- development: N83, decisive WR28.57%, PnL -$106.58;
- reference validation: N28, decisive WR27.78%, PnL -$34.17;
- external: N61, decisive WR41.38%, PnL -$75.48;
- August: one valid completed diagnostic, PnL -$2.12.
External net1R blocks: B1 N15 WR83.33% +$14.80; B2 N15 WR37.50% -$28.04; B3 N15 WR37.50% -$48.47; B4 N16 WR14.29% -$13.78. Strong decay / no stability.

Descriptive side/session cells are NOT promotable. Examples: external London SHORT net1R N9 WR80% +$21.55 and external NY LONG N8 WR100% approximately flat PnL, but reference-validation does not support a corresponding robust cell and these were observed only after the aggregate test.

Verdicts:
- `AMD2_DISTRIBUTION_SUPPORTED=FAIL`
- `AMD2_80_CANDIDATE=FAIL`
- `AMD2_NET1R_SUPPORTED=FAIL`

Interpretation: using the FVG as a mitigation entry zone is more faithful to the requested execution model and materially improves entry location versus AMD1 chase entry, but it still does not create a robust executable edge under the frozen H1 geometry. The main structural failure is that the opposite accumulation boundary is usually too close to provide net RR1:1 relative to the manipulation-extreme stop; forcing a synthetic net1R target also fails OOS.

Do not rescue AMD2 by choosing midpoint/25%/75% FVG entries, extending the mitigation window, changing accumulation length, allowing later FVGs, post-hoc isolating London SHORT or NY LONG, or altering the Distribution TP after seeing this evidence.