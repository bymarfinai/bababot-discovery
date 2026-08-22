#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_london_ny_long_entry_opt_b27r as b27r

ROOT = Path(__file__).resolve().parent.parent
SIGNALS = ROOT / 'BTC_SESSION_LIQUIDITY_PRESSURE_ENTRY_B27Q_Signals.csv'
B27R_TRADES = ROOT / 'BTC_LONDON_NY_LONG_ENTRY_OPT_B27R_Trades.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_LONG_ENTRY_TTL_B27S_Result.md'
OUT_TRADES = ROOT / 'BTC_LONDON_NY_LONG_ENTRY_TTL_B27S_Trades.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_LONG_ENTRY_TTL_B27S_Summary.csv'
OUT_SELECT = ROOT / 'BTC_LONDON_NY_LONG_ENTRY_TTL_B27S_Selection.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_LONG_ENTRY_TTL_B27S_StatusCounts.csv'

FRACS = {'F50':0.50,'F60':0.60,'F65':0.65,'F70':0.70,'F75':0.75,'F80':0.80}
TTLS = {'T15':15,'T30':30,'T45':45,'T60':60,'T90':90,'FULL':None}
PARTS = ('external','development','reference_validation','august')
DEV_PARTS = ('external','development')
KS = (1,2)
FEE = 0.40
NOTIONAL = 500.0
BAR5 = pd.Timedelta(minutes=5)


def pf(vals):
    s = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(s[s>0].sum()); neg = float(-s[s<0].sum())
    if neg == 0 and pos > 0: return float('inf')
    return pos/neg if neg > 0 else np.nan


def find_fill_ttl(q5, signal_ts, H, L, entry_px, ttl_min):
    expiry = None if ttl_min is None else signal_ts + pd.Timedelta(minutes=int(ttl_min))
    for k in range(len(q5)):
        ts = q5.index[k]
        if expiry is not None and ts >= expiry:
            return {'status':'TTL_EXPIRED','expiry_ts':expiry}
        r = q5.iloc[k]
        close = float(r.close)
        if close > H or close < L:
            return {'status':'RANGE_BROKE_BEFORE_FILL','cancel_ts':ts+BAR5}
        if float(r.low) <= entry_px <= float(r.high):
            return {'status':'FILLED','fill_k':k,'fill_ts':ts}
    return {'status':'NO_FILL' if ttl_min is None else 'TTL_EXPIRED'}


def simulate_one(x5, s, frac_name, ttl_name):
    H=float(s.previous_session_high); L=float(s.previous_session_low)
    signal_ts=pd.Timestamp(s.signal_ts); session_end=pd.Timestamp(s.active_session_end)
    frac=FRACS[frac_name]; px=float(L+frac*(H-L))
    q5=b27r.fast_slice(x5, signal_ts, session_end)
    base={
        'signal_id':f"{s.partition}|{s.transition}|{s.date_utc}|K{int(s.k)}|{signal_ts.isoformat()}",
        'partition':s.partition,'transition':s.transition,'date_utc':s.date_utc,'k':int(s.k),
        'opp_visits_at_signal':int(s.opp_visits_at_signal),'signal_ts':signal_ts,
        'structural_outcome':s.structural_outcome,'previous_session_high':H,'previous_session_low':L,
        'entry_fraction':frac_name,'entry_fraction_value':frac,'ttl':ttl_name,
        'planned_entry_px':px,'stop_px':L,'target_px':H,
        'nominal_rr':float((H-px)/(px-L)),
    }
    if q5.empty:
        return {**base,'filled':False,'entry_ts':pd.NaT,'entry_px':np.nan,'exit_ts':pd.NaT,'exit_px':np.nan,
                'exit_reason':'NO_ELIGIBLE_5M','gross_return':np.nan,'net_pnl_usd':np.nan,'hold_minutes':np.nan}
    fill=find_fill_ttl(q5,signal_ts,H,L,px,TTLS[ttl_name])
    if fill['status']!='FILLED':
        return {**base,'filled':False,'entry_ts':pd.NaT,'entry_px':np.nan,'exit_ts':pd.NaT,'exit_px':np.nan,
                'exit_reason':fill['status'],'gross_return':np.nan,'net_pnl_usd':np.nan,'hold_minutes':np.nan}
    k=int(fill['fill_k']); entry_ts=pd.Timestamp(fill['fill_ts'])
    solved=b27r.resolve_limit(q5,k,px,L,H)
    if solved is None:
        te=b27r.finish_time_exit(x5,session_end,px,entry_ts)
        if te is None:
            return {**base,'filled':True,'entry_ts':entry_ts,'entry_px':px,'exit_ts':pd.NaT,'exit_px':np.nan,
                    'exit_reason':'CENSORED','gross_return':np.nan,'net_pnl_usd':np.nan,'hold_minutes':np.nan}
        exit_ts,exit_px,ret,reason,hold=te
    else:
        exit_ts,exit_px,ret,reason=solved
        hold=float((exit_ts-entry_ts)/pd.Timedelta(minutes=1))
    return {**base,'filled':True,'entry_ts':entry_ts,'entry_px':px,'exit_ts':exit_ts,'exit_px':float(exit_px),
            'exit_reason':reason,'gross_return':float(ret),'net_pnl_usd':float(ret*NOTIONAL-FEE),'hold_minutes':hold}


