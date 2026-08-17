#!/usr/bin/env python3
"""F6.20 — Friday +0.5R failure-to-accelerate management.

Research only; live BBC untouched. Frozen F6.12/F6.9/F6.5 and F6.18 D3
remain unchanged.

F6.19 found the 12 residual +0.5R..<+1R losses are characterized by slow
failure to accelerate, with separation around +35m and deeper trend damage by
+65m after the first +0.5R milestone.

No threshold sweep. Predeclared natural candidates:
 A35_MILESTONE_LOST:
   at +35m after first +0.5R, current progress has fallen back below +0.5R,
   latest close < EMA7, and latest completed 5m taker imbalance < 0.
 A65_STRUCTURE_FAIL:
   at +65m after first +0.5R, current progress remains below +0.5R,
   latest close < EMA20, and EMA7 <= EMA20.
 A65_STRUCTURE_FLOW:
   A65_STRUCTURE_FAIL + latest completed 5m taker imbalance < 0.

All actions use the actual decision-time 5m open and compete chronologically
with the already-frozen FIB5/EARLY10/F6.5/D3 stack.
"""
from __future__ import annotations
import json, math, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f616_friday_post1r_profit_protection as f616
import f618_friday_bearish_displacement_protection as f618

OUT=Path(os.getenv('F620_OUT','f620_out')); OUT.mkdir(parents=True,exist_ok=True)
R=f517.SL
RULES=['A35_MILESTONE_LOST','A65_STRUCTURE_FAIL','A65_STRUCTURE_FLOW']


def metrics(pnls):
    p=np.asarray(pnls,dtype=float); wins=int((p>0).sum())
    gp=float(p[p>0].sum()); gl=float(-p[p<=0].sum())
    eq=np.cumsum(p); peak=np.maximum.accumulate(np.r_[0.0,eq])
    dd=float((peak[1:]-eq).max()) if len(eq) else 0.0
    ls=cur=0
    for x in p:
        if x<=0: cur+=1; ls=max(ls,cur)
        else: cur=0
    return {'n':int(len(p)),'wins':wins,'losses':int(len(p)-wins),
            'wr':float(wins/len(p)) if len(p) else np.nan,
            'pnl':float(p.sum()),'pf':float(gp/gl) if gl>0 else math.inf,
            'dd':dd,'ls':int(ls)}


def d3_event(k,t,tr):
    ps=f616.protection_state(k,tr)
    ds=f618.displacement_state(k,tr,ps)
    if ds is None or not ds['D3_STRONG_BODY_BREAK_PRIOR_LOW']:
        return None
    dt=ds['decision_t']
    if tr.exit_t<=dt: return None
    return (dt,'D3',f616.cut_pnl(tr.entry,float(ds['decision_open'])))


def frozen_events(k,t,tr):
    ev=list(f616.existing_events(k,t,tr))
    d3=d3_event(k,t,tr)
    if d3 is not None: ev.append(d3)
    ev.sort(key=lambda x:x[0])
    return ev


def accel_state(k,tr):
    ht=f616.first_hit(k,tr,0.5*R)
    if ht is None: return None
    out={'hit_t':ht}
    for mins in (35,65):
        dt=ht+pd.Timedelta(minutes=mins)
        if dt not in k.index or tr.exit_t<=dt:
            out[mins]=None; continue
        w=k[(k.index>=ht)&(k.index<dt)]
        if len(w)<2:
            out[mins]=None; continue
        last=w.iloc[-1]
        close=float(last.close)
        progress=(close/tr.entry-1.0)
        st={
            'decision_t':dt,'decision_open':float(k.loc[dt,'open']),
            'progress_r':progress/R,
            'below_halfR':bool(progress < 0.5*R),
            'below_ema7':bool(close<float(last.ema7)),
            'below_ema20':bool(close<float(last.ema20)),
            'ema7_le_ema20':bool(float(last.ema7)<=float(last.ema20)),
            'taker_last':float(last.taker_imb),
        }
        out[mins]=st
    s35=out.get(35); s65=out.get(65)
    out['A35_MILESTONE_LOST']=bool(s35 and s35['below_halfR'] and s35['below_ema7'] and s35['taker_last']<0)
    out['A65_STRUCTURE_FAIL']=bool(s65 and s65['below_halfR'] and s65['below_ema20'] and s65['ema7_le_ema20'])
    out['A65_STRUCTURE_FLOW']=bool(out['A65_STRUCTURE_FAIL'] and s65['taker_last']<0)
    return out


def candidate_event(tr,st,rule):
    if st is None or not st[rule]: return None
    mins=35 if rule.startswith('A35') else 65
    s=st[mins]; dt=s['decision_t']
    if tr.exit_t<=dt:return None
    return (dt,rule,f616.cut_pnl(tr.entry,s['decision_open']))


def apply(k,t,tr,st,rule):
    ev=frozen_events(k,t,tr)
    ce=candidate_event(tr,st,rule)
    if ce is not None: ev.append(ce)
    if not ev:return float(tr.pnl),'PARENT',None
    ev.sort(key=lambda x:x[0]); dt,layer,pnl=ev[0]
    return float(pnl),layer,dt


