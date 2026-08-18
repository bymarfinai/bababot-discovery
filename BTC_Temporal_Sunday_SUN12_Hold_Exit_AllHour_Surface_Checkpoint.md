# BTC Sunday — SUN1.2 Hold/Exit + All-Hour Executable Surface

**Status: COMPLETE — discovery-only selection, validation reported; live BBC untouched.**

## Definition
- 139 Sundays; discovery 83 / validation 56.
- Holds: 1h, 2h, 4h, 6h, 8h, 12h, 18h.
- TP 0.3–2.5% step 0.1; SL 0.3–1.5% step 0.1.
- $500 notional, 0.15% round-trip fee, historical funding, adverse-first same-5m ambiguity.

## Sunday 01:00 WIB BUY — hold/exit search
- discovery robust cells: **0**
- selected: **hold 18h / TP 0.6% / SL 1.3%**
- D: **$+3.026**, WR **67.47%**, PF **1.026**, DD **$33.020**, blocks **3/5**
- V: **$-24.701**, WR **57.14%**, PF **0.714**
- Full: **$-21.675**, WR **63.31%**, PF **0.894**, DD **$58.856**

### Best discovery cell by hold
- 1h: TP 0.4/SL 1.0 → D -44.81, WR 30.1%, PF 0.34; V -31.74
- 2h: TP 0.4/SL 1.0 → D -35.16, WR 37.3%, PF 0.50; V -39.80
- 4h: TP 0.4/SL 1.0 → D -14.78, WR 50.6%, PF 0.77; V -35.89
- 6h: TP 0.4/SL 1.1 → D -17.69, WR 59.0%, PF 0.77; V -53.08
- 8h: TP 0.4/SL 1.1 → D -10.64, WR 65.1%, PF 0.86; V -45.41
- 12h: TP 0.5/SL 1.3 → D -9.50, WR 63.9%, PF 0.90; V -33.65
- 18h: TP 0.6/SL 1.3 → D +3.03, WR 67.5%, PF 1.03; V -24.70

## All Sunday hours — discovery champion
- **18:00 WIB SELL / hold 18h / TP 1.9% / SL 0.7%**
- D: **$+55.362**, WR **40.96%**, PF **1.275**, blocks **4/5**
- V: **$-17.848**, WR **33.93%**, PF **0.879**
- Full: **$+37.514**, WR **38.13%**, PF **1.108**, DD **$42.618**

- total discovery-robust cells: **39**; of those validation-positive/PF>1: **9**

## Best discovery-selected candidate per Sunday hour
- 18:00 SELL 18h TP1.9/SL0.7: D +55.4, WR 41.0%, PF 1.28, blocks 4/5; V -17.8, PF 0.88 — Drobust=True Vpass=False
- 16:00 SELL 18h TP2.5/SL1.4: D +53.9, WR 48.2%, PF 1.20, blocks 4/5; V +9.7, PF 1.05 — Drobust=True Vpass=True
- 17:00 SELL 18h TP2.2/SL0.7: D +47.8, WR 37.3%, PF 1.22, blocks 4/5; V +8.6, PF 1.06 — Drobust=True Vpass=True
- 21:00 SELL 18h TP2.5/SL0.7: D +39.4, WR 34.9%, PF 1.18, blocks 4/5; V +9.0, PF 1.06 — Drobust=True Vpass=True
- 19:00 SELL 18h TP1.7/SL0.7: D +30.6, WR 41.0%, PF 1.15, blocks 4/5; V -10.1, PF 0.93 — Drobust=True Vpass=False
- 13:00 SELL 18h TP1.3/SL1.4: D +21.8, WR 50.6%, PF 1.10, blocks 4/5; V -63.1, PF 0.64 — Drobust=True Vpass=False
- 14:00 SELL 18h TP2.3/SL1.2: D +41.4, WR 47.0%, PF 1.17, blocks 3/5; V -14.6, PF 0.92 — Drobust=False Vpass=False
- 20:00 SELL 18h TP2.4/SL0.7: D +38.9, WR 38.6%, PF 1.18, blocks 3/5; V +19.2, PF 1.13 — Drobust=False Vpass=True
- 15:00 SELL 18h TP2.3/SL1.4: D +35.9, WR 49.4%, PF 1.13, blocks 2/5; V -9.9, PF 0.95 — Drobust=False Vpass=False
- 12:00 SELL 18h TP1.1/SL1.5: D +28.9, WR 61.4%, PF 1.16, blocks 3/5; V -88.6, PF 0.51 — Drobust=False Vpass=False
- 23:00 SELL 12h TP1.5/SL1.5: D +28.2, WR 51.8%, PF 1.13, blocks 3/5; V -46.9, PF 0.77 — Drobust=False Vpass=False
- 22:00 SELL 12h TP1.4/SL1.4: D +22.4, WR 56.6%, PF 1.11, blocks 3/5; V -44.9, PF 0.76 — Drobust=False Vpass=False
- 09:00 SELL 18h TP0.4/SL1.5: D +5.6, WR 81.9%, PF 1.07, blocks 3/5; V -57.5, PF 0.42 — Drobust=False Vpass=False
- 01:00 BUY 18h TP0.6/SL1.3: D +3.0, WR 67.5%, PF 1.03, blocks 3/5; V -24.7, PF 0.71 — Drobust=False Vpass=False
- 00:00 BUY 12h TP2.2/SL0.7: D +3.0, WR 42.2%, PF 1.02, blocks 3/5; V +0.1, PF 1.00 — Drobust=False Vpass=True
- 07:00 BUY 18h TP0.9/SL1.4: D -6.6, WR 59.0%, PF 0.96, blocks 2/5; V +18.5, PF 1.20 — Drobust=False Vpass=True
- 03:00 BUY 18h TP1.1/SL1.5: D -7.7, WR 50.6%, PF 0.96, blocks 3/5; V +23.7, PF 1.30 — Drobust=False Vpass=True
- 10:00 BUY 12h TP1.6/SL0.3: D -9.6, WR 30.1%, PF 0.93, blocks 3/5; V -20.1, PF 0.75 — Drobust=False Vpass=False
- 06:00 BUY 18h TP1.2/SL1.3: D -9.9, WR 54.2%, PF 0.95, blocks 2/5; V +6.9, PF 1.06 — Drobust=False Vpass=True
- 04:00 BUY 18h TP0.9/SL1.0: D -11.6, WR 54.2%, PF 0.93, blocks 2/5; V -12.6, PF 0.88 — Drobust=False Vpass=False
- 11:00 SELL 18h TP0.9/SL1.5: D -13.5, WR 57.8%, PF 0.93, blocks 1/5; V -50.2, PF 0.64 — Drobust=False Vpass=False
- 02:00 BUY 12h TP0.9/SL0.8: D -14.7, WR 48.2%, PF 0.88, blocks 2/5; V -37.4, PF 0.60 — Drobust=False Vpass=False
- 08:00 SELL 12h TP0.6/SL1.5: D -15.1, WR 60.2%, PF 0.87, blocks 2/5; V -78.2, PF 0.36 — Drobust=False Vpass=False
- 05:00 SELL 12h TP0.5/SL1.2: D -26.5, WR 62.7%, PF 0.77, blocks 2/5; V -58.1, PF 0.42 — Drobust=False Vpass=False

## Guardrail
All selections above are based on discovery only. Validation is a test, not a tuning input.
