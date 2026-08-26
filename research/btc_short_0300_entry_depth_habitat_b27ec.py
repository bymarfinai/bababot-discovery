#!/usr/bin/env python3
from __future__ import annotations
import math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_generic_f15_short_clock_scan_b27dr as dr
import btc_london_ny_short_mirror_b27ad as ad
import btc_f85_long_f15_short_collision_b27dt as dt

ROOT=Path(__file__).resolve().parent.parent
PFX='BTC_SHORT_0300_ENTRY_DEPTH_HABITAT_B27EC'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_TR=ROOT/f'{PFX}_Trades.csv'; OUT_SUM=ROOT/f'{PFX}_Summary.csv'; OUT_BL=ROOT/f'{PFX}_Blocks.csv'; OUT_SL=ROOT/f'{PFX}_Slippage.csv'; OUT_PORT=ROOT/f'{PFX}_Portfolio.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
CLOCK_MIN=180
DEPTHS=(0.05,0.15,0.25,0.35)
BAR5=pd.Timedelta(minutes=5); MAJOR=dr.MAJOR


def pf(vals):
    v=pd.to_numeric(pd.Series(vals),errors='coerce').dropna(); gp=float(v[v>0].sum()); gl=float(-v[v<0].sum())
    if gl==0 and gp>0:return float('inf')
    return gp/gl if gl>0 else np.nan

def metrics(z,col='fixed_net_pnl_usd'):
    if z is None or len(z)==0:return {'n':0,'wins':0,'wr':np.nan,'pf':np.nan,'expectancy':np.nan,'net':0.0}
    v=pd.to_numeric(z[col],errors='coerce').dropna()
    return {'n':len(v),'wins':int((v>0).sum()),'wr':float((v>0).mean()),'pf':pf(v),'expectancy':float(v.mean()),'net':float(v.sum())}

def generic_blind(x5,w,frac):
    H=float(w.H); L=float(w.L); rng=H-L; f=L+frac*rng
    base={'partition':w.partition,'anchor_date_utc':w.date_utc,'signal_ts':pd.Timestamp(w.signal_ts),'window_status':w.window_status,
          'H':H,'L':L,'range':rng,'FENTRY':f,'F65':L+.65*rng,'E20_DOWN':L-.20*rng,'entry_depth':frac,
          'eligible_start':w.eligible_start,'h2_bar_start':w.h2_bar_start,'opposite_break_bar_start':w.opposite_break_bar_start,'session_end':pd.Timestamp(w.session_end)}
    if pd.isna(w.eligible_start) or str(w.window_status).startswith('NO_WINDOW') or w.window_status=='NO_CAUSAL_LEAVE_BY_SESSION_END':
        return {**base,'touch':False,'touch_bar_start':pd.NaT}
    term=ad.terminal_start(w); q=ad.fast_slice(x5,pd.Timestamp(w.eligible_start),term)
    for ts,r in q.iterrows():
        if float(r.low)<=L or float(r.close)>H: raise AssertionError('terminal event leaked into eligible slice')
        if float(r.low)<=f<=float(r.high): return {**base,'touch':True,'touch_bar_start':pd.Timestamp(ts)}
    return {**base,'touch':False,'touch_bar_start':pd.NaT}

def confirm(x5,b):
    if not b.touch:return {**dict(b),'entry_executed':False,'entry_start':pd.NaT,'entry_px':np.nan,'entry_status':'NO_TOUCH'}
    ts=pd.Timestamp(b.touch_bar_start); r=x5.loc[ts]
    if not float(r.close)<float(b.FENTRY): return {**dict(b),'entry_executed':False,'entry_start':pd.NaT,'entry_px':np.nan,'entry_status':'NO_SAME_BAR_REJECTION'}
    et=ts+BAR5
    if et>=pd.Timestamp(b.session_end) or et not in x5.index:return {**dict(b),'entry_executed':False,'entry_start':et,'entry_px':np.nan,'entry_status':'NO_NEXT_BAR'}
    ep=float(x5.loc[et,'open']); frac=(ep-float(b.L))/float(b['range'])
    if ep<=float(b.L): return {**dict(b),'entry_executed':False,'entry_start':et,'entry_px':ep,'entry_status':'MISSED_H2_AT_OPEN'}
    if not (float(b.L)<ep<float(b.F65)): return {**dict(b),'entry_executed':False,'entry_start':et,'entry_px':ep,'entry_status':'INVALID_ENTRY_GEOMETRY'}
    if pd.notna(b.h2_bar_start) and pd.Timestamp(b.h2_bar_start)<et: raise AssertionError('entry after H2')
    return {**dict(b),'entry_executed':True,'entry_start':et,'entry_px':ep,'entry_fraction':frac,'entry_status':'EXECUTED'}

