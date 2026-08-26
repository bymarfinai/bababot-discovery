#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import eth_f85_long_exact_transplant_e1 as ethdata

ROOT=Path(__file__).resolve().parent.parent
AATR=ROOT/'ETH_LONG_F75_EARLY_RECLAIM_B27AA_ADAPT_Trades.csv'
PFX='ETH_GENERIC_F75_LONG_CLOCK_SCAN_B27DE_ADAPT'
OUT_MD=ROOT/f'{PFX}_Result.md';OUT_ROWS=ROOT/f'{PFX}_Rows.csv';OUT_SUM=ROOT/f'{PFX}_Summary.csv';OUT_LB=ROOT/f'{PFX}_DevLeaderboard.csv';OUT_STATUS=ROOT/f'{PFX}_Status.txt';OUT_PARITY=ROOT/f'{PFX}_LondonParity.csv'
BAR5=pd.Timedelta(minutes=5);REF_DUR=pd.Timedelta(hours=5,minutes=30);EXEC_DUR=pd.Timedelta(hours=6,minutes=30)
REF_BARS=66;EXEC_BARS=78;CLOCKS=tuple(range(0,24*60,30));LONDON_CLOCK=8*60
PARTS={'external':(pd.Timestamp('2020-01-01',tz='UTC'),pd.Timestamp('2022-01-01',tz='UTC')),'development':(pd.Timestamp('2022-01-01',tz='UTC'),pd.Timestamp('2025-01-01',tz='UTC')),'reference_validation':(pd.Timestamp('2025-01-01',tz='UTC'),pd.Timestamp('2026-07-30',tz='UTC')),'august':(pd.Timestamp('2026-08-01',tz='UTC'),pd.Timestamp('2026-08-21',tz='UTC'))}
MAJOR=('external','development','reference_validation');NOTIONAL=500.;FEE=.40;ENTRY_F=.75;STOP_F=.15;TARGET_EXT=.10

def fs(x,a,b):
    i=int(x.index.searchsorted(a,side='left'));j=int(x.index.searchsorted(b,side='left'));return x.iloc[i:j]
def part_for(ref_start,exec_start,exec_end):
    for n,(a,z) in PARTS.items():
        if ref_start>=a and exec_start>=a and exec_end<=z:return n
    return None

def hi_touch(r,H):return float(r.high)>=H and float(r.close)<=H
def lo_touch(r,L):return float(r.low)<=L and float(r.close)>=L

