#!/usr/bin/env python3
from pathlib import Path
import math
from collections import Counter
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/'BTC_LONDON_NY_SHORT_F15_FULL_HYBRID_ACTIVATION_GRID_B27AT_Trades.csv'
OUT_MD=ROOT/'BTC_LONDON_NY_SHORT_F15_LOSS_DECOMPOSITION_B27AU_Result.md'
OUT_SUM=ROOT/'BTC_LONDON_NY_SHORT_F15_LOSS_DECOMPOSITION_B27AU_Summary.csv'
OUT_WORST=ROOT/'BTC_LONDON_NY_SHORT_F15_LOSS_DECOMPOSITION_B27AU_Worst.csv'
OUT_STATUS=ROOT/'BTC_LONDON_NY_SHORT_F15_LOSS_DECOMPOSITION_B27AU_Status.txt'
MAJOR=('external','development','reference_validation')
NOTIONAL=500.0
FEE=0.40
EPS=1e-12

def pf(vals):
    x=pd.Series(vals,dtype=float).dropna(); p=float(x[x>0].sum()); n=float(-x[x<0].sum())
    if n==0 and p>0:return float('inf')
    return p/n if n>0 else np.nan

def fmt(x,d=3):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.{d}f}'

def pct(x):
    return '-' if pd.isna(x) else f'{100*float(x):.1f}%'

def stats(g):
    vals=g.net_pnl_usd.astype(float)
    wins=vals[vals>0]; losses=vals[vals<=0]
    return dict(n=len(g),wr=float((vals>0).mean()) if len(g) else np.nan,pf=pf(vals),exp=float(vals.mean()) if len(g) else np.nan,total=float(vals.sum()) if len(g) else np.nan,
                mean_win=float(wins.mean()) if len(wins) else np.nan,mean_loss=float(losses.mean()) if len(losses) else np.nan)

