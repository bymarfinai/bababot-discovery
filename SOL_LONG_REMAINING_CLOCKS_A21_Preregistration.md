# SOL LONG Remaining Untouched Clocks — A21 Preregistration

## Objective
Continue Stage 12 after A20 by testing the next remaining untouched H2-dominant clock habitats from the pre-existing A1 Development anatomy atlas.

## Frozen supported habitats
- R240 / 18:00 UTC: A2 parent + A4 REC_H2.
- R420 / 03:00 UTC: A17 parent only.
- R360 / 15:00 UTC: A20 parent only.

No recovery is inherited by 03:00 or 15:00.

## Candidate derivation
Use only old A1 atlas cells with:
- dominant visit H2,
- topology_supported=true,
- same_dom_blocks >=4/6,
- dominant_opportunity_n >=100.

Exclude:
- any clock within circular distance <=2h of supported clocks 03, 15, or 18,
- every exact hour already economically tested: 03, 08, 12, 13, 15, 18.

Rank by the same frozen A17/A20 anatomy ordering and select at most four clocks, each >2h from the other selected clocks. Supports are frozen from A1 topology fields.

No A21 PnL is used to select candidates.

## Gates
Development and OOS gates are identical to A20:
- Development N>=300, PF>1.15, 5bps PF>1, positive expectancy/net raw+stress, >=4 adequate blocks, >=4 positive raw and >=4 positive stress blocks.
- Freeze one winner by 5bps net, 5bps PF, raw net, N, anatomy rank.
- OOS exact candidate must be positive with PF>1 raw+stress in External and Reference Validation.
- Supports require >=3/4 positive raw and >=3/4 positive stress.

If no untouched candidate remains under this grammar, report exhaustion rather than broaden the hypothesis after seeing data.

Research only. Live Baba Bot remains unchanged.
