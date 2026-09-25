# BNB B43-S1 — Historical Options Access Audit

## Status

**B43 exact historical askIV replay is not available from the tested official Binance paths.**

## Evidence

### Product history
Binance officially announced additional BNBUSDT Daily Options starting 2023-08-30.

### Expired-symbol kline access
Direct Options Kline probes were attempted for:
- inferred 2023 expired BNB daily-option symbols;
- known BNB symbols that had expired only one day before the probe.

The API returned:
`The symbol is either in PENDING_TRADING status or does not exist.`

Therefore expired-contract kline replay is not available through the tested endpoint.

### Historical exercise records
Historical-exercise probes for BNB/BNBUSDT across tested 2023 and 2024 windows returned no usable records for reconstructing the chain.

### Active-contract backward kline access
The current active contract endpoint does return backward klines, but only since each current symbol was listed.

Probe at 2026-09-25 around 02:16 UTC:

| Symbol | Interval | Rows | First open ms | Last open ms | Note |
|---|---|---:|---:|---:|---|
| BNB-261030-780-C | 1h | 16 | 1790247600000 | 1790301600000 | very short live history |
| BNB-261030-780-P | 1h | 16 | 1790247600000 | 1790301600000 | very short live history |
| BNB-261002-780-C | 1h | 187 | 1789632000000 | 1790301600000 | about one week |
| BNB-261002-780-P | 1h | 145 | 1789783200000 | 1790301600000 | shorter than call |

These are traded option-price klines, not historical askIV/markIV snapshots.

## Consequence

A historical exact reproduction of the video's `Ask IV`-style levels cannot be claimed from these klines.

Two legitimate paths remain:

1. **Prospective exact path**
   - snapshot live askIV/markIV/Greeks + index;
   - freeze level map;
   - evaluate future HOD/LOD after the snapshot.

2. **Approximate reconstruction path**
   - use active-option traded-price klines;
   - invert a model-implied volatility using causal underlying price, strike and time-to-expiry;
   - label explicitly as reconstructed trade-price IV, not Binance askIV;
   - treat as exploratory only until independently validated.

B43-S1 chooses the prospective exact path as canonical. Approximate inversion may be a separate auxiliary experiment but cannot substitute for exact askIV history.
