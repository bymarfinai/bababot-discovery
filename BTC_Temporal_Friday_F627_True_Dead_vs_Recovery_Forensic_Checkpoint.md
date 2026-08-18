# Friday F6.27 — FAILED_LAUNCH_10 True-Dead vs Recovery Forensic

**Status: COMPLETE — FORENSIC ONLY; NO RULE TUNED/PROMOTED.**
**Live BBC untouched; F6.26 remains failed and is NOT frozen.**

## Cohorts
- true failure-to-develop caught by F6.26: **9** (D 4 / V 5)
- false-positive eventual winners: **13** (D 9 / V 4)
- other acted losers, secondary only: **4**

## Strongest causal separators available by +10m
- `b2_lower_wick_ratio`: strength full/D/V **0.821/0.833/0.850**, higher=dead; median dead/winner **0.2530/0.0694**; LOO median **0.811**
- `pre_last_body_ratio`: strength full/D/V **0.778/0.722/1.000**, higher=dead; median dead/winner **0.7792/0.4744**; LOO median **0.774**
- `pre_last_red`: strength full/D/V **0.769/0.722/0.875**, higher=dead; median dead/winner **1.0000/0.0000**; LOO median **0.769**
- `b2_body_ratio`: strength full/D/V **0.718/0.750/0.750**, lower=dead; median dead/winner **0.5296/0.7595**; LOO median **0.718**
- `b2_close_location`: strength full/D/V **0.726/0.750/0.700**, higher=dead; median dead/winner **0.2749/0.0694**; LOO median **0.721**
- `pre_last_upper_wick_ratio`: strength full/D/V **0.821/0.694/0.850**, lower=dead; median dead/winner **0.0007/0.2714**; LOO median **0.815**
- `b2_taker`: strength full/D/V **0.709/0.750/0.650**, higher=dead; median dead/winner **-0.1325/-0.2420**; LOO median **0.703**
- `pre_last_lower_wick_ratio`: strength full/D/V **0.641/0.667/0.700**, lower=dead; median dead/winner **0.1895/0.1889**; LOO median **0.657**
- `b2_break_b1_low_close`: strength full/D/V **0.662/0.639/0.675**, lower=dead; median dead/winner **0.0000/1.0000**; LOO median **0.653**
- `pre30_entry_pos`: strength full/D/V **0.744/0.583/1.000**, lower=dead; median dead/winner **0.0995/0.2743**; LOO median **0.736**

## What happens AFTER the +10m false alarm (descriptive, not a decision feature)
### true_dead
- N **9**, parent PnL sum **-28.953**, MFE/MAE median **0.246R / 1.139R**
- later close reclaim entry rate **77.8%**, median time **25.0m**
- later EMA7 reclaim rate **77.8%**, median **25.0m**
- later +0.5R hit rate **0.0%**, median **nanm**
- later +1R hit rate **0.0%**, median **nanm**

### false_winner
- N **13**, parent PnL sum **+49.572**, MFE/MAE median **1.495R / 0.487R**
- later close reclaim entry rate **100.0%**, median time **25.0m**
- later EMA7 reclaim rate **100.0%**, median **20.0m**
- later +0.5R hit rate **100.0%**, median **80.0m**
- later +1R hit rate **76.9%**, median **197.5m**

## Guardrail
The post-+10m section explains outcomes but cannot be used to justify a +10m live action. Any next candidate must use only the causal feature set above and must be predeclared without threshold/timing sweeps.