def metrics(g):
    setups=len(g); r=g[g.filled.astype(bool)&pd.to_numeric(g.net_pnl_usd,errors='coerce').notna()].copy() if setups else g
    n=len(r)
    if n==0:
        return {'setups':int(setups),'fills':0,'fill_rate':0.0 if setups else np.nan,'wins':0,'losses':0,'wr':np.nan,
                'tp_rate':np.nan,'net_pf':np.nan,'net_exp':np.nan,'total_net':np.nan,'time_exit_rate':np.nan,'median_rr':np.nan}
    net=pd.to_numeric(r.net_pnl_usd,errors='coerce')
    return {'setups':int(setups),'fills':int(n),'fill_rate':float(n/setups),'wins':int((net>0).sum()),'losses':int((net<=0).sum()),
            'wr':float((net>0).mean()),'tp_rate':float((r.exit_reason=='TP_RANGE_EDGE').mean()),'net_pf':float(pf(net)),
            'net_exp':float(net.mean()),'total_net':float(net.sum()),'time_exit_rate':float((r.exit_reason=='TIME_EXIT_SESSION_END').mean()),
            'median_rr':float(pd.to_numeric(r.nominal_rr,errors='coerce').median())}


def summarize(t):
    rows=[]
    for part in PARTS:
        for k in KS:
            for f in FRACS:
                for ttl in TTLS:
                    g=t[(t.partition==part)&(t.k==k)&(t.entry_fraction==f)&(t.ttl==ttl)]
                    rows.append({'partition':part,'k':k,'entry_fraction':f,'ttl':ttl,**metrics(g)})
    return pd.DataFrame(rows)


