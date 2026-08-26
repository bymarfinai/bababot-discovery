#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_f85_long_f15_short_collision_b27dt as dt
import tuesday_a511_true_oos_august as tue

ROOT=Path(__file__).resolve().parent.parent
PFX='BTC_TUESDAY_A511_PORTFOLIO_REVALIDATION_B27EA'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_TR=ROOT/f'{PFX}_Trades.csv'; OUT_BL=ROOT/f'{PFX}_Blocks.csv'; OUT_SLIP=ROOT/f'{PFX}_Slippage.csv'; OUT_PORT=ROOT/f'{PFX}_Portfolio.csv'; OUT_PAR=ROOT/f'{PFX}_Parity.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
MAJOR=dt.MAJOR
BAR5=pd.Timedelta(minutes=5)
NOTIONAL=tue.NOTIONAL; FEE=tue.FEE


def pf(vals):
    v=pd.to_numeric(pd.Series(vals),errors='coerce').dropna(); gp=float(v[v>0].sum()); gl=float(-v[v<0].sum())
    if gl==0 and gp>0:return float('inf')
    return gp/gl if gl>0 else np.nan

def metrics(d,col='pnl'):
    if d is None or len(d)==0:return {'n':0,'wins':0,'wr':np.nan,'pf':np.nan,'expectancy':np.nan,'net':0.0}
    v=pd.to_numeric(d[col],errors='coerce').dropna()
    return {'n':int(len(v)),'wins':int((v>0).sum()),'wr':float((v>0).mean()),'pf':pf(v),'expectancy':float(v.mean()),'net':float(v.sum())}

def part_for(t):
    t=pd.Timestamp(t)
    for name,(a,z) in dt.dr.PARTS.items():
        if a<=t<z:return name
    return None

def pnl_at(ep,px): return float(NOTIONAL*(1.0-float(px)/float(ep))-FEE)


def a52_detail(k,tr,h):
    if h is None or not (h['close_progress']<=tue.A52_WEAK and h['cum_mae']>=tue.A52_MAE):
        return None
    ep=float(tr['entry']); lp=ep*(1-tue.LOCK); d=pd.Timestamp(h['decision_t']); op=float(k.loc[d,'open'])
    if op>=lp:return {'pnl':pnl_at(ep,op),'exit_ts':d,'exit_px':op,'layer':'A5.2_MARKET'}
    for b in k[(k.index>=d)&(k.index<tr['exit_t'])].itertuples(index=False):
        if float(b.high)>=lp:return {'pnl':pnl_at(ep,lp),'exit_ts':pd.Timestamp(b.ts)+BAR5,'exit_px':lp,'layer':'A5.2_LOCK'}
        if float(b.low)<=ep*(1-tue.TP):
            return {'pnl':float(tr['pnl']),'exit_ts':pd.Timestamp(tr['exit_t']),'exit_px':float(tr['exit_px']),'layer':'PARENT_TP'}
    return {'pnl':float(tr['pnl']),'exit_ts':pd.Timestamp(tr['exit_t']),'exit_px':float(tr['exit_px']),'layer':'PARENT'}


def fast_detail(k,tr,arm,recovery=True):
    if arm is None:
        return {'pnl':float(tr['pnl']),'exit_ts':pd.Timestamp(tr['exit_t']),'exit_px':float(tr['exit_px']),'layer':'PARENT','recovery':False}
    ep=float(tr['entry']); lp=ep*(1-tue.LOCK); d=pd.Timestamp(arm['decision_t']); op=float(k.loc[d,'open'])
    if op>=lp:return {'pnl':pnl_at(ep,op),'exit_ts':d,'exit_px':op,'layer':'FASTMR_MARKET','recovery':False}
    for b in k[(k.index>=d)&(k.index<tr['exit_t'])].itertuples(index=False):
        if float(b.high)>=lp:return {'pnl':pnl_at(ep,lp),'exit_ts':pd.Timestamp(b.ts)+BAR5,'exit_px':lp,'layer':'FASTMR_LOCK','recovery':False}
        if recovery:
            prog=1.0-float(b.close)/ep
            if float(b.high)>=float(b.ema7) and float(b.close)<float(b.ema7) and prog>=tue.RECOVERY_PROGRESS:
                cancel=pd.Timestamp(b.ts)+BAR5
                if pd.Timestamp(tr['exit_t'])>cancel:
                    return {'pnl':float(tr['pnl']),'exit_ts':pd.Timestamp(tr['exit_t']),'exit_px':float(tr['exit_px']),'layer':'A5.11_RUNNER_RECOVERY','recovery':True}
    return {'pnl':float(tr['pnl']),'exit_ts':pd.Timestamp(tr['exit_t']),'exit_px':float(tr['exit_px']),'layer':'PARENT','recovery':False}


