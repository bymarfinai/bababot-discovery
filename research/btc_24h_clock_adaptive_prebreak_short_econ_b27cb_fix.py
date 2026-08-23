#!/usr/bin/env python3
from __future__ import annotations

import pandas as pd

import btc_24h_clock_adaptive_prebreak_short_econ_b27cb as b27cb


def summarize_fixed(t: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for v, sm, tm in b27cb.VARIANTS:
        z = t[t.variant == v]
        for p in b27cb.MAJOR:
            rows.append({'scope': 'PARTITION', 'name': p, 'variant': v, 'stop_multiple': sm, 'target_multiple': tm, 'nominal_rr': tm/sm, **b27cb.metrics(z[z.partition == p])})
        rows.append({'scope': 'POOL', 'name': 'POOLED_OOS', 'variant': v, 'stop_multiple': sm, 'target_multiple': tm, 'nominal_rr': tm/sm, **b27cb.metrics(z[z.partition.isin(b27cb.OOS)])})
        rows.append({'scope': 'POOL', 'name': 'POOLED_MAJOR', 'variant': v, 'stop_multiple': sm, 'target_multiple': tm, 'nominal_rr': tm/sm, **b27cb.metrics(z[z.partition.isin(b27cb.MAJOR)])})
        for cb in b27cb.CLOCKS:
            rows.append({'scope': 'CLOCK_MAJOR', 'name': cb, 'variant': v, 'stop_multiple': sm, 'target_multiple': tm, 'nominal_rr': tm/sm, **b27cb.metrics(z[z.clock_block == cb])})
            rows.append({'scope': 'CLOCK_OOS', 'name': cb, 'variant': v, 'stop_multiple': sm, 'target_multiple': tm, 'nominal_rr': tm/sm, **b27cb.metrics(z[(z.clock_block == cb) & (z.partition.isin(b27cb.OOS))])})
    return pd.DataFrame(rows)


if __name__ == '__main__':
    b27cb.summarize = summarize_fixed
    b27cb.main()
