# SUN1.7 — Sunday16 Loss + Previous-Day Forensics

**Status: COMPLETE — forensic only; no adaptive rule promoted; live BBC untouched.**

## Parent reproduction
- N **139**, wins **66**, WR **47.48%**, PnL **$+63.60**, PF **1.14**.
- TP: 34 (34W/0L); SL: 53; timeout: 52 (32W/20L).

## Loss anatomy
- Winner median MFE/MAE: **2.51% / 0.46%**.
- Loser median MFE/MAE: **0.41% / 1.50%**.
- Losers that first reached favorable excursion: >=0.3%: 46, >=0.5%: 31, >=0.8%: 17, >=1.0%: 14, >=1.5%: 3, >=2.0%: 0.

## Post-entry checkpoint strongest continuous separators
- +15m alive 139 (66W/73L): mfe 0.596 (lower=loss), taker_mean 0.574 (higher=loss), ema_spread 0.568 (higher=loss)
- +30m alive 139 (66W/73L): mfe 0.596 (lower=loss), ema_spread 0.567 (higher=loss), close_vs_ema20 0.566 (lower=loss)
- +60m alive 138 (66W/72L): mfe 0.577 (lower=loss), ema_spread 0.560 (higher=loss), close_vs_ema20 0.533 (lower=loss)
- +120m alive 138 (66W/72L): ema_spread 0.681 (higher=loss), mfe 0.664 (lower=loss), progress 0.653 (lower=loss)
- +240m alive 135 (66W/69L): progress 0.704 (lower=loss), mfe 0.690 (lower=loss), mae 0.634 (higher=loss)
- +360m alive 128 (64W/64L): progress 0.786 (lower=loss), mfe 0.727 (lower=loss), ema_spread 0.696 (higher=loss)
- +720m alive 106 (54W/52L): progress 0.795 (lower=loss), mfe 0.786 (lower=loss), mae 0.701 (higher=loss)

## Previous-day / pre-entry strongest reproducible features
- ret48h: robust 0.578; D 0.578 higher=loss; V 0.673 higher=loss
- sat_day_ret: robust 0.569; D 0.601 higher=loss; V 0.569 higher=loss
- ret24h: robust 0.567; D 0.567 higher=loss; V 0.683 higher=loss
- ret6h: robust 0.565; D 0.613 higher=loss; V 0.565 higher=loss
- prior24_close_loc: robust 0.545; D 0.545 higher=loss; V 0.676 higher=loss
- sat18_to_sun12_ret: robust 0.541; D 0.541 higher=loss; V 0.640 higher=loss
- ret72h: robust 0.540; D 0.540 higher=loss; V 0.603 higher=loss
- sun_pre16_ret: robust 0.536; D 0.536 higher=loss; V 0.691 higher=loss

## Friday / Saturday / Sunday-pre16 sign patterns
- F+|S-|U+: N26, WR 38.5%, PnL -60.73; D 17 / 41.2% / -23.77; V 9 / 33.3% / -36.96
- F-|S+|U+: N23, WR 39.1%, PnL -5.14; D 14 / 42.9% / -8.49; V 9 / 33.3% / +3.35
- F-|S+|U-: N21, WR 33.3%, PnL -24.64; D 14 / 35.7% / -9.46; V 7 / 28.6% / -15.18
- F+|S+|U+: N20, WR 45.0%, PnL +19.31; D 13 / 46.2% / +19.34; V 7 / 42.9% / -0.03
- F+|S+|U-: N14, WR 50.0%, PnL -10.23; D 6 / 33.3% / -18.12; V 8 / 62.5% / +7.88
- F-|S-|U-: N13, WR 69.2%, PnL +69.68; D 7 / 57.1% / +29.36; V 6 / 83.3% / +40.32
- F-|S-|U+: N12, WR 41.7%, PnL +4.96; D 5 / 60.0% / +23.05; V 7 / 28.6% / -18.09
- F+|S-|U-: N10, WR 100.0%, PnL +70.40; D 7 / 100.0% / +41.98; V 3 / 100.0% / +28.41

## Assessment
- Reproducible pre-entry features >=0.60 robust strength: **none**.
- If this list is empty or weak, previous-day context is not yet strong enough for a causal adaptive router. Post-entry path separation may still be stronger.
- Forensic only. No threshold was tuned and no state is promoted to a trading rule on this same sample.
