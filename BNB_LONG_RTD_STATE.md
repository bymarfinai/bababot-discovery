# BNB LONG — Ready-to-Trade Promotion State

## Status
**DISCOVERY FROZEN / OOS VALIDATION**

- Scope: **BNBUSDT LONG only**
- Discovery unit: **1-hour WIB habitat**
- Primary candidate: **B28M — 12:00–13:00 WIB**
- Backup candidate: **B28I — 08:00–09:00 WIB**
- Discovery frozen through: **B28P — 15:00–16:00 WIB**
- Blocked resume point: **B28Q — 16:00–17:00 WIB**
- SHORT discovery: **not started in this validation track**

## Decision
Per-hour discovery remains the unit of analysis. However, new-hour scanning is stopped while a structurally qualified LONG candidate is being validated.

Historical B28 branches remain frozen evidence. No prior result is deleted or rewritten.

## Primary candidate — B28M
Frozen structural character:

### `RV_MID__RANGE_HIGH / LB30 / hold360m`
- Habitat: **12:00–13:00 WIB**
- N: **201**
- WR: **63.68%**
- Net: **+$412.35**
- Expectancy: **+$2.05/trade**
- PF: **2.108**
- Max DD: **$41.59**
- Max loss streak: **5**
- Supportive quarter-hour anchors: **4/4**
- Development structural gate: **PASS**

Cross-era Development:
- 2022: N 55, WR 63.64%, expectancy +$2.07, PF 2.040
- 2023: N 67, WR 64.18%, expectancy +$1.70, PF 2.149
- 2024: N 79, WR 63.29%, expectancy +$2.34, PF 2.128

The B28M definition above is frozen before OOS. It must not be modified in response to OOS results.

## Stage state
1. **Character Discovery — PASS** (`B28M`)
2. **OOS Validation — CURRENT**
3. **Trade Construction — LOCKED pending OOS PASS**
4. **Execution Validation — LOCKED**
5. **Ready-to-Trade — NOT YET**

## OOS rules
- LONG only.
- Keep the habitat exactly **12:00–13:00 WIB**.
- Keep `RV_MID__RANGE_HIGH / LB30 / hold360m` frozen.
- Do not widen, combine, or shift hours during OOS.
- Do not optimize parameters on OOS.
- Do not relax existing gates after seeing OOS.
- Record the exact unseen interval/data source before evaluating results.
- Any debugging/data repair must preserve the preregistered character and must not become a new parameter search.

## Promotion / rejection rule
- **B28M OOS PASS →** advance to Trade Construction using the same frozen character.
- **B28M fundamental OOS REJECT →** promote **B28I** as the next validation candidate.
- **B28M + B28I fundamental REJECT →** reopen per-hour LONG discovery at **B28Q (16:00–17:00 WIB)**.
- A tooling/data failure is not a fundamental candidate rejection and is not permission to spawn new time-window variants.

## Blocked action
**B28Q must not be started while B28M or B28I remains an active validation candidate.**

The objective is no longer to map every BNB hour. The objective is to turn the first robust per-hour LONG character into an executable, validated strategy.