def build_a511():
    k=tue.load_extended()
    hp=tue.historical_parity(k)
    if not hp.get('pass',False): raise AssertionError('A5.11 frozen historical parity failed')
    rows=[]
    for t in tue.entries(k):
        tr=tue.simulate_parent(k,t); h=tue.first_hinge(k,tr)
        a52=a52_detail(k,tr,h)
        if a52 is not None:
            det={**a52,'a52_act':True,'fastmr_act':False,'recovery':False}
        else:
            arm=tue.fastmr_arm(k,tr,h); f=fast_detail(k,tr,arm,True); det={**f,'a52_act':False,'fastmr_act':arm is not None}
        lay=tue.layered(k,tr)
        if abs(float(det['pnl'])-float(lay['a511_pnl']))>1e-9:
            raise AssertionError(f'A5.11 detail PnL mismatch {t}: {det["pnl"]} vs {lay["a511_pnl"]}')
        exit_px=float(det['exit_px']); implied=float(tr['entry'])*(1.0-(float(det['pnl'])+FEE)/NOTIONAL)
        if abs(exit_px-implied)>max(1e-7,abs(exit_px)*1e-10):
            raise AssertionError(f'exit reconstruction mismatch {t}')
        part=part_for(t)
        if part is None: raise AssertionError(f'no partition {t}')
        rows.append({'partition':part,'entry_ts':pd.Timestamp(t),'exit_ts':pd.Timestamp(det['exit_ts']),'entry_px':float(tr['entry']),'exit_px':exit_px,'pnl':float(det['pnl']),'win':float(det['pnl'])>0,'final_layer':det['layer'],'a52_act':bool(det['a52_act']),'fastmr_act':bool(det['fastmr_act']),'recovery':bool(det.get('recovery',False))})
    q=pd.DataFrame(rows).sort_values('entry_ts').reset_index(drop=True)
    return k,hp,q


def parity_table(hp,q):
    m=metrics(q); checks=[
        ('n',m['n'],139,0),('wins',m['wins'],89,0),('wr',m['wr'],89/139,1e-12),('net',m['net'],130.33,.15),('pf',m['pf'],1.692,.01),
        ('a52_actions',int(q.a52_act.sum()),7,0),('fastmr_actions',int(q.fastmr_act.sum()),12,0),('recoveries',int(q.recovery.sum()),4,0),
    ]; rows=[]
    for field,a,e,tol in checks:
        ok=(int(a)==int(e)) if tol==0 else abs(float(a)-float(e))<=tol
        rows.append({'field':field,'actual':a,'expected':e,'pass':ok})
    rows.append({'field':'upstream_historical_parity','actual':bool(hp.get('pass')),'expected':True,'pass':bool(hp.get('pass'))})
    out=pd.DataFrame(rows)
    if not bool(out['pass'].all()): raise AssertionError('B27EA A5.11 parity failure\n'+out.to_string(index=False))
    return out


def blocks(q):
    rows=[]; arr=np.array_split(q.sort_values('entry_ts').reset_index(drop=True),8)
    for i,g in enumerate(arr,1): rows.append({'block':f'B{i}','start':g.entry_ts.min(),'end':g.entry_ts.max(),**metrics(g)})
    d=q.iloc[:83].copy(); v=q.iloc[83:].copy(); return pd.DataFrame(rows),metrics(d),metrics(v)

def slip(q):
    rows=[]
    for bps in (0,2,5,10):
        f=float(bps)/10000.0; en=q.entry_px.astype(float)*(1.0-f); ex=q.exit_px.astype(float)*(1.0+f); pnl=(1.0-ex/en)*NOTIONAL-FEE
        z=q.copy(); z['pnl_stress']=pnl; rows.append({'bps_per_fill':bps,**metrics(z,'pnl_stress')})
    return pd.DataFrame(rows)

def current_control(x5):
    raw,locked,base=dt.build_long(x5); rawL=dt.normalize_long(raw); sc=dt.build_shorts(x5); shorts=dt.normalize_short(sc); s20=shorts[shorts.clock_min_norm==1200].copy()
    full=pd.concat([rawL,s20],ignore_index=True); lk=dt.lock_rows(full,'B27EA_CURRENT_CONTROL'); acc=lk[lk.accepted_portfolio.astype(bool)].copy(); m=metrics(dt.pooled(acc))
    if not (m['n']==283 and abs(m['wr']-207/283)<1e-12 and abs(m['pf']-2.34)<=.03 and abs(m['net']-367.49)<=.30): raise AssertionError('current portfolio parity '+str(m))
    return full,acc,m