def select_primary(sm,t):
    dev=sm[(sm.partition.isin(DEV_PARTS))&(sm.k==1)].copy()
    assert set(dev.partition.unique()).issubset(set(DEV_PARTS))
    rows=[]
    for f in FRACS:
        for ttl in TTLS:
            z=dev[(dev.entry_fraction==f)&(dev.ttl==ttl)].set_index('partition')
            if not all(p in z.index for p in DEV_PARTS): continue
            a=z.loc['external']; b=z.loc['development']
            elig=bool(a.fills>=20 and b.fills>=20 and a.net_exp>0 and b.net_exp>0 and a.net_pf>=1.10 and b.net_pf>=1.10)
            pool=t[(t.k==1)&(t.entry_fraction==f)&(t.ttl==ttl)&t.partition.isin(DEV_PARTS)&t.filled.astype(bool)&pd.to_numeric(t.net_pnl_usd,errors='coerce').notna()]
            pexp=float(pd.to_numeric(pool.net_pnl_usd,errors='coerce').mean()) if len(pool) else np.nan
            rows.append({'entry_fraction':f,'ttl':ttl,'external_fills':int(a.fills),'development_fills':int(b.fills),
                         'external_pf':a.net_pf,'development_pf':b.net_pf,'external_exp':a.net_exp,'development_exp':b.net_exp,
                         'min_pf':min(a.net_pf,b.net_pf) if not (pd.isna(a.net_pf) or pd.isna(b.net_pf)) else np.nan,
                         'pooled_dev_exp':pexp,'min_fills':int(min(a.fills,b.fills)),'dev_eligible':elig})
    sel=pd.DataFrame(rows); e=sel[sel.dev_eligible].copy()
    if len(e)==0:return sel,None
    e=e.sort_values(['min_pf','pooled_dev_exp','min_fills'],ascending=[False,False,False])
    r=e.iloc[0]
    return sel,(str(r.entry_fraction),str(r.ttl))


def audit(x5,signals,trades,b27r_trades):
    assert (signals.transition=='LONDON_TO_NEWYORK').all() and (signals.side=='LONG').all()
    assert signals.k.isin(KS).all() and (signals.opp_visits_at_signal==0).all()
    assert (trades.opp_visits_at_signal==0).all()
    for f,v in FRACS.items():
        g=trades[trades.entry_fraction==f]
        exp=g.previous_session_low.astype(float)+v*(g.previous_session_high.astype(float)-g.previous_session_low.astype(float))
        assert np.allclose(g.planned_entry_px.astype(float),exp.astype(float))
    ent=pd.to_datetime(trades.entry_ts,utc=True,errors='coerce'); sig=pd.to_datetime(trades.signal_ts,utc=True,errors='coerce')
    assert ((ent>=sig)|ent.isna()).all()
    assert np.allclose(trades.stop_px.astype(float),trades.previous_session_low.astype(float))
    assert np.allclose(trades.target_px.astype(float),trades.previous_session_high.astype(float))
    for ttl,m in TTLS.items():
        if m is None:continue
        g=trades[(trades.ttl==ttl)&trades.filled.astype(bool)]
        for r in g.itertuples(index=False):
            assert pd.Timestamp(r.entry_ts) < pd.Timestamp(r.signal_ts)+pd.Timedelta(minutes=m)
    # FULL control must exactly reproduce B27R fraction rows for same source signals.
    old=b27r_trades[(b27r_trades.transition=='LONDON_TO_NEWYORK')&(b27r_trades.k.isin(KS))&(b27r_trades.opp_visits_at_signal==0)&b27r_trades.entry_method.isin(FRACS.keys())].copy()
    old=old.rename(columns={'entry_method':'entry_fraction'})
    new=trades[trades.ttl=='FULL'].copy()
    keys=['partition','date_utc','k','signal_ts','entry_fraction']
    for df in (old,new):
        df['signal_ts']=pd.to_datetime(df.signal_ts,utc=True,errors='coerce')
    z=old.merge(new,on=keys,suffixes=('_old','_new'),how='outer',indicator=True)
    assert (z._merge=='both').all()
    assert (z.filled_old.astype(str)==z.filled_new.astype(str)).all()
    both=z[pd.to_numeric(z.net_pnl_usd_old,errors='coerce').notna()|pd.to_numeric(z.net_pnl_usd_new,errors='coerce').notna()]
    assert np.allclose(pd.to_numeric(both.net_pnl_usd_old,errors='coerce'),pd.to_numeric(both.net_pnl_usd_new,errors='coerce'),equal_nan=True)
    assert (z.exit_reason_old.fillna('NA')==z.exit_reason_new.fillna('NA')).all()


