# BabaBot Research Registry — Session Sweep / Daily High-Low Track

Purpose: prevent repeating or renaming the BTC session-transition daily-high/low sweep studies.

## TS-HILO V2 — three sessions, open+close, sweep/reclaim, structural 1R — REJECT
Frozen mechanism:
- six anchors/day: Asia open/close, London open/close, New York open/close;
- known daily/frozen high-low only;
- first 90m after each anchor;
- 15m same-candle sweep + reclaim;
- entry next 15m open;
- structural SL at sweep extreme;
- TP gross 1R; max hold6h; fee0.15%; no 1m.

Historical 2023-12-02 to 2026-07-30: 1,451 events.
Best fixed cell: `ASIA_OPEN HIGH->SHORT` N68, 43TP/25SL, decisive WR63.24%, last30 WR66.67%; still negative after modeled fee because median risk only ~0.31%.
No fixed anchor+side met preregistered descriptive-support gate; no 80% candidate.
Broad OPEN aggregate WR49.68%; CLOSE aggregate WR48.23%.
August through available 2026-08-18 data: 19 events; no robust transfer result.
Do not rerun by shifting session anchors/windows, flipping direction, or changing RR on the same sample.

## AOH1 — Asia Open HIGH failed-acceptance immediate bearish breakdown confirmation — REJECT
Hypothesis generated from the best TS-HILO cell but externally validated.
Frozen rule:
1. previous UTC day HIGH;
2. first90m Asia Open;
3. completed15m sweep above PDH and close below PDH;
4. immediately following15m candle bearish and closes below reclaim-candle LOW;
5. SHORT next15m open;
6. SL at reclaim HIGH;
7. TP sized so modeled net reward equals modeled net loss after 0.15% round-trip fee: raw target distance = structural risk +0.30%; max hold6h.

Evidence:
- External untouched 2022-01-01 to 2023-12-02: 45 reclaim candidates, 14 confirmed trades, 5TP/9SL, decisive WR35.71%, PnL -$27.33 at $500 reference notional.
- External blocks: 66.67%, 50.00%, 0.00%, 25.00%; only first block positive.
- Reference 2023-12-02 to 2026-07-30: 68 reclaim candidates, 25 confirmed, 5TP/20SL, WR20.00%, PnL -$44.27.
- August 2026 available data: 0 reclaim candidates / 0 trades.
Verdicts: `AOH1_EXTERNAL_SUPPORT=FAIL`; `AOH1_80_CANDIDATE=FAIL`.

Interpretation: requiring immediate bearish displacement below the reclaim-candle low does NOT improve Asia-open high-sweep reversal reliability. It appears to select moves where reversal timing is already too late or continuation risk remains high. Do not rescue by allowing a later confirmation candle, weakening the close-below-low rule, changing PDH definition, shifting Asia time/window, or retuning RR on the same data.

## AOH2 — Asia Open context threshold grid (PRE_UP60 + prior-day range location) — REJECT
Frozen core setup remained Asia Open PDH immediate reclaim -> SHORT next15m open, structural SL, TP sized for modeled net RR1:1 after 0.15% fee. Exactly 42 context combinations were searched on reference-development only: PRE_UP60 minimum {0,0.05,0.10,0.15,0.20,0.30,0.50%} x prior-day range location minimum {70,75,80,85,90,95%}.
Selected by Wilson lower bound: PRE_UP60 >=0.20%, location>=70%.
Evidence:
- development N28, WR50.00%, PnL -$4.71;
- reference validation N8, WR50.00%, PnL +$1.15;
- external 2022-2023 N27, WR33.33%, PnL -$21.47;
- August 2026 N0.
Verdicts: `AOH2_CONTEXT_SUPPORTED=FAIL`; `AOH2_80_CANDIDATE=FAIL`.
Do not rerun wider threshold grids, add extra context indicators, or rescue with post-hoc weekday/time filters on the same samples.

## H1-MAP V1 — fixed session anchors, offsets -3h..+3h, causal prior-3H range — DESCRIPTIVE ONLY / NO 70-80% CELL
Purpose: test whether recurring structure exists before or after the six session anchors on 1H candles rather than only at the anchor itself.
Frozen design:
- BTCUSDT 1H;
- six fixed Asia/London/New York open+close anchors;
- fixed offsets -3,-2,-1,0,+1,+2,+3h;
- each event candle classified against only the completed prior3H range as HIGH_REJECT / LOW_REJECT / HIGH_ACCEPT / LOW_ACCEPT / INSIDE / BOTH;
- directional follow-through measured from the next1H open over next1H and next3H;
- no TP/SL/RR/fee optimization.

Historical 2022-01-01 through 2026-07-30: 70,182 anchor-offset records; August through available 2026-08-18: 751.
Strongest fixed directional cells by next3H direction:
- `LONDON_OPEN -3h LOW_REJECT -> LONG`: N180, +3H 61.7%;
- `LONDON_CLOSE +2h LOW_REJECT -> LONG`: N210, +3H 61.0%;
- `ASIA_CLOSE 0h LOW_REJECT -> LONG` / equivalently `LONDON_OPEN +1h`: N220, +3H 60.9%;
- `LONDON_CLOSE +3h LOW_REJECT -> LONG` / equivalently `NEW_YORK_CLOSE -3h`: N200, +3H 60.0%;
- `ASIA_OPEN 0h HIGH_REJECT -> SHORT`: N235, +3H 57.9%.
No fixed cell met `STRONG_REPEATABLE_DIRECTION` >=70%; no descriptive 80% cell.
Pure pretrend-turn timing without sweep condition peaked only around 58.5% reversal; exact seven-hour U/D color sequences were diffuse (~1-2% each) and none met stability criteria.

Interpretation: 1H before/after mapping DOES reveal recurring reaction zones, especially LOW_REJECT reactions around several absolute hours, but not a deterministic 70-80% pattern by session offset + simple prior3H range event alone. Do not claim an 80% 1H pattern or rerun the same map with shifted anchors/range lengths after seeing this result.
