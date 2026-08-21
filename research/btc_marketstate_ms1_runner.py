#!/usr/bin/env python3
import numpy as np
import pandas as pd
import btc_marketstate_ms1 as ms1
import ms1_funding_source as fs

def load_funding():
    f=pd.concat([fs.load_archived_funding(),fs.load_recent_funding()],ignore_index=True)
    f=f.dropna().drop_duplicates('ts').sort_values('ts').reset_index(drop=True)
    f['funding_mean30']=f.funding_rate.rolling(30,min_periods=10).mean()
    f['funding_sd30']=f.funding_rate.rolling(30,min_periods=10).std()
    f['funding_z_30']=(f.funding_rate-f.funding_mean30)/f.funding_sd30.replace(0,np.nan)
    if f.ts.max()<pd.Timestamp('2026-08-19',tz='UTC'):
        raise RuntimeError(f'funding coverage ends {f.ts.max()}')
    return f

if __name__=='__main__':
    ms1.load_funding=load_funding
    ms1.main()
