# BTC Temporal A4 — Post-Entry Rescue Checkpoint

**Date:** 2026-08-16  
**Status:** A4/A4.2 DISCOVERY COMPLETE — causal rescue signal found; promising but not production-ready  
**Symbol:** BTCUSDT  
**Timezone:** WIB / UTC+7  
**Evaluation:** 971 days, 2023-12-02 to 2026-07-30 exclusive  
**5m data:** 279,648 / 279,648 = 100% coverage  
**Tuesday occurrences:** 139

## Parent trade

Every Tuesday at exactly **06:00 WIB**:
- direction: **SELL**
- TP: **0.5%**
- SL: **0.5%**
- max hold: **4h**
- margin reference: **$10**
- leverage reference: **50x**
- notional: **$500**
- assumed round-trip fee per position: **0.15%**
- same-5m TP+SL ambiguity treated conservatively as **SL first**

Baseline first-touch:
- TP first: **84**
- SL first: **45**
- no-touch: **10**
- resolved first-touch WR: **65.12%**

Baseline actual-money model, including 4h timeout close and fee:
- 139 trades
- net-positive trades: **86**
- net-negative trades: **53**
- net-positive trade rate: **61.87%**
- cumulative net PnL: **-$7.90**

## Research question

Can the 0.5/0.5 losing paths be recognized *after entry* early enough to rescue them, without filtering out Tuesday trades?

Architecture:

`06:00 SELL -> observe completed 5m path -> HOLD / CUT / FLIP BUY`

The entry remains on every Tuesday. Rescue is trade management, not a pre-entry filter.

---

## A4 oracle rescue capacity

The loss-rescue idea is mechanically feasible. Of the 45 baseline SL trades:

| Checkpoint | SL still open | Oracle flip becomes total-positive |
|---|---:|---:|
| 5m | 44 | **34** |
| 10m | 41 | 26 |
| 15m | 38 | 26 |
| 20m | 34 | 23 |
| 30m | 31 | 18 |
| 45m | 26 | 19 |
| 60m | 21 | 15 |

Thus the bottleneck is **identification**, not lack of time to react.

A generic walk-forward KNN using all-calendar-day 06:00 path analogues did not identify losers well enough. It produced little improvement and discovery-selected configurations generally failed validation. The generic analogue model is not the recommended rescue mechanism.

---

## A4.1 winner-vs-loser path atlas

The first completed 5m bar already contains useful separation.

Among Tuesday trades still open after 5m:

### Eventual SELL TP median path
- return vs entry: **-0.0381%** (favorable to short)
- short MFE: **0.0975%**
- short MAE: **0.0526%**
- close-position in 5m range: **0.5000**
- taker edge (`taker buy ratio - 0.5`): **-0.0391**

### Eventual SELL SL median path
- return vs entry: **+0.0330%** (adverse to short)
- short MFE: **0.0673%**
- short MAE: **0.0961%**
- close-position in 5m range: **0.7143**
- taker edge: **+0.0189**

The most useful simple discriminator was adverse price progress very early:
- first-5m return +0.10% to +0.20%: **11/14 = 78.57%** eventual SELL SL
- +0.20% to +0.30%: **2/2 = 100%** eventual SELL SL

This relationship remained visible in the last-40% validation segment:
- +0.10% to +0.20%: **3/4 = 75%** eventual SL
- +0.20% to +0.30%: **1/1 = 100%** eventual SL

Losers also tend to show less favorable excursion before going adverse and more buyer-side taker aggression.

---

# A4.2 local refinement

Chronological split:
- discovery: first **83 Tuesdays** (~60%)
- validation: last **56 Tuesdays** (~40%)

Only a local interpretable grid around the discovered 5m state was tested:
- adverse move thresholds: 0.08–0.20%
- short MFE ceilings: 0.05–0.15%
- optional buyer-taker confirmation
- optional close-location confirmation
- CUT vs FLIP

