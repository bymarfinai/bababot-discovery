# B27BN — BTC 24H Swing-Boundary Invalidation Audit — Result

**Audit status: PASS.** Regime-structure anatomy only; no LONG/SHORT mapping, entry, stop, target, fee, WR, PF, PnL, session filter, or live change was used.

B27BH parent identity reproduced exactly: **1,023 episodes = 527 RESUME + 496 TRANSITION; BULL-origin 532; BEAR-origin 491.**

Frozen boundary comes from the immediately preceding completed directional 4H state: latest confirmed swing low (`lsl`) for BULL, latest confirmed swing high (`lsh`) for BEAR.

## Pooled OOS — first SIDEWAYS bar

| Origin | Boundary known | Wick BREAK N | P(transition \| break) | HOLD N | P(transition \| hold) | Lift |
|---|---:|---:|---:|---:|---:|---:|
| BULL | 313/313 = 100.0% | 87 | 49.4% | 226 | 41.6% | +7.8pp |
| BEAR | 242/242 = 100.0% | 71 | 59.2% | 171 | 52.0% | +7.1pp |

## Pooled OOS — cumulative frozen-boundary wick break by outcome

| Origin | Outcome | Age1 / 4h | By age2 / 8h | By age3 / 12h |
|---|---|---:|---:|---:|
| BULL | RESUME | 25.0% | 32.4% | 33.0% |
| BULL | TRANSITION | 31.4% | 44.5% | 47.4% |
| BULL | TRANSITION - RESUME at age3 |  |  | +14.5pp |
| BEAR | RESUME | 26.1% | 26.1% | 27.0% |
| BEAR | TRANSITION | 32.1% | 40.5% | 42.0% |
| BEAR | TRANSITION - RESUME at age3 |  |  | +15.0pp |

## OOS stability — first-bar wick-break lift and age3 break-rate separation

| Partition | Origin | First-bar transition lift | Age3 TRANSITION-RESUME break rate |
|---|---|---:|---:|
| external | BULL | +5.1pp | +15.5pp |
| external | BEAR | +9.6pp | +21.2pp |
| reference_validation | BULL | +16.4pp | +18.8pp |
| reference_validation | BEAR | +4.3pp | +10.1pp |

## Close-break confirmation — pooled OOS

| Origin | First close-break N | P(transition \| close break) | P(transition \| close hold) | Lift | RESUME close-break by age3 | TRANSITION close-break by age3 |
|---|---:|---:|---:|---:|---:|---:|
| BULL | 62 | 51.6% | 41.8% | +9.8pp | 20.5% | 37.2% |
| BEAR | 46 | 56.5% | 53.6% | +3.0pp | 18.9% | 28.2% |

## Important diagnostic

- BULL: genuine TRANSITION episodes that reached the opposite detector state **without ever wick-breaking** the frozen origin boundary during SIDEWAYS: **49.6%**.
- BULL: RESUME episodes that **did wick-break** the frozen boundary before returning to the origin state: **35.2%**.
- BEAR: genuine TRANSITION episodes that reached the opposite detector state **without ever wick-breaking** the frozen origin boundary during SIDEWAYS: **56.5%**.
- BEAR: RESUME episodes that **did wick-break** the frozen boundary before returning to the origin state: **27.0%**.

## Frozen support gate

- Exact source/detector/episode/timing identity: **PASS**.
- Boundary available >=95% pooled OOS for both origins: **PASS**.
- First-bar wick break increases transition rate pooled OOS for both origins: **PASS**.
- First-bar wick-break lift positive in external and validation for both origins: **PASS**.
- Age3 transition-minus-resume wick-break rate >=10pp pooled OOS for both origins: **PASS**.
- Age3 separation positive in external and validation for both origins: **PASS**.
- First-bar BREAK and HOLD pooled-OOS N >=20 per origin: **PASS**.

**Frozen verdict: `B27BN_SWING_BOUNDARY_INVALIDATION_SUPPORTED`.**

## Interpretation boundary

A supported result would validate only the frozen prior swing boundary as a causal regime-invalidation signal. It does not redesign the production detector or authorize any trading behavior.

Research only. Live BBC unchanged.
