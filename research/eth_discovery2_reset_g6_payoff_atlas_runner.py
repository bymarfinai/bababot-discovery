#!/usr/bin/env python3
"""Pre-run compatibility wrapper for G6.

No preregistered metric or calculation is changed. This only makes Development
block column names valid Python identifiers for pandas.itertuples rendering.
"""
from __future__ import annotations

import numpy as np
import eth_discovery2_reset_g6_payoff_atlas as g6


def safe_dev_blocks(TA):
    Q=TA[TA.partition=="development"].sort_values("entry_ts").reset_index(drop=True)
    rows=[]
    for bi,ix in enumerate(np.array_split(np.arange(len(Q)),4),1):
        B=Q.iloc[ix]
        row={"block":bi,"n":len(B),
             "median_fee_be_R":float(B.fee_be_R.median()),
             "median_full_mfe_R":float(B.full_mfe_R.median()),
             "median_full_mae_R":float(B.full_mae_R.median()),
             "fee_clear_rate":float(B.clears_fee_by_mfe.mean()),
             "terminal_net_positive_rate":float(B.terminal_net_positive.mean())}
        for T in g6.MAJOR_T:
            key=f"mfe_ge_{T:.2f}R".replace('.', '_')
            row[key]=float((B.full_mfe_R>=T).mean())
        rows.append(row)
    import pandas as pd
    return pd.DataFrame(rows)


g6.dev_blocks=safe_dev_blocks

g6.main()