def pct(v):return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v,d=2):
    if pd.isna(v):return '-'
    if math.isinf(float(v)):return 'inf'
    return f'{float(v):.{d}f}'


def main():
    x5,coverage=b21.load5()
    s=pd.read_csv(SIGNALS)
    for c in ['signal_ts','active_session_end']:s[c]=pd.to_datetime(s[c],utc=True,errors='coerce')
    s=s[(s.transition=='LONDON_TO_NEWYORK')&(s.side=='LONG')&s.k.isin(KS)&(s.opp_visits_at_signal==0)].copy()
    rows=[]
    for q in s.itertuples(index=False):
        ser=pd.Series(q._asdict())
        for f in FRACS:
            for ttl in TTLS:
                rows.append(simulate_one(x5,ser,f,ttl))
    t=pd.DataFrame(rows)
    old=pd.read_csv(B27R_TRADES)
    audit(x5,s,t,old)
    t.to_csv(OUT_TRADES,index=False)
    sm=summarize(t);sm.to_csv(OUT_SUM,index=False)
    sel,chosen=select_primary(sm,t)
    ref_pass=False;ref=None
    if chosen:
        f,ttl=chosen
        ref=sm[(sm.partition=='reference_validation')&(sm.k==1)&(sm.entry_fraction==f)&(sm.ttl==ttl)].iloc[0]
        ref_pass=bool(ref.fills>=15 and ref.net_exp>0 and ref.net_pf>=1.20)
    sel['selected_primary']=False;sel['reference_pass']=False
    if chosen:
        mask=(sel.entry_fraction==chosen[0])&(sel.ttl==chosen[1]);sel.loc[mask,'selected_primary']=True;sel.loc[mask,'reference_pass']=ref_pass
    sel.to_csv(OUT_SELECT,index=False)
    t.groupby(['partition','k','entry_fraction','ttl','exit_reason'],dropna=False).size().reset_index(name='n').to_csv(OUT_STATUS,index=False)

    md=['# B27S — London -> New York LONG Entry Staleness / TTL — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
        '**Audit status: PASS.** FULL controls exactly reproduce B27R fraction-method outcomes. B27Q signal identity unchanged.','',
        '## Primary K1 OPP0 — external/development grid','',
        '| Part | Fraction | TTL | Fills | Fill rate | WR | PF | Net exp | Total net |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|']
    for part in DEV_PARTS:
        for r in sm[(sm.partition==part)&(sm.k==1)].itertuples(index=False):
            md.append(f'| {part} | {r.entry_fraction} | {r.ttl} | {r.fills} | {pct(r.fill_rate)} | {pct(r.wr)} | {num(r.net_pf)} | ${num(r.net_exp)} | ${num(r.total_net)} |')
    md+=['','## Frozen selection','']
    if not chosen:
        md.append('**No fraction + TTL pair passed the predeclared external + development gate.**')
    else:
        md.append(f'Selected using external + development only: **{chosen[0]} + {chosen[1]}**.')
        md.append(f'Reference-validation: fills **{int(ref.fills)}**, WR **{pct(ref.wr)}**, PF **{num(ref.net_pf)}**, net exp **${num(ref.net_exp)}** -> **{"PASS" if ref_pass else "FAIL"}**.')
    md+=['','## Secondary K2 diagnostic — best-looking rows are not promoted','',
         '| Part | Fraction | TTL | Fills | WR | PF | Net exp |','|---|---|---|---:|---:|---:|---:|']
    for part in PARTS:
        g=sm[(sm.partition==part)&(sm.k==2)].copy()
        if len(g):
            g=g.sort_values(['net_exp','fills'],ascending=[False,False]).head(8)
            for r in g.itertuples(index=False):
                md.append(f'| {part} | {r.entry_fraction} | {r.ttl} | {r.fills} | {pct(r.wr)} | {num(r.net_pf)} | ${num(r.net_exp)} |')
    md+=['','Historical research only; reference validation is not pristine OOS. Live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__=='__main__':main()
