# SOL Options Wall Forward Validation V1 — Current Result

**Status: FORWARD_SAMPLE_CENSORED**

- First eligible map: 2026-09-22T02:29:31.999Z
- Latest evaluated minute: 2026-09-22T03:51Z
- Prospective snapshots captured: 2
- Distinct map regimes: 1
- Primary lower wall: 116
- Primary upper wall: 120
- Observed SOLUSDT spot range after first map: 116.30–118.09
- Level touches across top-three lower/upper walls: 0
- Frozen horizon: 240 minutes

The second snapshot retained the same expiry tuple and the exact same top-three wall ranks, so it remains part of the same map regime rather than creating a new independent observation.

No wall-reaction outcome exists yet because no recorded concentration strike has been touched after the map was known.

The sample is censored because the 240-minute horizon has not completed. Censored is not counted as failure.

Historical SOL detector trades in the frozen 279-trade universe end on 2026-09-19, before the first options map, so none may be attributed to this options layer.
