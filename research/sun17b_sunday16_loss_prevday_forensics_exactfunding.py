#!/usr/bin/env python3
"""SUN1.7b wrapper: exact SUN1.6 funding parity for SUN1.7 forensics."""
import os
from pathlib import Path
import pandas as pd
import sun17_sunday16_loss_prevday_forensics as base


def exact_sun16_funding(k,f,entry_t,exit_t,entry_px):
    # SUN1.6 charges funding present at 5m bar opens up to the EXIT BAR OPEN,
    # not at the following 5m exit boundary. It also uses exact kline-open map only.
    exit_bar_t = exit_t - pd.Timedelta(minutes=5)
    rows=f[(f.ts>entry_t)&(f.ts<=exit_bar_t)]
    qty=base.NOTIONAL/entry_px; cost=0.0; n=0
    for r in rows.itertuples(index=False):
        if r.ts in k.index:
            px=float(k.loc[r.ts,'open'])
            cost += -qty*px*float(r.rate)
            n += 1
    return float(cost),int(n)

base.funding_short=exact_sun16_funding
base.OUT=Path(os.getenv('SUN17_OUT','sun17_out')); base.OUT.mkdir(parents=True,exist_ok=True)

if __name__=='__main__':
    base.main()
