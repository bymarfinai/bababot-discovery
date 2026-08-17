#!/usr/bin/env python3
"""F6.14A fast/vectorized parity implementation of Friday remaining-loss anatomy.
Research only. Live BBC untouched. No rule tuning.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd
import f517_regime_attribution as f517
import f611_friday_fibonacci_forensic as f611
import f69_friday_early_sink_candidate_robustness as f69
import f613_friday_three_layer_integration as f613

OUT=Path(os.getenv('F614A_OUT','f614a_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL; SPLIT=f517.SPLIT_N

def precompute_fib_baseline(k):
    hi=k.high.astype(float).shift(1).rolling(24,min_periods=12).max()
    lo=k.low.astype(float).shift(1).rolling(24,min_periods=12).min()
    ref=k.close.astype(float).shift(1)
    r2=100.0*(hi-lo)/ref
    # At decision t, f612 uses s=t-24h,...,t-5m (288 points), excluding s=t.
    return r2.shift(1).rolling(288,min_periods=1).median()

def fib5_fast(k,baseline,t,tr):
    f2=f611.fib_features(k,t,float(tr.entry),120)
    b=float(baseline.loc[t]) if t in baseline.index else np.nan
    if f2 is None or not np.isfinite(b): return False,f2,b
    return bool(float(k.loc[t].close)<tr.entry and tr.exit_t>t+pd.Timedelta(minutes=5) and float(f2['retr_depth'])<=0.382 and float(f2['range_pct'])>b),f2,b

def checkpoints(k,t,tr):
    out={}
    for m in [5,10,15,30,60,120,180]:
        d=t+pd.Timedelta(minutes=m)
        if tr.exit_t<=d: out[m]={'alive':False}; continue
        x=k[(k.index>=t)&(k.index<d)]
        if len(x)!=m//5: out[m]={'alive':False}; continue
        last=x.iloc[-1]; qv=float(x.quote_volume.sum()); tb=float(x.taker_buy_quote.sum())
        out[m]={'alive':True,'progress':float(last.close)/tr.entry-1.0,
                'close_above_entry':bool(float(last.close)>=tr.entry),
                'high_reclaim':bool(float(x.high.max())>=tr.entry),
                'ema7_dist':float(last.close)/float(last.ema7)-1.0,
                'ema20_dist':float(last.close)/float(last.ema20)-1.0,
                'taker':(2*tb/qv-1.0) if qv>0 else np.nan,
                'mfe':float(x.high.max())/tr.entry-1.0,'mae':1.0-float(x.low.min())/tr.entry}
    return out

def main():
    k=f517.load_klines(); baseline=precompute_fib_baseline(k)
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[]; rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8); tr=f517.simulate_parent(k,t); parents.append(tr)
        a5,f2,b=fib5_fast(k,baseline,t,tr); a10=f69.early_state(k,t,tr); a60=f69.f65_state(k,t,tr)
        bars=k[(k.index>=t)&(k.index<tr.exit_t)].copy(); first=bars.iloc[0]; rest=bars.iloc[1:]
        first5_red=bool(float(first.close)<tr.entry); strict=bool(first5_red and (rest.empty or float(rest.high.max())<tr.entry-1e-12))
        mfe=float(tr.mfe); mfe_r=mfe/R; mae_r=float(tr.mae)/R
        fav=bars.high.astype(float)/tr.entry-1.0; peak_min=int((fav.idxmax()-t)/pd.Timedelta(minutes=1))+5
        if strict: arch='A_IMMEDIATE_SINK'
        elif mfe_r<0.5: arch='B_NEVER_GOT_0.5R'
        elif mfe_r<1: arch='C_PARTIAL_LT_1R'
        elif mfe_r<2: arch='D_GOOD_START_GIVEBACK_1_2R'
        elif mfe_r<2.5: arch='E_RUNNER_GIVEBACK_2_2.5R'
        else: arch='F_ALMOST_TP_GIVEBACK_GE_2.5R'
        layer='PARENT'; managed=float(tr.pnl)
        if a5: layer='FIB5'; managed=f613.cut_pnl(tr.entry,float(k.loc[t+pd.Timedelta(minutes=5),'open']))
        elif a10: layer='EARLY10'; managed=f613.cut_pnl(tr.entry,float(k.loc[t+pd.Timedelta(minutes=10),'open']))
        elif a60: layer='F65_60'; managed=f613.cut_pnl(tr.entry,float(k.loc[t+pd.Timedelta(minutes=60),'open']))
        cp=checkpoints(k,t,tr)
        row={'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,'parent_pnl':float(tr.pnl),'parent_win':tr.pnl>0,
             'reason':tr.reason,'managed_pnl':managed,'layer':layer,'a5':a5,'a10':a10,'a60':a60,
             'first5_red':first5_red,'strict_sink':strict,'mfe_r':mfe_r,'mae_r':mae_r,'peak_min':peak_min,'archetype':arch,
             'fib2h_retr':float(f2['retr_depth']) if f2 else np.nan,'fib2h_range_pct':float(f2['range_pct']) if f2 else np.nan,
             'fib_baseline':b,'shallow382':bool(f2 and float(f2['retr_depth'])<=0.382),'expanded2h':bool(f2 and np.isfinite(b) and float(f2['range_pct'])>b)}
        for m,st in cp.items():
            for kk,v in st.items():row[f'cp{m}_{kk}']=v
        rows.append(row)
    f517.assert_parent(parents); df=pd.DataFrame(rows)
    parity={'fib5':int(df.a5.sum()),'early10':int(df.a10.sum()),'f65':int(df.a60.sum())}
    if parity != {'fib5':9,'early10':10,'f65':6}: raise RuntimeError(f'layer parity failed {parity}')
    df.to_csv(OUT/'f614a_rows.csv',index=False)
    losses=df[df.parent_pnl<=0].copy(); untouched=losses[losses.layer=='PARENT'].copy(); winners=df[df.parent_pnl>0].copy()
    def grp(g):
        return {'n':int(len(g)),'pnl':float(g.parent_pnl.sum()),'median_mfe_r':float(g.mfe_r.median()) if len(g) else np.nan,
                'median_peak_min':float(g.peak_min.median()) if len(g) else np.nan,'first5_red_pct':float(g.first5_red.mean()) if len(g) else np.nan,
                'median_fib_retr':float(g.fib2h_retr.median()) if len(g) else np.nan,'shallow_expanded_pct':float((g.shallow382&g.expanded2h).mean()) if len(g) else np.nan}
    all_arch={a:grp(g) for a,g in losses.groupby('archetype')}; un_arch={a:grp(g) for a,g in untouched.groupby('archetype')}
    cpcomp={}
    for m in [5,10,15,30,60,120,180]:
        cpcomp[str(m)]={}
        for name,g in [('untouched_loss',untouched),('winner',winners)]:
            a=g[g[f'cp{m}_alive']==True] if f'cp{m}_alive' in g else g.iloc[0:0]
            cpcomp[str(m)][name]={'n':int(len(a)),'progress':float(a[f'cp{m}_progress'].median()) if len(a) else np.nan,
                                  'above_entry_pct':float(a[f'cp{m}_close_above_entry'].mean()) if len(a) else np.nan,
                                  'taker':float(a[f'cp{m}_taker'].median()) if len(a) else np.nan,
                                  'ema7_dist':float(a[f'cp{m}_ema7_dist'].median()) if len(a) else np.nan,
                                  'mfe_r':float((a[f'cp{m}_mfe']/R).median()) if len(a) else np.nan}
    facts={'parent_losses':int(len(losses)),'intercepted':int((losses.layer!='PARENT').sum()),'untouched':int(len(untouched)),
           'untouched_sl':int((untouched.reason=='SL').sum()),'untouched_timeout':int((untouched.reason=='TIMEOUT').sum()),
           'never_05R':int((untouched.mfe_r<.5).sum()),'reach_05R':int((untouched.mfe_r>=.5).sum()),'reach_1R':int((untouched.mfe_r>=1).sum()),
           'reach_2R':int((untouched.mfe_r>=2).sum()),'reach_25R':int((untouched.mfe_r>=2.5).sum()),
           'first5_red':int(untouched.first5_red.sum()),'first5_green':int((~untouched.first5_red).sum())}
    out={'parity':parity,'facts':facts,'all_loss_archetypes':all_arch,'untouched_archetypes':un_arch,
         'layers_on_losses':losses.layer.value_counts().to_dict(),'untouched_discovery':int((untouched.i<SPLIT).sum()),'untouched_validation':int((untouched.i>=SPLIT).sum()),
         'checkpoint_compare':cpcomp,
         'untouched_dates':untouched[['date','period','reason','parent_pnl','archetype','mfe_r','peak_min','first5_red','fib2h_retr','shallow382','expanded2h']].to_dict('records')}
    (OUT/'f614a_summary.json').write_text(json.dumps(out,indent=2,default=float))
    pd.crosstab(losses.archetype,losses.layer).to_csv(OUT/'f614a_layer_archetype.csv')
    md=['# F6.14A Friday Remaining Loss Anatomy','', '**Status: COMPLETE — FORENSIC ONLY; FROZEN LAYERS UNCHANGED**','',
        f"- Parent losses **{facts['parent_losses']}**; intercepted **{facts['intercepted']}**; untouched **{facts['untouched']}**.",
        f"- Untouched never +0.5R **{facts['never_05R']}**; reached +0.5R **{facts['reach_05R']}**; +1R **{facts['reach_1R']}**; +2R **{facts['reach_2R']}**; +2.5R **{facts['reach_25R']}**.",
        f"- Untouched first5 red/green **{facts['first5_red']}/{facts['first5_green']}**.",'','## Untouched anatomy']
    for a,x in un_arch.items(): md.append(f"- {a}: **{x['n']}**")
    (OUT/'F6.14A_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=float))
if __name__=='__main__':main()