def detect_and_trade(exe,H,L,exec_end):
    R=H-L;f75=L+ENTRY_F*R;f15=L+STOP_F*R;e10=H+TARGET_EXT*R
    if not R>0:return {'status':'BAD_RANGE','executed':False}
    k1=None; hi_in=False; lo_in=False; low_visits=0
    # Find first High visit K1 with OPP0. A prior Low visit permanently invalidates OPP0.
    for k,(ts,b) in enumerate(exe.iterrows()):
        cl=float(b.close); ht=hi_touch(b,H); lt=lo_touch(b,L)
        if cl>H or cl<L:return {'status':'BREAK_BEFORE_K1','executed':False}
        if ht and lt:return {'status':'AMBIGUOUS_BOTH_BEFORE_K1','executed':False}
        if lt and not lo_in:
            low_visits+=1
            if low_visits>0:return {'status':'LOW_VISIT_BEFORE_K1','executed':False}
        if ht and not hi_in:
            if low_visits==0:k1=k;break
        hi_in=bool(ht);lo_in=bool(lt)
    if k1 is None:return {'status':'NO_K1','executed':False}
    k1_ts=exe.index[k1]; leave=None
    # Contiguous K1 High-touch episode; a strict break during it invalidates the window.
    for k in range(k1+1,len(exe)):
        b=exe.iloc[k];cl=float(b.close)
        if cl>H:return {'status':'HIGH_BREAK_DURING_K1','executed':False,'k1_bar_start':k1_ts}
        if cl<L:return {'status':'LOW_BREAK_DURING_K1','executed':False,'k1_bar_start':k1_ts}
        if hi_touch(b,H):continue
        leave=k;break
    if leave is None:return {'status':'NO_CAUSAL_LEAVE','executed':False,'k1_bar_start':k1_ts}
    eligible=leave+1
    touched=False;touch_k=None;confirm=None
    for k in range(eligible,len(exe)):
        b=exe.iloc[k];cl=float(b.close);hi=float(b.high)
        if hi>=H:return {'status':'H2_BEFORE_CONFIRM','executed':False,'k1_bar_start':k1_ts,'leave_bar_start':exe.index[leave],'touch_bar_start':exe.index[touch_k] if touch_k is not None else pd.NaT}
        if cl<L:return {'status':'LOW_BREAK_BEFORE_CONFIRM','executed':False,'k1_bar_start':k1_ts,'leave_bar_start':exe.index[leave],'touch_bar_start':exe.index[touch_k] if touch_k is not None else pd.NaT}
        if not touched:
            if float(b.low)<=f75<=float(b.high):
                touched=True;touch_k=k
                if cl>f75:confirm=k;break
        else:
            if cl>f75:confirm=k;break
    if confirm is None:return {'status':'NO_RECLAIM','executed':False,'k1_bar_start':k1_ts,'leave_bar_start':exe.index[leave],'touch_bar_start':exe.index[touch_k] if touch_k is not None else pd.NaT}
    entry_k=confirm+1
    if entry_k>=len(exe):return {'status':'NO_NEXT_ENTRY_BAR','executed':False,'k1_bar_start':k1_ts,'leave_bar_start':exe.index[leave],'touch_bar_start':exe.index[touch_k],'confirmation_bar_start':exe.index[confirm]}
    entry_ts=exe.index[entry_k];entry=float(exe.iloc[entry_k].open);ef=(entry-L)/R
    if entry>=H:return {'status':'MISSED_H2_AT_OPEN','executed':False,'k1_bar_start':k1_ts,'leave_bar_start':exe.index[leave],'touch_bar_start':exe.index[touch_k],'confirmation_bar_start':exe.index[confirm],'entry_ts':entry_ts,'entry_px':entry}
    if not(f15<entry<H):return {'status':'INVALID_ENTRY_GEOMETRY','executed':False,'k1_bar_start':k1_ts,'leave_bar_start':exe.index[leave],'touch_bar_start':exe.index[touch_k],'confirmation_bar_start':exe.index[confirm],'entry_ts':entry_ts,'entry_px':entry}
    reason=None;exit_ts=pd.NaT;exit_px=np.nan;h2_seen=False
    for k in range(entry_k,len(exe)):
        b=exe.iloc[k];hi=float(b.high);cl=float(b.close)
        if hi>=H:h2_seen=True
        if hi>=e10:
            reason='TP_E10';exit_ts=exe.index[k];exit_px=e10;break
        if cl<f15:
            reason='CLOSE_INVALIDATION_F15';exit_ts=exe.index[k]+BAR5;exit_px=cl;break
    if reason is None:
        reason='TIME_EXIT_EXEC_END';exit_ts=exec_end
        # execution window end open is supplied by caller after the slice; placeholder here
        exit_px=np.nan
    return {'status':'EXECUTED','executed':True,'k1_bar_start':k1_ts,'leave_bar_start':exe.index[leave],'touch_bar_start':exe.index[touch_k],'confirmation_bar_start':exe.index[confirm],'entry_ts':entry_ts,'entry_px':entry,'entry_fraction':ef,'F75':f75,'F15':f15,'E10':e10,'exit_ts':exit_ts,'exit_px':exit_px,'exit_reason':reason,'h2_before_exit':h2_seen}

def finalize_time_exit(x5,z,exec_end):
    if not z.get('executed',False):return z
    if z['exit_reason']=='TIME_EXIT_EXEC_END':
        p=int(x5.index.searchsorted(exec_end,side='left'))
        if p>=len(x5) or x5.index[p]!=exec_end:raise AssertionError('missing exec-end bar')
        z['exit_px']=float(x5.iloc[p].open)
    net=(float(z['exit_px'])/float(z['entry_px'])-1.)*NOTIONAL-FEE
    z['net_pnl_usd']=net;z['win']=bool(net>0);z['hold_minutes']=float((pd.Timestamp(z['exit_ts'])-pd.Timestamp(z['entry_ts']))/pd.Timedelta(minutes=1))
    return z

