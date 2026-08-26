# B27DU — BTC F15 SHORT 20:00 UTC Walk-Forward / Portfolio / Execution-Stress Validation — Preregistration

**Status:** PREREGISTERED before result-bearing B27DU execution.

## Purpose
Test whether the already-discovered F15 SAME_BAR_REJECTION SHORT at reference clock 20:00 UTC remains historically stable across chronological eras, continues to add value when merged with the frozen B27DQ LONG portfolio, and survives conservative execution slippage.

B27DU is **not pristine unseen OOS**, because 20:00 UTC and the six-clock comparison basket were already observed in B27DR/B27DS/B27DT. It is a frozen-rule robustness test only.

## Frozen primary SHORT
Exact B27DR/B27DS structure, unchanged:
- reference start: **20:00 UTC**;
- reference duration: **5h30m**;
- execution: **01:30–08:00 UTC next day**;
- first Low K1 with opposite-side visits = 0;
- causal leave from first Low-touch episode;
- pre-H2 F15 touch;
- original F15-touch 5m bar must close below F15;
- enter SHORT at next 5m open if geometry remains valid and H2 has not already occurred;
- F15 = L + 0.15R;
- F65 = L + 0.65R completed-close invalidation;
- E20_DOWN = L - 0.20R fixed target;
- same fee/notional and time-exit semantics as B27DR/B27AD.

No price level, candle filter, regime filter, timeframe, confirmation, stop, target, duration, or clock may be tuned in B27DU.

## Frozen LONG control
Use exact B27DQ live-executable four-zone LONG research portfolio and reproduce pooled-major control approximately:
- accepted N = 227;
- WR = 72.2%;
- PF = 2.25;
- net = +$289.76;
- max loss streak = 3.

## Frozen six-SHORT comparison basket
Comparator only; no re-ranking:
- 20:00 UTC
- 04:30 UTC
- 03:30 UTC
- 03:00 UTC
- 21:00 UTC
- 00:00 UTC

Use exact B27DT one-BTC-position semantics.

## Chronological robustness windows
Use entry timestamp to assign accepted trades to these fixed blocks:
- W1: 2020-01-01 <= entry < 2021-07-01
- W2: 2021-07-01 <= entry < 2023-01-01
- W3: 2023-01-01 <= entry < 2024-07-01
- W4: 2024-07-01 <= entry < 2026-01-01
- W5_YTD: 2026-01-01 <= entry through dataset end

W1–W4 are the **completed-window gate set**. W5_YTD is reported but not used to pass/fail because it is incomplete.

Also report calendar-year SHORT20 N/WR/PF/net for anatomy only.

## Primary SHORT20 chronological gate
For each completed window W1–W4 define a window PASS when:
- N >= 8;
- WR >= 60%;
- PF >= 1.20;
- net > 0.

Chronological stability is SUPPORTED when:
- at least 3 of 4 completed windows PASS; and
- no completed window has PF < 0.80.

This gate is intentionally weaker than the pooled discovery numbers because block sample sizes are much smaller; it is a stability gate, not a new clock-selection gate.

## Portfolio test
Construct historical FIRST_SIGNAL_WINS portfolios using exact B27DT semantics:
1. LONG_ONLY = frozen accepted B27DQ LONG control.
2. LONG_PLUS_SHORT20 = raw B27DQ LONG candidates + frozen SHORT20 candidates, chronological one BTC position.
3. LONG_PLUS_SHORT6 = raw B27DQ LONG candidates + frozen six-clock SHORT basket, chronological one BTC position.

For every 18-month window report:
- LONG_ONLY N/WR/PF/net;
- SHORT accepted N/WR/PF/net;
- combined N/WR/PF/net;
- delta net versus LONG_ONLY;
- number of baseline LONG trades displaced.

Portfolio stability for LONG_PLUS_SHORT20 is SUPPORTED when:
- at least 3 of 4 completed windows have delta net > 0; and
- total pooled-major baseline LONG displacement = 0; and
- pooled-major combined net > LONG_ONLY net.

The six-clock basket is a comparator and cannot determine the primary B27DU pass/fail.

## Conservative SHORT execution stress
Reprice every frozen SHORT20 trade with symmetric adverse slippage on both fills:
- SHORT entry market sell: entry_px * (1 - bps/10000)
- exit market buy: exit_px * (1 + bps/10000)

Test per-fill slippage:
- 0 bps
- 2 bps
- 5 bps
- 10 bps

Keep the existing fixed $0.40 fee and $500 notional. Do not change trade eligibility or exit reason under slippage; this is a pure fill-price stress.

Execution robustness is SUPPORTED when at **5 bps per fill** pooled-major SHORT20 retains:
- WR >= 65%;
- PF >= 1.50;
- net > 0.

10 bps is diagnostic only.

## Final status
`B27DU_SHORT2000_HISTORICAL_ROBUSTNESS_SUPPORTED` only if:
- B27DQ parity PASS;
- B27DS/B27DR SHORT20 parity PASS;
- chronological SHORT20 stability SUPPORTED;
- LONG_PLUS_SHORT20 portfolio stability SUPPORTED;
- 5 bps execution robustness SUPPORTED.

Otherwise return a specific NOT_SUPPORTED status and preserve all outputs.

## Guardrails
- Research only; live BBC unchanged.
- No post-result clock pruning, filter addition, target/stop tuning, or arbitration tuning inside B27DU.
- Any rule modification requires a new experiment ID.
