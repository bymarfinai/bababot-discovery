# SOL Derivatives-State Rising Edge V5 — Preregistration

## Hypothesis
V4 showed that frozen derivatives states overlap a large share of true SOL long legs early, but are loss-making because the same broad state stays active and generates repeated/redundant entry opportunities.

V5 changes ONLY event semantics:
- A signal exists only on the first completed 15m bar where a frozen V4 state changes from OFF to ON.
- No extra threshold, score, cooldown, optimizer, or model is introduced.
- While a state remains ON, it cannot signal again.
- It may signal again only after first turning OFF and later returning ON.

## Frozen states
Exactly the six V4 states, unchanged:
NEW_LONG_BUILD
FRESH_LONG_BUILD
SHORT_SQUEEZE
LOW_FUNDING_SQUEEZE
ABSORPTION_RELEASE
DELEVERAGING_REVERSAL

## Execution
Unchanged from V4:
- next 15m open
- one active position
- 0.15% RT cost
- USD500 notional
- L2 TP2/SL1 max 24h
- L3 TP3/SL1 max 48h
- L5 TP5/SL1 max 72h
- same-5m TP+SL = loss

## Evaluation
Separate 2023, 2024, 2025, 2026.
Report trades/week, WR, net expectancy/trade, mean/median weekly return, leg hit, early hit.

## Gate
Promising only if:
- expectancy >0 in 2024, 2025, and 2026;
- weighted 2025+2026 expectancy >0;
- >=1 executed trade/week in both 2024 and 2025;
- no threshold rescue.