def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[]; rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t); parents.append(tr)
        st=accel_state(k,tr)
        fe=frozen_events(k,t,tr)
        if fe:
            base_dt,base_layer,base_pnl=fe[0]
        else:
            base_dt,base_layer,base_pnl=None,'PARENT',float(tr.pnl)
        row={'i':i,'period':'discovery' if i<f517.SPLIT_N else 'validation','date':tr.date,
             'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),'parent_mfe_r':float(tr.mfe/R),
             'frozen_pnl':float(base_pnl),'frozen_layer':base_layer}
        if st is not None:
            for mins in (35,65):
                s=st.get(mins)
                if s:
                    for kk,v in s.items():row[f's{mins}_{kk}']=str(v) if isinstance(v,pd.Timestamp) else v
            for r in RULES: row[f'signal_{r}']=bool(st[r])
        for rule in RULES:
            pnl,layer,dt=apply(k,t,tr,st,rule)
            row[f'{rule}_pnl']=pnl; row[f'{rule}_layer']=layer
            row[f'{rule}_inc']=pnl-float(base_pnl)
            row[f'{rule}_dt']=None if dt is None else str(dt)
        rows.append(row)
    f517.assert_parent(parents)
    df=pd.DataFrame(rows); df.to_csv(OUT/'f620_rows.csv',index=False)
    parent_m=metrics(df.parent_pnl); base_m=metrics(df.frozen_pnl)
    # F6.18 D3 stack parity.
    if abs(base_m['pnl']-123.232)>0.10 or abs(base_m['wr']*100-51.45)>0.08:
        raise AssertionError(f'F6.18 stack parity mismatch {base_m}')

    out={'parent':parent_m,'frozen_four_layer':base_m,'rules':{}}
    for rule in RULES:
        pnlc=f'{rule}_pnl'; layerc=f'{rule}_layer'; incc=f'{rule}_inc'
        m=metrics(df[pnlc]); acts=df[df[layerc]==rule].copy()
        d=df[df.i<f517.SPLIT_N]; v=df[df.i>=f517.SPLIT_N]
        low_res=acts[(acts.parent_pnl<=0)&(acts.parent_mfe_r>=0.5)&(acts.parent_mfe_r<1.0)]
        vals={
            'metrics':m,'actions':int(len(acts)),
            'actions_D':int((acts.i<f517.SPLIT_N).sum()),'actions_V':int((acts.i>=f517.SPLIT_N).sum()),
            'incremental_vs_frozen':float(m['pnl']-base_m['pnl']),
            'incremental_D':float(d[incc].sum()),'incremental_V':float(v[incc].sum()),
            'parent_winners_acted':int(acts.parent_win.sum()),'parent_losses_acted':int((~acts.parent_win).sum()),
            'low_givebacks_acted':int(len(low_res)),
            'loss_to_positive':int(((acts.parent_pnl<=0)&(acts[pnlc]>0)).sum()),
            'winner_to_nonpositive':int(((acts.parent_pnl>0)&(acts[pnlc]<=0)).sum()),
            'positive_increment_actions':int((acts[incc]>0).sum()),
            'negative_increment_actions':int((acts[incc]<0).sum()),
            'wr_gain_pp':float((m['wr']-base_m['wr'])*100),
            'dd_improvement':float(base_m['dd']-m['dd']),
            'action_dates':acts[['date','period','parent_pnl','parent_mfe_r',pnlc,incc]].to_dict('records') if len(acts) else [],
        }
        vals['screen_pass']=bool(vals['incremental_vs_frozen']>0 and vals['incremental_D']>=0 and vals['incremental_V']>=0 and vals['low_givebacks_acted']>0 and vals['winner_to_nonpositive']==0)
        out['rules'][rule]=vals
    passed=[r for r in RULES if out['rules'][r]['screen_pass']]
    out['screen_pass_rules']=passed
    out['best_predeclared']=max(passed,key=lambda r:out['rules'][r]['incremental_vs_frozen']) if passed else None
    (OUT/'f620_summary.json').write_text(json.dumps(out,indent=2,default=str))
    md=['# Friday F6.20 — Failure-to-Accelerate Management','',
        '**Status: COMPLETE — same-sample provisional causal action test. Live BBC untouched.**','',
        f"Frozen FIB5/EARLY10/F6.5/D3: PnL **{base_m['pnl']:+.3f}**, WR **{base_m['wr']*100:.2f}%**, PF **{base_m['pf']:.3f}**, DD **{base_m['dd']:.3f}**.",'',
        'No threshold sweep. +0.5R milestone and 35/65m horizons were predeclared from F6.19 forensic.','']
    for rule in RULES:
        x=out['rules'][rule]; m=x['metrics']
        md += [f"## {rule}",f"- actions **{x['actions']}** (D {x['actions_D']} / V {x['actions_V']})",
               f"- low givebacks caught **{x['low_givebacks_acted']}**; winners acted **{x['parent_winners_acted']}**",
               f"- loss→positive **{x['loss_to_positive']}**; winner→nonpositive **{x['winner_to_nonpositive']}**",
               f"- incremental **{x['incremental_vs_frozen']:+.3f}**; D/V **{x['incremental_D']:+.3f} / {x['incremental_V']:+.3f}**",
               f"- managed PnL **{m['pnl']:+.3f}**, WR **{m['wr']*100:.2f}%**, PF **{m['pf']:.3f}**, DD **{m['dd']:.3f}**",
               f"- screen **{'PASS' if x['screen_pass'] else 'FAIL'}**",'']
    md += ['## Verdict',f"Best predeclared: **{out['best_predeclared']}**." if out['best_predeclared'] else 'No candidate passes the frozen screen.',
           '','Guardrail: F6.20 is motivated by same-sample F6.19 forensic, so any PASS is provisional until independent OOS trigger evidence accumulates.']
    (OUT/'F6.20_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__':main()
