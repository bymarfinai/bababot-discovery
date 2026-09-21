# SOL Execution Cost Audit V1 — Result

## Execution mapping

- Score-3 FIVE_MIN_REVERSAL_BREAK research entry is next-5m-open after a completed reversal-break bar; conservative live mapping is market/taker.
- RECLAIM_EXTREME protective exits map naturally to STOP_MARKET/taker.
- Structural/time completion exits map conservatively to market/taker once the completed-bar state is known.
- Therefore the primary execution reference is taker + taker.

## Funding

- Historical Binance funding records represented by snapshot: **6,623**.
- Trades crossing >=1 funding timestamp: **112/279 (40.14%)**.
- Total funding impact: **-0.284R**.
- Mean funding impact per trade: **-0.0010R**.
- Gross mean/PF before funding: **0.171R / 1.470**.
- After historical funding, before trading friction: **0.170R / 1.466**.

## Current SOLUSDT order-book snapshot

- Snapshot UTC: **2026-09-21 10:36:42.975000+00:00**
- Bid / ask: **115.5700 / 115.5800**
- Full spread: **0.865 bps**
- Top bid notional: **125,848 USD**
- Top ask notional: **34,124 USD**
- $500 market-buy depth slippage beyond best ask: **0.000 bps**
- $500 market-sell depth slippage beyond best bid: **0.000 bps**

This snapshot demonstrates current visible depth only; it is not a historical slippage guarantee.

## Cost budget including historical funding

- PF 1.10 round-trip cost ceiling: **19.68 bps**.
- Mean-R break-even round-trip cost ceiling: **26.14 bps**.
- Reference taker+taker fee: **10.00 bps** before account-specific discounts.
- Reference fee + current full spread: **10.865 bps**.
- Extra slippage/latency budget after fee+spread before PF<1.10: **8.815 bps round trip**.
- Extra slippage/latency budget after fee+spread before mean R<=0: **15.275 bps round trip**.

## Existing BabaBot generic cost assumption

- Existing config fee assumption: **10.0 bps round trip**.
- Existing config slippage assumption: **5.0 bps**.
- Existing combined assumption: **15.0 bps**.
- At 15 bps + historical funding: mean **0.072R**, PF **1.178**, cumulative **20.184R**.
- Remaining headroom from 15 bps to PF 1.10 ceiling: **4.68 bps**.

## Scenario table

| Round-trip friction | Mean net R | PF | Cum R | Max DD | WR |
|---:|---:|---:|---:|---:|---:|
| 0.0 bps | 0.170 | 1.466 | 47.366 | 5.868 | 59.14% |
| 10.0 bps | 0.105 | 1.267 | 29.244 | 6.812 | 58.42% |
| 12.0 bps | 0.092 | 1.231 | 25.620 | 7.001 | 58.06% |
| 15.0 bps | 0.072 | 1.178 | 20.184 | 7.516 | 57.71% |
| 18.0 bps | 0.053 | 1.127 | 14.747 | 8.292 | 57.71% |
| 19.0 bps | 0.046 | 1.111 | 12.935 | 8.551 | 57.71% |
| 19.5 bps | 0.043 | 1.103 | 12.029 | 8.680 | 57.35% |
| 20.0 bps | 0.040 | 1.095 | 11.123 | 8.810 | 57.35% |
| 25.0 bps | 0.007 | 1.017 | 2.063 | 10.103 | 56.63% |
| 30.0 bps | -0.025 | 0.944 | -6.998 | 15.039 | 56.27% |

## Verdict

**EXECUTION_COST_NOT_PRIMARY_BLOCKER_AT_EXISTING_15BPS_ASSUMPTION**

The filtered SOL universe remains above PF 1.10 at the repository's existing 15 bps total-cost assumption even after historical funding is applied.

The remaining deployment gap is not another detector search. It is live execution instrumentation: record actual account commission, maker/taker status, signal-to-fill slippage, latency, and funding on every SOL trade. Only those realized fills can confirm the production cost distribution.