No broader feature zoo was added.

## Best cross-period balanced rescue rule

At **06:05 WIB**, after the first completed 5m candle, while the original SELL is still open:

1. price is at least **+0.12% adverse** versus the 06:00 SELL entry;
2. short MFE during those 5 minutes is **<0.15%**;
3. average taker-buy ratio over the first 5m is **>50%** (buyer dominance);
4. then close the SELL and **FLIP BUY**;
5. BUY uses TP/SL **0.5%/0.5%** for the remaining original 4h horizon.

The evaluator charges the original short round-trip fee plus a second round-trip fee for the flipped BUY.

### Full 971-day result
- Tuesday trades retained: **139/139**
- rescue flips: **16**
- original SELL SL converted to total-positive: **7**
- original SELL TP damaged into negative: **2**
- other originally-negative trades improved: **12 total improved-negative cases**
- net-positive trades: **91 / 139 = 65.47%**
- baseline net-positive rate: 86 / 139 = **61.87%**
- improvement: **+5 net winning trades / +3.60 percentage points**
- baseline cumulative net PnL: **-$7.90**
- rescue cumulative net PnL: **+$11.50**
- improvement vs baseline: **+$19.40**
- profit factor: **1.086**
- max drawdown: **$23.43**
- max loss streak: **5**
- positive chronological blocks: **4/8**

### Discovery 83 Tuesdays
- flips: **11**
- SELL SL -> positive: **5**
- SELL TP damaged: **1**
- delta vs baseline: **+$18.84**

### Validation 56 Tuesdays
- flips: **5**
- SELL SL -> positive: **2**
- SELL TP damaged: **1**
- validation net-positive rate: **41/56 = 73.21%**
- validation cumulative PnL: **+$24.35** vs baseline **+$23.79**
- delta vs baseline: **+$0.56**
- profit factor: **1.58**

The rule improves both discovery and validation, but the validation PnL lift is small. It is a genuine promising signal, not yet a strong production proof.

## Conservative zero-validation-damage variant

At 06:05:
1. adverse move >= **+0.15%**;
2. short MFE < **0.15%**;
3. average taker-buy ratio > **50%**;
4. flip BUY 0.5/0.5.

Full 139:
- flips: **11**
- SL -> positive: **4**
- TP damaged: **1**
- net-positive trades: **89/139 = 64.03%**
- cumulative net PnL: **+$5.53**
- delta vs baseline: **+$13.43**

Validation 56:
- flips: **2**
- SL -> positive: **1**
- TP damaged: **0**
- net-positive rate: **73.21%**
- cumulative net PnL: **+$25.48** vs baseline +$23.79
- delta: **+$1.69**
- PF: **1.603**

This is the cleaner rule if minimizing collateral damage is prioritized over full-history conversion count.

---

# Verdict

**Yes: some of the 0.5/0.5 losses are learnable after entry.**

The strongest repeated path signature is not a complex ML pattern. It is an early failure of the SELL thesis:

`first 5m moves materially adverse + little/no favorable excursion + buyers dominate taker flow`

That condition can be used to flip a subset of likely SELL losers to BUY while keeping all 139 Tuesday entries.

However, the full-sample net-positive rate reaches only **65.47%**, not 70%+. The later validation segment happens to show **73.21%**, but that should not be generalized to the whole history.

Therefore:
- rescue hypothesis: **PROMISING / PARTIALLY CONFIRMED**
- 70%+ full-history effective WR: **NOT ACHIEVED**
- generic KNN rescue: **not recommended**
- interpretable 5m adverse-path rescue: **recommended for further frozen robustness testing**
- live deployment: **not yet**

## Next recommended validation

Freeze the 0.12/0.15/taker>50% rule and test it without retuning across rolling/leave-one-block-out periods and, separately, test whether the rescue BUY exit geometry should remain 0.5/0.5 or use a better frozen payoff. Do not continue arbitrary threshold mining.
