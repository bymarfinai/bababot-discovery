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
