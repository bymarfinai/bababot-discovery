# B21 Implementation Correction Note

The first B21 workflow run (`run_id=32478430958`) completed technically but its stage-propagation output is **scientifically invalid** and must not be interpreted as a rejection of the B21 hypothesis.

## What happened

The first implementation converted higher-timeframe transition timestamps with `DatetimeIndex.asi8` and compared them against `Timestamp.value`. On the GitHub Actions pandas build, those integer representations can use different datetime resolutions. The resulting search key and transition array were therefore not resolution-safe, causing every higher-timeframe lookup to return missing and every seed to be incorrectly classified as `S0_5M`.

Evidence of the implementation inconsistency was visible inside the same run: the latest-state table contained real 15m/1h/4h OFF→ON transitions, while the cascade table reported zero transitions at every higher stage.

## Correction

The corrected runner keeps timestamps as timezone-aware `DatetimeIndex` objects and uses `DatetimeIndex.searchsorted(Timestamp)` directly. No research definition changes:

- same data;
- same partitions;
- same frozen BULL definition;
- same 7-day propagation horizon;
- same seed definition;
- same outcome diagnostics;
- same gates.

Only the timestamp lookup implementation is corrected.

The corrected result supersedes the first run for B21 interpretation. The first generated files remain in Git history for traceability.