def portfolio(x5,q):
    full,control,cm=current_control(x5)
    a=q.copy(); a['side']='SHORT'; a['source']='TUESDAY_A511'; a['clock_min_norm']=1380; a['exit_ts_norm']=pd.to_datetime(a.exit_ts,utc=True); a['candidate_id']=a.partition.astype(str)+'|TUEA511|'+a.entry_ts.astype(str)
    cand=a[['partition','entry_ts','exit_ts_norm','pnl','side','source','clock_min_norm','candidate_id']].copy()
    lk=dt.lock_rows(pd.concat([full,cand],ignore_index=True),'B27EA_WITH_A511'); acc=lk[lk.accepted_portfolio.astype(bool)].copy(); am=metrics(dt.pooled(acc))
    cids=set(dt.pooled(control).candidate_id.astype(str)); current_after=dt.pooled(acc[acc.source!='TUESDAY_A511']); aids=set(current_after.candidate_id.astype(str)); displaced=cids-aids
    ta=dt.pooled(acc[acc.source=='TUESDAY_A511']); tm=metrics(ta)
    return pd.DataFrame([{'portfolio':'CURRENT_LONG_SHORT20',**cm,'tuesday_accepted_n':0,'tuesday_accepted_net':0.0,'displaced_current_n':0},
                         {'portfolio':'PLUS_TUESDAY_A511',**am,'tuesday_accepted_n':tm['n'],'tuesday_accepted_net':tm['net'],'tuesday_accepted_wr':tm['wr'],'tuesday_accepted_pf':tm['pf'],'displaced_current_n':len(displaced)}]),cm,am,tm,len(displaced)

def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def num(x):
    if pd.isna(x):return '-'
    if math.isinf(float(x)):return 'inf'
    return f'{float(x):.2f}'
def usd(x): return f'${float(x):+.2f}'

def main():
    _,hp,q=build_a511(); parity=parity_table(hp,q); bl,dseg,vseg=blocks(q); sl=slip(q)
    x5,cov=dt.dq.dn.dl.dj.b21.load5(); port,cm,am,tm,disp=portfolio(x5,q)
    stability=bool(int((bl.net>0).sum())>=6 and dseg['net']>0 and vseg['net']>0)
    s5=sl[sl.bps_per_fill==5].iloc[0]; execution=bool(float(s5.wr)>=.55 and float(s5.pf)>=1.20 and float(s5.net)>0)
    portfolio_ok=bool(am['n']>283 and am['net']>cm['net'] and am['wr']>=.70 and am['pf']>=1.80 and disp<=5 and tm['net']>0)
    supported=bool(stability and execution and portfolio_ok)
    status='B27EA_TUESDAY_A511_THIRD_EDGE_HISTORICAL_CANDIDATE_SUPPORTED' if supported else 'B27EA_TUESDAY_A511_THIRD_EDGE_NOT_SUPPORTED'
    q.to_csv(OUT_TR,index=False); parity.to_csv(OUT_PAR,index=False); bl.to_csv(OUT_BL,index=False); sl.to_csv(OUT_SLIP,index=False); port.to_csv(OUT_PORT,index=False); OUT_STATUS.write_text(status+'\n')
    m=metrics(q)
    lines=['# B27EA — Tuesday A5.11 Independent Portfolio Revalidation — Result','',f'Raw 5m control coverage: **{cov:.4%}**. Frozen Tuesday historical parity: **PASS**.','',f'A5.11 standalone: **N={m["n"]}, WR={pct(m["wr"])}, PF={num(m["pf"])}, net={usd(m["net"])}**.','',
           '## Chronological stability','', '| Block | N | WR | PF | Net |','|---|---:|---:|---:|---:|']
    for r in bl.itertuples(index=False): lines.append(f'| {r.block} | {r.n} | {pct(r.wr)} | {num(r.pf)} | {usd(r.net)} |')
    lines += ['',f'Positive blocks: **{int((bl.net>0).sum())}/8**; first83 net={usd(dseg["net"])}; last56 net={usd(vseg["net"])}; stability **{"PASS" if stability else "FAIL"}**.','',
              '## Adverse slippage — A5.11 standalone','', '| bps/fill | N | WR | PF | Net |','|---:|---:|---:|---:|---:|']
    for r in sl.itertuples(index=False): lines.append(f'| {r.bps_per_fill} | {r.n} | {pct(r.wr)} | {num(r.pf)} | {usd(r.net)} |')
    lines += ['',f'5bps execution gate: **{"PASS" if execution else "FAIL"}**.','', '## One-BTC portfolio compatibility','', '| Portfolio | N | WR | PF | Net | Tuesday accepted | Tuesday net | Displaced current |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in port.itertuples(index=False): lines.append(f'| {r.portfolio} | {r.n} | {pct(r.wr)} | {num(r.pf)} | {usd(r.net)} | {r.tuesday_accepted_n} | {usd(r.tuesday_accepted_net)} | {r.displaced_current_n} |')
    lines += ['',f'Portfolio gate (N>283, net improves, WR>=70%, PF>=1.80, <=5 displaced, incremental net>0): **{"PASS" if portfolio_ok else "FAIL"}**.','',f'**Status: `{status}`.**','',
              'Evidence limitation: A5.11 is frozen reused-history with insufficient pristine forward observations. B27EA is compatibility/revalidation only. Pre-B27DX control is used and must be rerun after the known LONG causal correction. No live exchange writes changed.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); print('\n'.join(lines))

if __name__=='__main__': main()