def main():
    tr=pd.read_csv(SRC)
    tr=tr[tr.activation=='E20'].copy()
    for c in ['entry_px','H','L','range','F65','activation_px','exit_px','net_pnl_usd','trough_extension_r','realized_exit_extension_r','capture_ratio','giveback_r']:
        tr[c]=pd.to_numeric(tr[c],errors='coerce')
    tr['activated']=tr.activated.astype(str).str.lower().eq('true')
    expected={'external':50,'development':79,'reference_validation':34,'august':1}
    expected_tot={'external':45.38940247643859,'development':-21.484136251984076,'reference_validation':-38.96368214144346,'august':-2.41989561044702}
    for p,n in expected.items():
        g=tr[tr.partition==p]
        assert len(g)==n,(p,len(g),n)
        assert abs(float(g.net_pnl_usd.sum())-expected_tot[p])<1e-8,(p,float(g.net_pnl_usd.sum()),expected_tot[p])
    assert len(tr)==164

    # Derived diagnostics.
    tr['pre_invalid']=tr.exit_reason.eq('PRE_ACT_CLOSE_INVALIDATION_F65')
    tr['f65_overshoot_r']=np.where(tr.pre_invalid,(tr.exit_px-tr.F65)/tr['range'],np.nan)
    tr['exact_e20_net']=((tr.entry_px-tr.activation_px)/tr.entry_px)*NOTIONAL-FEE
    tr['runner_delta_vs_exact_e20']=np.where(tr.activated,tr.net_pnl_usd-tr.exact_e20_net,np.nan)

    rows=[]
    parts=list(MAJOR)+['POOLED_MAJOR']
    for p in parts:
        g=tr[tr.partition.isin(MAJOR)] if p=='POOLED_MAJOR' else tr[tr.partition==p]
        base=stats(g)
        for activated_label,gg in [('ALL',g),('ACTIVATED',g[g.activated]),('NOT_ACTIVATED',g[~g.activated])]:
            s=stats(gg)
            rows.append({'partition':p,'view':activated_label,'bucket':'ALL',**s})
        for reason,gg in g.groupby('exit_reason'):
            s=stats(gg)
            rows.append({'partition':p,'view':'EXIT_REASON','bucket':reason,**s})
        pre=g[g.pre_invalid]
        if len(pre):
            q=pre.f65_overshoot_r.dropna()
            rows.append({'partition':p,'view':'PRE_INVALID_OVERSHOOT','bucket':'F65_OVERSHOOT_R','n':len(pre),'wr':np.nan,'pf':np.nan,'exp':float(q.median()),'total':float(pre.net_pnl_usd.sum()),'mean_win':float(q.quantile(.75)),'mean_loss':float(q.quantile(.90)),'max_value':float(q.max())})
        act=g[g.activated]
        for label,gg in [('ACTIVATED_ALL',act),('ACTIVATED_WIN',act[act.net_pnl_usd>0]),('ACTIVATED_LOSS',act[act.net_pnl_usd<=0])]:
            if len(gg):
                rows.append({'partition':p,'view':'PATH','bucket':label,'n':len(gg),'wr':float((gg.net_pnl_usd>0).mean()),'pf':pf(gg.net_pnl_usd),'exp':float(gg.net_pnl_usd.mean()),'total':float(gg.net_pnl_usd.sum()),
                    'mean_win':float(gg.trough_extension_r.median()),'mean_loss':float(gg.realized_exit_extension_r.median()),'max_value':float(gg.capture_ratio.median()),'giveback':float(gg.giveback_r.median()),'runner_delta':float(gg.runner_delta_vs_exact_e20.sum())})
    sm=pd.DataFrame(rows)

    major=tr[tr.partition.isin(MAJOR)].copy()
    losses=major[major.net_pnl_usd<0].sort_values('net_pnl_usd')
    gross_loss=float(-losses.net_pnl_usd.sum())
    worst5=losses.head(5); worst10=losses.head(10)
    worst_rows=[]
    for k,w in [(5,worst5),(10,worst10)]:
        mix='; '.join(f'{a}:{b}' for a,b in Counter(w.exit_reason).items())
        worst_rows.append({'k':k,'loss_abs':float(-w.net_pnl_usd.sum()),'share_of_gross_losses':float((-w.net_pnl_usd.sum())/gross_loss),'reason_mix':mix})
    worst=pd.DataFrame(worst_rows)
    worst.to_csv(OUT_WORST,index=False); sm.to_csv(OUT_SUM,index=False)

    # Core pooled attribution.
    activated=major[major.activated]; nonact=major[~major.activated]
    act_loss=activated[activated.net_pnl_usd<=0]; act_win=activated[activated.net_pnl_usd>0]
    pre=major[major.pre_invalid]
    reasons=major.groupby('exit_reason').net_pnl_usd.agg(['count','sum','mean']).sort_values('sum')
    runner_delta=float(activated.runner_delta_vs_exact_e20.sum())
    exact_e20_total=float(activated.exact_e20_net.sum()+nonact.net_pnl_usd.sum())

    md=['# B27AU — BTC London->NY SHORT F15 E20 Hybrid Loss Decomposition — Result','',
        '**Audit status: PASS.** B27AT E20 identities/totals reproduced exactly before attribution.','',
        f'Pooled-major N: **{len(major)}**; realized total: **${major.net_pnl_usd.sum():+.3f}**.','',
        '## 1. Activated vs not activated','',
        '| Group | N | WR | PF | Exp/trade $ | Total $ | Mean win $ | Mean loss $ |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for name,g in [('Activated',activated),('Not activated',nonact),('All',major)]:
        s=stats(g); md.append(f'| {name} | {s["n"]} | {pct(s["wr"])} | {fmt(s["pf"])} | {fmt(s["exp"])} | {fmt(s["total"])} | {fmt(s["mean_win"])} | {fmt(s["mean_loss"])} |')
    md += ['','## 2. PnL by exit reason','', '| Exit reason | N | Total $ | Avg $ |','|---|---:|---:|---:|']
    for reason,r in reasons.iterrows(): md.append(f'| {reason} | {int(r["count"])} | {float(r["sum"]):+.3f} | {float(r["mean"]):+.3f} |')

    q=pre.f65_overshoot_r.dropna()
    md += ['','## 3. Pre-activation invalidation tail','',
        f'Pre-activation F65 invalidations: **{len(pre)} / {len(major)} ({100*len(pre)/len(major):.1f}%)**; total **${pre.net_pnl_usd.sum():+.3f}**.',
        f'Overshoot above F65 on the completed-close exit: median **{q.median():.3f}R**, P75 **{q.quantile(.75):.3f}R**, P90 **{q.quantile(.90):.3f}R**, max **{q.max():.3f}R**.','',
        '## 4. Activated path: winners vs losers','',
        '| Activated path | N | Median trough below L | Median realized exit below L | Median capture | Median giveback | Total PnL $ |','|---|---:|---:|---:|---:|---:|---:|']
    for name,g in [('Winners',act_win),('Losers',act_loss),('All activated',activated)]:
        md.append(f'| {name} | {len(g)} | {fmt(g.trough_extension_r.median())}R | {fmt(g.realized_exit_extension_r.median())}R | {pct(g.capture_ratio.median())} | {fmt(g.giveback_r.median())}R | {g.net_pnl_usd.sum():+.3f} |')

    md += ['','## 5. Loss concentration','']
    for _,r in worst.iterrows(): md.append(f'- Worst {int(r.k)} trades contribute **{100*r.share_of_gross_losses:.1f}%** of pooled gross losses (${r.loss_abs:.3f}); exit mix: {r.reason_mix}.')
    md += ['','## 6. Runner attribution after E20','',
        f'For activated trades only, exact mechanical exit at E20 would contribute **${activated.exact_e20_net.sum():+.3f}**. Actual hybrid contribution from those same activated trades is **${activated.net_pnl_usd.sum():+.3f}**. Runner delta vs exact E20 = **${runner_delta:+.3f}**.',
        f'Keeping non-activated trades unchanged, the diagnostic exact-E20 total would be **${exact_e20_total:+.3f}** versus actual hybrid **${major.net_pnl_usd.sum():+.3f}**. This is attribution only, not a proposed strategy.','',
        '## Diagnosis','']
    # Mechanical diagnosis text based strictly on computed numbers.
    if nonact.net_pnl_usd.sum() < 0: md.append(f'1. **Primary drag before activation:** non-activated trades contribute **${nonact.net_pnl_usd.sum():+.3f}**. These never earn the E20 floor, so the hybrid cannot protect them.')
    if runner_delta < 0: md.append(f'2. **Runner also destroys value after activation:** relative to an exact E20 exit, the frozen runner gives back **${-runner_delta:.3f}** across activated trades.')
    else: md.append(f'2. **Runner adds value after activation:** +${runner_delta:.3f} versus exact E20, so post-activation management is not the main drag.')
    md.append(f'3. **Loss tail is concentrated:** worst 10 trades account for **{100*worst.iloc[1].share_of_gross_losses:.1f}%** of all gross losses.')
    md.append('4. No threshold or filter was selected in this audit; this is causal attribution only. Live BBC unchanged.')
    OUT_MD.write_text('\n'.join(md)+'\n'); OUT_STATUS.write_text('B27AU_PASS\n')
    print('\n'.join(md))

if __name__=='__main__': main()
