#!/usr/bin/env python3
"""Fast exact-equivalent runner for frozen SR81.

Scientific definition is unchanged. Optimizations only:
1) latest-completed-1H ATR is found by index search instead of full filtering;
2) ATR is looked up only after a 5m candle actually contains the level.
The original code's outcome, approach, episode-skip, thresholds and gates are unchanged.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import btc_friday_sr81_prior_proof_level as sr81


def fast_touch_atr(h: pd.DataFrame, t: pd.Timestamp):
    cutoff = t - pd.Timedelta(hours=1)
    pos = h.index.searchsorted(cutoff, side="right") - 1
    if pos < 0:
        return np.nan
    return float(h.iloc[int(pos)].atr14)


def fast_prior_proof(k: pd.DataFrame, h: pd.DataFrame, fs: pd.Timestamp, level: float, side: str):
    hist = k[(k.index >= fs-sr81.LOOKBACK) & (k.index < fs)]
    if hist.empty:
        return {'resolved':0,'hold':0,'break':0,'ambiguous':0,'unresolved':0,'events':[]}
    idx=list(hist.index);i=1;events=[]
    while i<len(idx):
        t=idx[i];prev_t=idx[i-1];b=hist.loc[t]
        # Exact logical short-circuit: ATR cannot matter if this bar never touches the level.
        if not (float(b.low) <= level <= float(b.high)):
            i+=1;continue
        atr=fast_touch_atr(h,t)
        if not np.isfinite(atr) or atr<=0:
            i+=1;continue
        prev=hist.loc[prev_t]
        if side=='SUPPORT':
            eligible=float(prev.close)>level+sr81.APPROACH_ATR*atr
        else:
            eligible=float(prev.close)<level-sr81.APPROACH_ATR*atr
        if not eligible:
            i+=1;continue
        r=sr81.sr.resolve(k,t,level,side,atr)
        events.append({'touch':str(t),'atr':atr,'outcome':r['outcome']})
        resume=t+sr81.EPISODE
        while i<len(idx) and idx[i]<resume:
            i+=1
    outcomes=[e['outcome'] for e in events]
    return {
      'resolved':sum(o in {'HOLD','BREAK'} for o in outcomes),
      'hold':sum(o=='HOLD' for o in outcomes),'break':sum(o=='BREAK' for o in outcomes),
      'ambiguous':sum(str(o).startswith('AMBIGUOUS') for o in outcomes),
      'unresolved':sum(o=='UNRESOLVED' for o in outcomes),'events':events}


sr81.touch_atr = fast_touch_atr
sr81.prior_proof = fast_prior_proof

if __name__ == "__main__":
    sr81.main()
