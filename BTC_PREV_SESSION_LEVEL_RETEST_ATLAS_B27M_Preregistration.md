# B27M — Previous-Session Level Retest Atlas Optimized Rerun

Execution-equivalent additive rerun of B27L. All research definitions are frozen exactly as B27L: same BTC 5m source, partitions, weekdays, session windows, transitions, 15m/1H session-anchored observation bars, ±0.10%/±0.20% zones, first strict close-through BULL/BEAR classification, NO_BREAK, distinct retests, raw touch bars, and exact High/Low retest combinations.

Only implementation difference: use index-position slicing instead of repeated full-dataframe boolean scans so the workflow completes efficiently. No trading rule is introduced.

Research only; live BBC unchanged.
