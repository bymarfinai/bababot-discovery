#!/usr/bin/env python3
from __future__ import annotations

import numpy as np
import pandas as pd

import btc_london_ny_4h_regime_alignment_b27ag as m


def fixed_load_struct_side(side: str):
    sig=pd.read_csv(m.SIGNALS)
    sig=sig[(sig.transition=='LONDON_TO_NEWYORK') & (sig.side==side) &
            (pd.to_numeric(sig.k)==1) & (pd.to_numeric(sig.opp_visits_at_signal)==0)].copy()
    sig=m.dt(sig,['signal_ts','signal_bar_start','active_session_end'])
    if side=='LONG':
        w=m.dt(pd.read_csv(m.LONG_W),['signal_ts','eligible_start','h2_bar_start','session_end'])
        e=pd.read_csv(m.LONG_E); e=e[e.entry_name=='F85'].copy()
        e=m.dt(e,['signal_ts','entry_ts','h2_bar_start','eligible_start'])
        e['filled_b']=m.as_bool(e.filled); e['h2_b']=m.as_bool(e.target_hit)
        e['entry_time_norm']=e.entry_ts
        e['entry_px_norm']=pd.to_numeric(e.entry_px,errors='coerce')
        frac=.85
    else:
        w=m.dt(pd.read_csv(m.SHORT_W),['signal_ts','eligible_start','h2_bar_start','session_end'])
        t=pd.read_csv(m.SHORT_T); e=t[t.rule=='BLIND_F15'].copy()
        e=m.dt(e,['signal_ts','blind_touch_bar_start','h2_bar_start','eligible_start'])
        e['filled_b']=m.as_bool(e.blind_filled); e['h2_b']=m.as_bool(e.h2_after_fill)
        e['entry_time_norm']=e.blind_touch_bar_start
        e['entry_px_norm']=pd.to_numeric(e.blind_entry_px,errors='coerce')
        frac=.15
    keys=['partition','signal_ts']
    for d in (sig,w,e):
        d.sort_values(keys,inplace=True); d.reset_index(drop=True,inplace=True)
    assert len(sig)==len(w)==len(e), (side,len(sig),len(w),len(e))
    assert sig[keys].equals(w[keys]) and sig[keys].equals(e[keys]), f'{side} identity mismatch'
    # Recompute expected geometry AFTER sort/reset so the audit uses the same row identity.
    expected=pd.to_numeric(e.L)+frac*(pd.to_numeric(e.H)-pd.to_numeric(e.L))
    f=e[e.filled_b]
    assert np.allclose(f.entry_px_norm.to_numpy(float),expected.loc[f.index].to_numpy(float),rtol=1e-12,atol=1e-9)
    return sig,w,e


m.load_struct_side=fixed_load_struct_side
m.main()
