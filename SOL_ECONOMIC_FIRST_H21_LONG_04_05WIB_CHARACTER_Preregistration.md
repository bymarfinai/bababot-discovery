# SOL Economic-First H21 — One-Hour LONG Character Discovery

## Question
Within **21:00–22:00 UTC / 04:00–05:00 WIB** only, what causal pre-entry character produces robust high-WR positive SOL LONG economics?

## Independence
H21 is independent of H00–H20. No candidate, rule, parameter, gate, ranking privilege, or verdict is inherited from any prior hour.

## Frozen engine
Use the frozen SOL economic-first H00 engine without changing methodology:
- LONG only
- raw SOLUSDT Binance Futures 5m weekdays
- exact 5m-open entry and exact 5m-open fixed-hold exit
- fixed notional $500
- round-trip fee $0.75
- lookbacks: 15, 30, 60, 120, 240, 360 minutes
- holds: 60, 120, 240, 360, 720, 960 minutes
- 90 frozen causal character rules
- rolling causal normalization with `ROLL_N=60`, `MIN_HIST=40`
- Development years 2022–2024 only
- OOS / External / Reference Validation remain closed
- no TP, SL, Fibonacci, reference range, visit, breakout, retest, or EMA logic

## Frozen H21 anchors
- **21:00 UTC / 04:00 WIB**
- **21:15 UTC / 04:15 WIB**
- **21:30 UTC / 04:30 WIB**
- **21:45 UTC / 04:45 WIB**

Adapter clocks: `(1260, 1275, 1290, 1305)`.

## Frozen gates
Anchor gate: anchor evaluable at N>=40; supportive if WR>=52%, positive net/expectancy, PF>=1.05, DD<=$125, loss streak<=10. Candidate requires at least 3/4 evaluable anchors and 3/4 supportive anchors.

Pooled gate: N>=160, WR>=55%, positive net, expectancy>=+$0.50, PF>=1.20, DD<=$125, loss streak<=8.

Era gate: every Development year N>=40, WR>=52%, positive net/expectancy, PF>=1.05; at least two years must have WR>=55%.

No gate relaxation, rounding rescue, OOS leakage, or candidate inheritance.

## Candidate universe and ranking
90 rules × 6 lookbacks × 6 holds = **3,240 candidates**. Rank full passers exactly as in the frozen H00 engine. If no candidate passes all frozen gates, status is `SOL_ECONOMIC_FIRST_H21_NO_LONG_CHARACTER`.

If at least one candidate passes all gates, status is `SOL_ECONOMIC_FIRST_H21_LONG_CHARACTER_FOUND`, with exactly the top full passer selected under the frozen ranking rule.

Research/shadow only.
