#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b

ROOT = Path(__file__).resolve().parent.parent
IN_TRADES = ROOT / 'BTC_PREVIOUS_BAR_BREAKOUT_B27A_Trades.csv'
OUT_MD = ROOT / 'BTC_4H_BREAKOUT_VALIDATION_FORENSICS_B27B_Result.md'
OUT_CSV = ROOT / 'BTC_4H_BREAKOUT_VALIDATION_FORENSICS_B27B_Tables.csv'


def pf(v: pd.Series):
    s = pd.to_numeric(v, errors='coerce').dropna().astype(float)
    pos = float(s[s > 0].sum()); neg = float(-s[s < 0].sum())
    if neg == 0 and pos > 0: return float('inf')
    return pos / neg if neg > 0 else np.nan


def summarize(g: pd.DataFrame):
    if len(g) == 0:
        return {'n':0,'wins':0,'losses':0,'wr':np.nan,'net_pf':np.nan,'net_exp':np.nan,'total_net':np.nan,'med_risk':np.nan}
    net = g.net_pnl_usd.astype(float)
    wins = int((g.exit_reason == 'TP').sum())
    return {
        'n': int(len(g)),
        'wins': wins,
        'losses': int(len(g)-wins),
        'wr': float(wins/len(g)),
        'net_pf': float(pf(net)),
        'net_exp': float(net.mean()),
        'total_net': float(net.sum()),
        'med_risk': float(g.risk_pct.median()),
    }


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.2f}%'
def num(v,d=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{d}f}'


def add_feature_rows(t: pd.DataFrame, z4: pd.DataFrame, x5: pd.DataFrame):
    rows=[]
    xidx=x5.index; xhi=x5.high.to_numpy(float); xlo=x5.low.to_numpy(float)
    for r in t.itertuples(index=False):
        ts=pd.Timestamp(r.signal_ts)
        if ts not in z4.index:
            continue
        i=z4.index.get_loc(ts)
        if isinstance(i, slice) or i < 1: continue
        sig=z4.iloc[i]; prev=z4.iloc[i-1]
        prev_range=float(prev.high-prev.low)
        body_ratio=abs(float(sig.close-sig.open))/float(sig.high-sig.low) if float(sig.high-sig.low)>0 else 0.0
        if r.side=='LONG':
            extension=(float(sig.close)-float(prev.high))/prev_range if prev_range>0 else np.nan
        else:
            extension=(float(prev.low)-float(sig.close))/prev_range if prev_range>0 else np.nan
        entry_ts=pd.Timestamp(r.entry_ts); exit_ts=pd.Timestamp(r.exit_ts)
        a=int(xidx.searchsorted(entry_ts,side='left')); b=int(xidx.searchsorted(exit_ts,side='right'))
        risk_px=abs(float(r.entry_px)-float(r.stop_px))
        mfe_r=np.nan
        if risk_px>0 and b>a:
            if r.side=='LONG':
                mfe_px=float(np.max(xhi[a:b]))-float(r.entry_px)
            else:
                mfe_px=float(r.entry_px)-float(np.min(xlo[a:b]))
            mfe_r=mfe_px/risk_px
        rows.append({**r._asdict(),
                     'signal_body_ratio':body_ratio,
                     'breakout_extension_prev_range':extension,
                     'signal_range_pct':float((sig.high-sig.low)/sig.close) if float(sig.close)!=0 else np.nan,
                     'year':ts.year,
                     'quarter':f'{ts.year}-Q{ts.quarter}',
                     'mfe_r':mfe_r})
    return pd.DataFrame(rows)


def table_rows(df, label, group_col, order=None):
    out=[]
    vals=list(df[group_col].dropna().unique())
    if order is not None:
        vals=[x for x in order if x in vals]
    else:
        vals=sorted(vals)
    for v in vals:
        g=df[df[group_col]==v]
        out.append({'table':label,'group':str(v),**summarize(g)})
    return out


