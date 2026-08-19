#!/usr/bin/env python3
"""SR82-T0: conditional executable rejection-candle trade on frozen PRIOR_PROVEN_SUPPORT context."""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
import pandas as pd
import btc_friday_sr80_level_reliability as sr
import btc_friday_sr82_support_external as s82

ROOT=Path(__file__).resolve().parent.parent
CTX=ROOT/'BTC_Friday_SR82_Support_External_Result.json'
OUT_MD=ROOT/'BTC_Friday_SR82_T0_Rejection_Trade_Result.md'
OUT_JSON=ROOT/'BTC_Friday_SR82_T0_Rejection_Trade_Result.json'
OUT_ROWS=ROOT/'BTC_Friday_SR82_T0_Rejection_Trade_Rows.csv'
COST=.0015;NOTIONAL=500.;HOLD_BARS=72


def pf(vals):
    gp=sum(v for v in vals if v>0);gl=-sum(v for v in vals if v<0)
    return gp/gl if gl>0 else (999.0 if gp>0 else None)
def stats(z):
    vals=z.pnl_usd.astype(float).tolist() if len(z) else []
    if not vals:return {'n':0,'wins':0,'wr':None,'pnl':0.0,'exp':None,'pf':None}
    w=sum(v>0 for v in vals);return {'n':len(vals),'wins':w,'wr':w/len(vals),'pnl':sum(vals),'exp':sum(vals)/len(vals),'pf':pf(vals)}
def blocks(z):
    if z.empty:return {f'B{i}':stats(z) for i in range(1,5)}
    dates=sorted(z.friday_wib.unique());out={}
    for i,ch in enumerate(np.array_split(np.array(dates,dtype=object),4)):out[f'B{i+1}']=stats(z[z.friday_wib.isin(set(ch))])
    return out

def simulate(k,entry_t,entry,target,stop):
    j=int(k.index.searchsorted(entry_t,side='left'))
    if j>=len(k) or k.index[j]!=entry_t:return None
    bars=k.iloc[j:j+HOLD_BARS]
    if len(bars)!=HOLD_BARS:return None
    exit_px=None;reason=None;exit_t=None
    for t,b in bars.iterrows():
        hit_stop=float(b.low)<=stop;hit_tp=float(b.high)>=target
        if hit_stop:
            exit_px=stop;reason='STOP';exit_t=t;break
        if hit_tp:
            exit_px=target;reason='TARGET';exit_t=t;break
    if exit_px is None:
        b=bars.iloc[-1];exit_px=float(b.close);reason='TIME';exit_t=bars.index[-1]+pd.Timedelta(minutes=5)
    gross=exit_px/entry-1.0;net=gross-COST
    return {'exit_t':str(exit_t),'exit_price':exit_px,'reason':reason,'gross_ret':gross,'net_ret':net,'pnl_usd':net*NOTIONAL,'win':int(net>0)}

