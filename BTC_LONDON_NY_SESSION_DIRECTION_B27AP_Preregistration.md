# B27AP — BTC London->NY Session Direction Bias Audit — Preregistration

## Purpose
Test whether the London->New York time window itself has a persistent bullish directional bias, independently of any B27Q LONG/SHORT signal selection.

## Frozen universe
- BTCUSDT raw 5m archive used by B27Q/B27AK.
- UTC weekdays only.
- London source session: 08:00 inclusive to 13:30 exclusive.
- New York observation session: 13:30 inclusive to 20:00 exclusive.
- Include only dates with complete 5m bars for both windows.
- No signal, K1, OPP0, F15/F85, regime, EMA, swing, trade, PnL, stop, target, or confirmation filter.

## Frozen measurements per date
1. London H = max high in 08:00-13:30; London L = min low; R=H-L.
2. NY session return = final 19:55 close / 13:30 open - 1.
3. Direction label: UP if return>0, DOWN if return<0, FLAT if exactly 0.
4. High close-break = any completed NY 5m close strictly > H.
5. Low close-break = any completed NY 5m close strictly < L.
6. First strict boundary close-break: HIGH_FIRST, LOW_FIRST, SAME_BAR_BOTH if theoretically both conditions occur on the same completed bar, or NONE.
7. Max upside extension = max(0,(max NY high-H)/R).
8. Max downside extension = max(0,(L-min NY low)/R).

## Outputs
Report overall and calendar-year counts/rates for UP/DOWN, median and mean NY return, high/low close-break rates, first-break distribution, and median upside/downside extension.

## Interpretation
This audit answers only whether the time window itself is directionally biased. It must not be used to retrofit the SHORT detector. A modest plurality is not described as 'always bullish'.

Research only; live BBC unchanged.