def build_cases(x5):
    anchors=pd.date_range(x5.index.min().normalize(),x5.index.max().normalize(),freq='D',tz='UTC'); rows=[]
    for anchor in anchors:
        ref_start=anchor+pd.Timedelta(minutes=CLOCK_MIN); ref_end=ref_start+dr.REF_DUR; exec_start=ref_end; exec_end=exec_start+dr.EXEC_DUR
        part=dr.part_for_window(ref_start,exec_start,exec_end)
        if part is None or exec_start.weekday()>=5: continue
        ref=dr.fast_slice(x5,ref_start,ref_end); exe=dr.fast_slice(x5,exec_start,exec_end)
        if len(ref)!=dr.REF_BARS or len(exe)!=dr.EXEC_BARS: continue
        H=float(ref.high.max()); L=float(ref.low.min())
        if not (math.isfinite(H) and math.isfinite(L) and H>L):continue
        sig=dr.find_short_k1(exe,H,L)
        if sig is None:continue
        s=pd.Series({'partition':part,'date_utc':str(anchor.date()),'previous_session_high':H,'previous_session_low':L,'signal_bar_start':sig,'signal_ts':sig+BAR5,'active_session_end':exec_end})
        w=pd.Series(ad.build_window(x5,s))
        for frac in DEPTHS:
            b=pd.Series(generic_blind(x5,w,frac)); e=pd.Series(confirm(x5,b)); fx=ad.simulate_fixed(x5,e)
            rows.append({**dict(e),**fx})
    return pd.DataFrame(rows)
def summarize(cases):
    rows=[]
    for f in DEPTHS:
        for p in dr.PART_ORDER:
            z=cases[(cases.entry_depth==f)&(cases.partition==p)&cases.entry_executed.astype(bool)&cases.fixed_net_pnl_usd.notna()]
            rows.append({'entry_depth':f,'partition':p,**metrics(z)})
    return pd.DataFrame(rows)
def parity(summary):
    exp={'external':(19,.737,13.51),'development':(37,.838,17.92),'reference_validation':(11,.545,-4.15)}
    for p,(n,wr,net) in exp.items():
        r=summary[(summary.entry_depth==.15)&(summary.partition==p)].iloc[0]
        if not (int(r.n)==n and abs(float(r.wr)-wr)<=.006 and abs(float(r.net)-net)<=.35): raise AssertionError(f'F15 parity fail {p}: {r.to_dict()}')
    z=summary[(summary.entry_depth==.15)&summary.partition.isin(MAJOR)]
    if int(z.n.sum())!=67 or abs(float(z.net.sum())-27.29)>.5: raise AssertionError('F15 pooled parity fail')
def eligible(r): return bool(r.n>=20 and r.wr>=.70 and r.pf>=1.30 and r.expectancy>0)
def select(summary):
    d=summary[summary.partition=='development'].copy(); d['eligible']=d.apply(eligible,axis=1); q=d[d.eligible]
    if q.empty:return None
    return q.sort_values(['pf','wr','expectancy','n','entry_depth'],ascending=[False,False,False,False,True]).iloc[0]
def replication(summary,f):
    for p,nmin in [('external',15),('reference_validation',10)]:
        r=summary[(summary.entry_depth==f)&(summary.partition==p)].iloc[0]
        if not (r.n>=nmin and r.wr>=.65 and r.pf>=1.20 and r.expectancy>0):return False
    return True
def block_stats(tr):
    q=tr.sort_values('entry_start').reset_index(drop=True); cuts=np.linspace(0,len(q),5,dtype=int); rows=[]
    for i in range(4):
        g=q.iloc[cuts[i]:cuts[i+1]]; rows.append({'block':f'B{i+1}',**metrics(g)})
    return pd.DataFrame(rows)
def slippage(tr):
    rows=[]
    for bps in (0,2,5,10):
        f=bps/10000; en=tr.entry_px.astype(float)*(1-f); ex=tr.fixed_exit_px.astype(float)*(1+f); pnl=(1-ex/en)*ad.NOTIONAL-ad.FEE
        z=tr.copy(); z['stress']=pnl; rows.append({'bps_per_fill':bps,**metrics(z,'stress')})
    return pd.DataFrame(rows)