def main():
    if not CTX.exists():raise RuntimeError('SR82 context result missing')
    ctx=json.loads(CTX.read_text())
    if ctx.get('verdict')!='BTC_FRIDAY_SR82_SUPPORT_EXTERNAL_80_CANDIDATE':
        out={'protocol':'SR82-T0','status':'NOT_RUN_CONTEXT_REJECTED','context_verdict':ctx.get('verdict'),'verdict':'REJECT_SR82_T0_REJECTION_TRADE','reason':'Frozen conditional protocol forbids trade evaluation unless SR82 context passes.'}
        OUT_JSON.write_text(json.dumps(out,indent=2)+'\n');OUT_MD.write_text(f"# BTC Friday SR82-T0 — Result\n\n**NOT RUN** — SR82 context verdict was `{ctx.get('verdict')}`.\n\nFrozen protocol forbids rescue trade testing after a failed context.\n");print(json.dumps(out,indent=2));return
    k=s82.load5();h=sr.build_h1(k);events,viol=s82.build(k,h);rows=[];skips={'not_bullish_rejection':0,'touch_bar_already_resolved':0,'entry_outside_boundaries':0,'missing_next_bar':0}
    for _,e in events.iterrows():
        touch=pd.Timestamp(e.touch_utc);fs=pd.Timestamp(e.freeze_utc);level=float(e.level)
        hc=sr.completed_h1_before(h,fs)
        if hc.empty or not np.isfinite(hc.iloc[-1].atr14):continue
        atr=float(hc.iloc[-1].atr14);target=level+.50*atr;stop=level-.50*atr
        if touch not in k.index:continue
        b=k.loc[touch]
        if float(b.high)>=target or float(b.low)<=stop:
            skips['touch_bar_already_resolved']+=1;continue
        if not (float(b.close)>level and float(b.close)>float(b.open)):
            skips['not_bullish_rejection']+=1;continue
        entry_t=touch+pd.Timedelta(minutes=5)
        if entry_t not in k.index:
            skips['missing_next_bar']+=1;continue
        entry=float(k.loc[entry_t].open)
        if entry>=target or entry<=stop:
            skips['entry_outside_boundaries']+=1;continue
        tr=simulate(k,entry_t,entry,target,stop)
        if tr is None:continue
        rows.append({'friday_wib':e.friday_wib,'freeze_utc':str(fs),'touch_utc':str(touch),'entry_utc':str(entry_t),'cluster_id':e.cluster_id,'level':level,'atr':atr,'target':target,'stop':stop,'entry':entry,'sources':e.sources,'families':e.families,'prior_resolved':int(e.prior_resolved),**tr})
    z=pd.DataFrame(rows)
    if len(z):z.to_csv(OUT_ROWS,index=False)
    s=stats(z);bl=blocks(z);positive=sum(q['n']>=2 and q['pnl']>0 for q in bl.values());ok=bool(s['n']>=12 and s['wr'] is not None and s['wr']>=.80 and s['pnl']>0 and s['exp'] is not None and s['exp']>0 and s['pf'] is not None and s['pf']>1 and positive>=3 and viol==0)
    out={'protocol':'SR82-T0','context_verdict':ctx['verdict'],'external_window':ctx.get('external_window'),'candidate_context_touches':len(events),'skips':skips,'trades':s,'blocks':bl,'positive_blocks':positive,'integrity_violations':viol,'verdict':'BTC_FRIDAY_REJECTION_TRADE_80_CANDIDATE' if ok else 'REJECT_SR82_T0_REJECTION_TRADE'}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n');F=lambda x,d=2:'-' if x is None else f'{x:.{d}f}';md=['# BTC Friday SR82-T0 — Executable Rejection Candle Trade','',f"**Verdict: {out['verdict']}**",'',f"Context touches: **{len(events)}**; executable rejection trades: **{s['n']}**",f"Skips: `{skips}`",f"Integrity violations: **{viol}**",'', '| Trades | Wins | WR | PnL | Exp/trade | PF |','|---:|---:|---:|---:|---:|---:|',f"| {s['n']} | {s['wins']} | {F(100*s['wr'] if s['wr'] is not None else None)}% | ${F(s['pnl'])} | ${F(s['exp'],3)} | {F(s['pf'],3)} |",'', '## Chronological blocks','', '| Block | N | Wins | WR | PnL | PF |','|---|---:|---:|---:|---:|---:|']
    for b,q in bl.items():md.append(f"| {b} | {q['n']} | {q['wins']} | {F(100*q['wr'] if q['wr'] is not None else None)}% | ${F(q['pnl'])} | {F(q['pf'],3)} |")
    md += ['','Entry is strictly next-5m-open after a bullish rejection touch candle; no result-dependent tuning.'];OUT_MD.write_text('\n'.join(md)+'\n');print(json.dumps(out,indent=2,default=str))

if __name__=='__main__':main()