def pf(vals):
    x=pd.to_numeric(pd.Series(vals),errors='coerce').dropna();p=float(x[x>0].sum());n=float(-x[x<0].sum())
    if n==0 and p>0:return float('inf')
    return p/n if n>0 else np.nan
def metrics(g):
    e=g[g.executed.astype(bool)].copy();x=pd.to_numeric(e.net_pnl_usd,errors='coerce').dropna();n=len(x)
    return {'windows':len(g),'k1':int(g.k1_bar_start.notna().sum()),'executed':n,'wr':float((x>0).mean()) if n else np.nan,'pf':float(pf(x)) if n else np.nan,'exp':float(x.mean()) if n else np.nan,'net':float(x.sum()) if n else 0.0,'tp_rate':float((e.exit_reason=='TP_E10').mean()) if n else np.nan,'time_rate':float((e.exit_reason=='TIME_EXIT_EXEC_END').mean()) if n else np.nan}
def pct(v):return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v):
    if pd.isna(v):return '-'
    if math.isinf(float(v)):return 'inf'
    return f'{float(v):.2f}'
def clock_name(m):return f'{m//60:02d}:{m%60:02d}'

def main():
    x5,cov=ethdata.load5();rows=[]
    for day in pd.date_range(pd.Timestamp('2020-01-01',tz='UTC'),pd.Timestamp('2026-08-21',tz='UTC'),freq='D'):
        for cm in CLOCKS:
            rs=day+pd.Timedelta(minutes=cm);re=rs+REF_DUR;es=re;ee=es+EXEC_DUR;part=part_for(rs,es,ee)
            if part is None or es.weekday()>=5:continue
            ref=fs(x5,rs,re);exe=fs(x5,es,ee)
            if len(ref)!=REF_BARS or len(exe)!=EXEC_BARS:continue
            H=float(ref.high.max());L=float(ref.low.min());z=detect_and_trade(exe,H,L,ee);z=finalize_time_exit(x5,z,ee)
            rows.append({'partition':part,'anchor_date':str(day.date()),'clock_min':cm,'clock':clock_name(cm),'reference_start':rs,'reference_end':re,'execution_start':es,'execution_end':ee,'H':H,'L':L,'range':H-L,**z})
    d=pd.DataFrame(rows)
    for c in ('executed',):d[c]=d[c].fillna(False).astype(bool)
    d.to_csv(OUT_ROWS,index=False)

    # London parity against persisted B27AA EARLY_RECLAIM executed identities.
    aa=pd.read_csv(AATR);aa=aa[(aa.variant=='EARLY_RECLAIM')&(aa.entry_executed.astype(str).str.lower()=='true')].copy();aa['entry_ts']=pd.to_datetime(aa.entry_ts,utc=True)
    lp=[];parity=True
    for part in PARTS:
        got=d[(d.clock_min==LONDON_CLOCK)&(d.partition==part)&d.executed].copy();gset=set(pd.to_datetime(got.entry_ts,utc=True));aset=set(aa[aa.partition==part].entry_ts)
        gm=metrics(d[(d.clock_min==LONDON_CLOCK)&(d.partition==part)])
        lp.append({'partition':part,'expected_n':len(aset),'got_n':len(gset),'missing':len(aset-gset),'extra':len(gset-aset),'wr':gm['wr'],'pf':gm['pf'],'exp':gm['exp'],'net':gm['net']})
        parity=parity and gset==aset
    pd.DataFrame(lp).to_csv(OUT_PARITY,index=False)
    if not parity:
        OUT_STATUS.write_text('ETH_LONG_B27DE_ADAPT_LONDON_PARITY_FAIL\n')
        pd.DataFrame(lp).to_csv(OUT_SUM,index=False)
        raise AssertionError('London parity failed; clock ranking aborted')

    sums=[]
    for cm in CLOCKS:
        for part in PARTS:
            g=d[(d.clock_min==cm)&(d.partition==part)];s=metrics(g);sums.append({'clock_min':cm,'clock':clock_name(cm),'partition':part,**s})
    sm=pd.DataFrame(sums);sm.to_csv(OUT_SUM,index=False)
    dev=sm[sm.partition=='development'].copy();dev['dev_eligible']=(dev.executed>=25)&(dev.wr>=.70)&(dev.pf>=1.30)&(dev.exp>0)&(dev.clock_min!=LONDON_CLOCK)
    dev=dev.sort_values(['dev_eligible','pf','wr','exp','executed','clock_min'],ascending=[False,False,False,False,False,True]);dev.to_csv(OUT_LB,index=False)
    elig=dev[dev.dev_eligible]
    selected=None;rep=False
    if len(elig):
        selected=elig.iloc[0];cm=int(selected.clock_min)
        ex=sm[(sm.clock_min==cm)&(sm.partition=='external')].iloc[0];rv=sm[(sm.clock_min==cm)&(sm.partition=='reference_validation')].iloc[0]
        rep=bool(ex.executed>=15 and ex.wr>=.65 and ex.pf>=1.20 and ex.exp>0 and rv.executed>=10 and rv.wr>=.65 and rv.pf>=1.20 and rv.exp>0)
        status='ETH_LONG_B27DE_ADAPT_HISTORICAL_REPLICATION_SUPPORTED' if rep else 'ETH_LONG_B27DE_ADAPT_DEV_CLOCK_FOUND_REPLICATION_FAILED'
    else:status='ETH_LONG_B27DE_ADAPT_NO_NEW_CLOCK_CANDIDATE'
    OUT_STATUS.write_text(status+'\n')
    md=['# ETH LONG B27DE-Adapt — Generic F75 LONG Clock-Rotation Scan — Result','',f'ETHUSDT 5m rows: **{len(x5):,}**; coverage: **{cov:.4%}**.','',
        'Clock-only scan: 48 half-hour reference starts, 5h30 reference + 6h30 execution. ETH-specific F75 EARLY_RECLAIM + E10/F15 is frozen; no 4H regime filter.','',
        '## London parity','', '| Partition | Expected N | Got N | Missing | Extra | WR | PF | Exp | Net |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in lp:md.append(f'| {r["partition"]} | {r["expected_n"]} | {r["got_n"]} | {r["missing"]} | {r["extra"]} | {pct(r["wr"])} | {num(r["pf"])} | ${num(r["exp"])} | ${num(r["net"])} |')
    md += ['','**London parity: PASS.**','','## Development leaderboard — top 12','', '| Clock | N | WR | PF | Exp | Net | Eligible |','|---|---:|---:|---:|---:|---:|---|']
    for r in dev.head(12).itertuples(index=False):md.append(f'| {r.clock} | {r.executed} | {pct(r.wr)} | {num(r.pf)} | ${num(r.exp)} | ${num(r.net)} | {"YES" if r.dev_eligible else "NO"} |')
    if selected is not None:
        cm=int(selected.clock_min);ex=sm[(sm.clock_min==cm)&(sm.partition=='external')].iloc[0];rv=sm[(sm.clock_min==cm)&(sm.partition=='reference_validation')].iloc[0]
        md += ['','## Selected development clock','',f'**{selected.clock} UTC reference start** — development N={selected.executed}, WR={pct(selected.wr)}, PF={num(selected.pf)}, exp=${num(selected.exp)}, net=${num(selected.net)}.',
               f'- external: N={ex.executed}, WR={pct(ex.wr)}, PF={num(ex.pf)}, exp=${num(ex.exp)}, net=${num(ex.net)}.',
               f'- reference_validation: N={rv.executed}, WR={pct(rv.wr)}, PF={num(rv.pf)}, exp=${num(rv.exp)}, net=${num(rv.net)}.']
    md += ['',f'**Status: {status}**','', 'Historical replication uses reused partitions and is not pristine OOS. Research only; no live changes.']
    OUT_MD.write_text('\n'.join(md)+'\n')
if __name__=='__main__':main()