def portfolio(x5,tr):
    raw,_,_=dt.build_long(x5); rawL=dt.normalize_long(raw); sc=dt.build_shorts(x5); sh=dt.normalize_short(sc); s20=sh[sh.clock_min_norm==1200].copy()
    ctrlraw=pd.concat([rawL,s20],ignore_index=True); ctrl=dt.lock_rows(ctrlraw,'B27EC_CTRL'); ca=dt.pooled(ctrl[ctrl.accepted_portfolio.astype(bool)]); cm=metrics(ca,'pnl')
    a=tr.copy(); a['side']='SHORT'; a['source']='SHORT_0300_DEPTH'; a['clock_min_norm']=CLOCK_MIN; a['exit_ts_norm']=pd.to_datetime(a.fixed_exit_px.index if False else a.fixed_exit_reason,errors='coerce')
    a['exit_ts_norm']=pd.to_datetime(a.apply(lambda r: pd.Timestamp(r.entry_start)+pd.Timedelta(minutes=float(r.fixed_hold_minutes)),axis=1),utc=True)
    a['pnl']=a.fixed_net_pnl_usd; a['candidate_id']=a.partition.astype(str)+'|0300D|'+a.entry_start.astype(str)
    cand=a[['partition','entry_start','exit_ts_norm','pnl','side','source','clock_min_norm','candidate_id']].rename(columns={'entry_start':'entry_ts'})
    lk=dt.lock_rows(pd.concat([ctrlraw,cand],ignore_index=True),'B27EC_PLUS'); acc=dt.pooled(lk[lk.accepted_portfolio.astype(bool)]); am=metrics(acc,'pnl')
    added=acc[acc.source=='SHORT_0300_DEPTH']; tm=metrics(added,'pnl'); current_after=acc[acc.source!='SHORT_0300_DEPTH']; displaced=len(set(ca.candidate_id.astype(str))-set(current_after.candidate_id.astype(str)))
    return pd.DataFrame([{'portfolio':'CONTROL',**cm,'added_n':0,'added_net':0,'displaced':0},{'portfolio':'PLUS_SELECTED',**am,'added_n':tm['n'],'added_net':tm['net'],'displaced':displaced}]),cm,am,tm,displaced

def pct(x):return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def num(x):return '-' if pd.isna(x) else ('inf' if math.isinf(float(x)) else f'{float(x):.2f}')
def main():
    x5,cov=dr.b21.load5(); cases=build_cases(x5); summary=summarize(cases); parity(summary); sel=select(summary)
    status='B27EC_NO_DEVELOPMENT_ENTRY_DEPTH'; lines=['# B27EC — SHORT 03:00 Entry-Depth Habitat — Result','',f'5m coverage **{cov:.4%}**. F15 parity **PASS**.','']
    lines += ['| Depth | Ext N/WR/PF/Net | Dev N/WR/PF/Net | Val N/WR/PF/Net |','|---|---|---|---|']
    for f in DEPTHS:
        vals=[]
        for p in ['external','development','reference_validation']:
            r=summary[(summary.entry_depth==f)&(summary.partition==p)].iloc[0]; vals.append(f'{r.n}/{pct(r.wr)}/{num(r.pf)}/${r.net:+.2f}')
        lines.append(f'| F{int(f*100):02d} | {vals[0]} | {vals[1]} | {vals[2]} |')
    bl=pd.DataFrame(); sl=pd.DataFrame(); port=pd.DataFrame()
    if sel is not None:
        f=float(sel.entry_depth); rep=replication(summary,f); tr=cases[(cases.entry_depth==f)&cases.partition.isin(MAJOR)&cases.entry_executed.astype(bool)&cases.fixed_net_pnl_usd.notna()].copy(); bl=block_stats(tr); stability=bool(((bl.net>0)&(bl.pf>1)).sum()>=3); sl=slippage(tr); s5=sl[sl.bps_per_fill==5].iloc[0]; stress=bool(s5.wr>=.65 and s5.pf>=1.20 and s5.net>0)
        pok=False
        if rep and stability and stress:
            port,cm,am,tm,disp=portfolio(x5,tr); pok=bool(am.net>cm.net and am.wr>=.70 and am.pf>=1.80 and disp<=5 and tm.net>0)
        supported=rep and stability and stress and pok; status='B27EC_SHORT_0300_ENTRY_HABITAT_SUPPORTED' if supported else 'B27EC_SHORT_0300_ENTRY_HABITAT_NOT_SUPPORTED'
        lines += ['',f'Selected on development only: **F{int(f*100):02d}**. Replication **{"PASS" if rep else "FAIL"}**; chronological **{"PASS" if stability else "FAIL"}**; 5bps **{"PASS" if stress else "FAIL"}**; portfolio **{"PASS" if pok else "FAIL"}**.']
        if len(sl):
            lines += ['','## Slippage','', '| bps/fill | N | WR | PF | Net |','|---:|---:|---:|---:|---:|']
            for r in sl.itertuples(index=False):lines.append(f'| {r.bps_per_fill} | {r.n} | {pct(r.wr)} | {num(r.pf)} | ${r.net:+.2f} |')
        if len(port):
            lines += ['','## Portfolio','', '| Portfolio | N | WR | PF | Net | Added N | Added net | Displaced |','|---|---:|---:|---:|---:|---:|---:|---:|']
            for r in port.itertuples(index=False):lines.append(f'| {r.portfolio} | {r.n} | {pct(r.wr)} | {num(r.pf)} | ${r.net:+.2f} | {r.added_n} | ${r.added_net:+.2f} | {r.displaced} |')
    cases.to_csv(OUT_TR,index=False); summary.to_csv(OUT_SUM,index=False); bl.to_csv(OUT_BL,index=False); sl.to_csv(OUT_SL,index=False); port.to_csv(OUT_PORT,index=False); OUT_STATUS.write_text(status+'\n'); lines += ['',f'**Status: `{status}`.**','', 'Research only. Frozen structure unchanged; only entry depth varied.']; OUT_MD.write_text('\n'.join(lines)+'\n'); print('\n'.join(lines))
if __name__=='__main__':main()
