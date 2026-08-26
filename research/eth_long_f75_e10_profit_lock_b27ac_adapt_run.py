#!/usr/bin/env python3
from __future__ import annotations

import pandas as pd
import eth_long_f75_e10_profit_lock_b27ac_adapt as m


def corrected_synthetic_tests():
    idx=pd.date_range('2026-01-05 14:00',periods=7,freq='5min',tz='UTC')
    x=pd.DataFrame([
        {'open':97.5,'high':99,'low':97,'close':98.0},
        {'open':98,'high':101.2,'low':97.8,'close':100.5},
        {'open':100.5,'high':102,'low':100.2,'close':101.5},
        {'open':101.5,'high':103,'low':101.2,'close':102.4},
        {'open':102.4,'high':103,'low':101.8,'close':102.0},
        {'open':102.0,'high':102.2,'low':100.8,'close':101.0},
        {'open':101.0,'high':101.1,'low':100.9,'close':101.0},
    ],index=idx)
    class R: pass
    r=R(); r.entry_ts=idx[0]; r.session_end=idx[-1]+m.BAR5; r.entry_px=97.5; r.H=100.; r.L=90.; r.range=10.
    z=m.hybrid_exit(x,r)
    # E10=101 is reached on idx[1]. The floor becomes effective only on idx[2].
    # idx[2] opens below 101, so the frozen rule requires an actual-open gap exit at 100.5.
    assert z['e10_reached']
    assert z['hybrid_exit_reason']=='ACTIVE_FLOOR_GAP_OPEN'
    assert abs(z['hybrid_exit_px']-100.5)<1e-12
    assert z['hybrid_exit_ts']==idx[2]


if __name__=='__main__':
    m.synthetic_tests=corrected_synthetic_tests
    m.main()
