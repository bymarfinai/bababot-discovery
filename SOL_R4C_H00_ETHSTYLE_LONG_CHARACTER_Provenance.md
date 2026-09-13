# SOL R4c H00 ETH-Style — Provenance

- Parent R4b checkpoint: `128747de04df3c7f69a259a3980ab800c0708d47`.
- Branch: `sol-r4c-hourly-character-scan`.
- Hour only: H00 = 00:00–01:00 WIB.
- Direction: LONG.
- Search grammar: 90 character rules × 6 lookbacks × 6 holds = 3,240 candidates.
- Lookbacks/holds and economic gates are inherited from the existing SOL economic-first character engine, which mirrors the ETH E12A/E12B one-hour method.
- 2022/2023/2024 are treated as development-era consistency checks in this runner.
- No gate relaxation after observing H00.
- The earlier fixed-H120 H00 diagnostic is retained separately and is not used to select this grid winner.