def main():
    trades=pd.read_csv(IN_TRADES, parse_dates=['signal_ts','signal_complete_ts','entry_ts','exit_ts'])
    t=trades[(trades.timeframe=='4h')&(trades.rr=='R2')&(trades.resolved.astype(str).str.lower().isin(['true','1']))].copy()
    x5,coverage=b21.load5(); z4=b22b.resample_ohlc(x5,'4h')
    f=add_feature_rows(t,z4,x5)

    allrows=[]
    allrows += table_rows(f,'partition','partition',['external','development','reference_validation'])
    val=f[f.partition=='reference_validation'].copy()
    allrows += table_rows(val,'validation_year','year',[2025,2026])
    allrows += table_rows(val,'validation_quarter','quarter')
    allrows += table_rows(val,'validation_side','side',['LONG','SHORT'])

    val['risk_bucket']=pd.cut(val.risk_pct.astype(float),[-np.inf,.01,.015,.02,.03,np.inf],right=False,
                              labels=['<1%','1-1.5%','1.5-2%','2-3%','>=3%'])
    allrows += table_rows(val,'validation_risk_bucket','risk_bucket',['<1%','1-1.5%','1.5-2%','2-3%','>=3%'])

    val['body_bucket']=pd.cut(val.signal_body_ratio.astype(float),[-np.inf,.25,.5,.75,np.inf],right=False,
                              labels=['<25%','25-50%','50-75%','>=75%'])
    allrows += table_rows(val,'validation_body_bucket','body_bucket',['<25%','25-50%','50-75%','>=75%'])

    val['extension_bucket']=pd.cut(val.breakout_extension_prev_range.astype(float),[-np.inf,.10,.25,.50,np.inf],right=False,
                                   labels=['<10% prev range','10-25%','25-50%','>=50%'])
    allrows += table_rows(val,'validation_extension_bucket','extension_bucket',['<10% prev range','10-25%','25-50%','>=50%'])

    tbl=pd.DataFrame(allrows); tbl.to_csv(OUT_CSV,index=False)

    losses=val[val.exit_reason!='TP'].copy()
    loss_mfe_n=int(losses.mfe_r.notna().sum())
    loss_mfe_05=float((losses.mfe_r>=0.5).mean()) if len(losses) else np.nan
    loss_mfe_10=float((losses.mfe_r>=1.0).mean()) if len(losses) else np.nan

    md=['# B27B — Why 4H Breakout Validation Is Worse','',
        f'Source coverage: **{coverage:.4%}**. Frozen source trades: B27A 4H R2. No entry/exit rule changed.','']

    def add_table(title, name):
        md.extend([f'## {title}','', '| Group | N | W | L | WR | Net PF | Net exp/trade | Total net | Median stop |',
                   '|---|---:|---:|---:|---:|---:|---:|---:|---:|'])
        q=tbl[tbl.table==name]
        for r in q.itertuples(index=False):
            md.append(f'| {r.group} | {r.n} | {r.wins} | {r.losses} | {pct(r.wr)} | {num(r.net_pf)} | ${num(r.net_exp)} | ${num(r.total_net)} | {pct(r.med_risk)} |')
        md.append('')

    add_table('Partition comparison','partition')
    add_table('Validation by year','validation_year')
    add_table('Validation by quarter','validation_quarter')
    add_table('Validation by side','validation_side')
    add_table('Validation by stop distance','validation_risk_bucket')
    add_table('Validation by breakout candle body ratio','validation_body_bucket')
    add_table('Validation by close extension beyond previous high/low','validation_extension_bucket')

    md += ['## Losing-trade path diagnostic','',
           f'- Validation non-TP trades: **{len(losses)}**; MFE measurable: **{loss_mfe_n}**.',
           f'- Fraction of losing/non-TP trades that still reached at least **+0.5R** before exit: **{pct(loss_mfe_05)}**.',
           f'- Fraction that reached at least **+1.0R** before exit: **{pct(loss_mfe_10)}**.', '',
           'This is forensic only. Any apparent good subgroup is not a validated trading filter and requires a new preregistered test.', '',
           'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__=='__main__':
    main()
