# Sunday 09:00 WIB SELL — SUN1.3 TP/SL Deep Dive

**All TP/SL combinations from SUN1.2 were retested for this hour only. Live BBC untouched.**

- SELL cells tested: **2093** = 7 holds × 23 TP values × 13 SL values.
- TP grid 0.3–2.5 step 0.1; SL grid 0.3–1.5 step 0.1; holds 1/2/4/6/8/12/18h.

## Exact TP0.4 / SL0.4 by hold
- 1h: D -52.63, WR 34.9%, PF 0.32; V -51.89, WR 19.6%, PF 0.17; Full -104.51
- 2h: D -62.64, WR 33.7%, PF 0.31; V -54.62, WR 25.0%, PF 0.20; Full -117.26
- 4h: D -62.64, WR 43.4%, PF 0.38; V -51.44, WR 30.4%, PF 0.26; Full -114.08
- 6h: D -60.91, WR 44.6%, PF 0.42; V -49.37, WR 35.7%, PF 0.31; Full -110.27
- 8h: D -57.57, WR 48.2%, PF 0.46; V -52.44, WR 39.3%, PF 0.33; Full -110.02
- 12h: D -56.51, WR 51.8%, PF 0.49; V -61.94, WR 37.5%, PF 0.30; Full -118.45
- 18h: D -55.83, WR 51.8%, PF 0.49; V -64.14, WR 39.3%, PF 0.30; Full -119.97

## 18h: TP fixed 0.4, SL sweep
- SL 0.3: D -60.47, WR 43.4%, PF 0.43; V -57.83, PF 0.29; Full -118.30
- SL 0.4: D -55.83, WR 51.8%, PF 0.49; V -64.14, PF 0.30; Full -119.97
- SL 0.5: D -44.00, WR 60.2%, PF 0.59; V -76.11, PF 0.27; Full -120.12
- SL 0.6: D -38.18, WR 65.1%, PF 0.64; V -81.19, PF 0.28; Full -119.37
- SL 0.7: D -30.09, WR 69.9%, PF 0.71; V -90.12, PF 0.26; Full -120.21
- SL 0.8: D -30.06, WR 72.3%, PF 0.72; V -91.33, PF 0.27; Full -121.39
- SL 0.9: D -24.33, WR 74.7%, PF 0.76; V -89.20, PF 0.28; Full -113.53
- SL 1.0: D -28.71, WR 74.7%, PF 0.73; V -84.54, PF 0.31; Full -113.26
- SL 1.1: D -36.39, WR 74.7%, PF 0.68; V -88.15, PF 0.30; Full -124.55
- SL 1.2: D -13.38, WR 78.3%, PF 0.86; V -80.07, PF 0.32; Full -93.45
- SL 1.3: D -1.89, WR 80.7%, PF 0.98; V -74.84, PF 0.35; Full -76.72
- SL 1.4: D -6.39, WR 80.7%, PF 0.93; V -68.77, PF 0.37; Full -75.16
- SL 1.5: D +5.63, WR 81.9%, PF 1.07; V -57.52, PF 0.42; Full -51.89

## Outcome anatomy, 18h
- 0.4/0.4: full TP/SL/timeout **64/73/2**, full PnL **-119.97**, WR **46.8%**, PF **0.40**.
- 0.4/1.5: full TP/SL/timeout **101/11/27**, full PnL **-51.89**, WR **73.4%**, PF **0.71**.

## Guardrail
Selection remains discovery-only; validation is shown only as a robustness check.
