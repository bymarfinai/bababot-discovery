#!/usr/bin/env python3
from pathlib import Path
import sys,pandas as pd
ROOT=Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
import btc_mtf_bull_cascade_b21 as b21
import btc_generic_f85_long_clock_scan_b27de as de
import btc_f85_long_range_completion_recency_b27dj as dj
import bbc_f85_f15_signals as sig

x5,_=b21.load5(); a=pd.Timestamp('2025-09-11T00:00:00Z'); cm=330
c=de.build_case(x5,a,cm)
print('DIAG_B27DE', {k:c.get(k) for k in ['case_status','entry_executed','entry_bar_start','touch_bar_start','H','L','F85','k1_signal_bar_start','leave_bar_start']})
rs=a+pd.Timedelta(minutes=cm); re=rs+sig.REF_DUR; ref=de.fast_slice(x5,rs,re)
ad=sig.LongF85Session('RAW_0530',a,ref)
print('DIAG_ADAPTER_RANGE', {'H':ad.H,'L':ad.L,'completion_elapsed':ad.range_completion_elapsed_min,'state':ad.state})
q=dj.load_candidates(); q=q[(q.zone=='RAW_0530') & (pd.to_datetime(q.entry_bar_start,utc=True)==pd.Timestamp('2025-09-11T12:30:00Z'))].copy()
print('DIAG_PERSISTED_CANDIDATE_N',len(q))
if len(q):
    z,_=dj.attach_range_completion(q,x5)
    print('DIAG_PERSISTED_FEATURE',z[['entry_bar_start','range_completion_elapsed_min','range_completed_second_half','primary_eligible']].to_dict('records'))
