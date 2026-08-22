#!/usr/bin/env python3
from __future__ import annotations

import numpy as np
import pandas as pd

import btc_london_ny_short_breakdown_reclaim_b27ai as m

_orig = m.simulate_reclaim

def fixed_simulate_reclaim(x5, r):
    d = _orig(x5, r)
    rename = {
        'trough_px_in_trade':'b27ai_trough_px_in_trade',
        'trough_extension_r':'b27ai_trough_extension_r',
        'realized_exit_extension_r':'b27ai_realized_exit_extension_r',
        'capture_ratio':'b27ai_capture_ratio',
        'giveback_r':'b27ai_giveback_r',
    }
    return {rename.get(k,k):v for k,v in d.items()}


def fixed_summarize_new(g: pd.DataFrame) -> dict:
    e=g[g.entry_executed_b].copy()
    if not len(e):
        return {'trades':0,'wr':np.nan,'pf':np.nan,'exp':np.nan,'total':0.0,'accept_rate':np.nan,'e20_rate':np.nan,
                'preinvalid':0,'reclaim_exits':0,'time_exits':0,'med_trough_ext':np.nan,'med_exit_ext':np.nan,'med_capture':np.nan,'med_giveback':np.nan}
    p=e.b27ai_net_pnl_usd.astype(float); acc=e[e.breakdown_accepted.astype(bool)]
    return {'trades':len(e),'wr':float((p>0).mean()),'pf':m.pf(p),'exp':float(p.mean()),'total':float(p.sum()),
            'accept_rate':float(e.breakdown_accepted.mean()),'e20_rate':float(e.e20_diag_reached.mean()),
            'preinvalid':int((e.b27ai_exit_reason=='PRE_ACCEPT_CLOSE_INVALIDATION_F65').sum()),
            'reclaim_exits':int((e.b27ai_exit_reason=='BREAKDOWN_RECLAIM_L').sum()),
            'time_exits':int((e.b27ai_exit_reason=='TIME_EXIT_SESSION_END').sum()),
            'med_trough_ext':float(acc.b27ai_trough_extension_r.median()) if len(acc) else np.nan,
            'med_exit_ext':float(acc.b27ai_realized_exit_extension_r.median()) if len(acc) else np.nan,
            'med_capture':float(acc.b27ai_capture_ratio.median()) if len(acc) else np.nan,
            'med_giveback':float(acc.b27ai_giveback_r.median()) if len(acc) else np.nan}

m.simulate_reclaim = fixed_simulate_reclaim
m.summarize_new = fixed_summarize_new
m.main()
