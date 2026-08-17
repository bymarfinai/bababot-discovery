#!/usr/bin/env python3
"""Saturday T-Method S5.7B — Candle Morphology & Sequence Atlas.

Research only; live BBC untouched. No management action is applied.

Purpose
-------
Study whether the *shape of the completed 5m candle* at three causal Saturday
runner events separates future deep runners (later >=+0.80%) from shallow ones:
1) the +0.50% hinge candle;
2) the first completed-close giveback <=+0.40% after the hinge;
3) the completed-close rebuild >=+0.50% that occurs before <=+0.20% breakdown
   within the frozen S5.7 60m window.

No morphology threshold sweep. Fixed descriptive taxonomy:
- DOJI_LIKE: body/range <= 0.20
- STRONG_BODY: body/range >= 0.70
- CLOSE_TOP_Q / CLOSE_BOTTOM_Q: close location >=0.75 / <=0.25
- LOWER_WICK_DOM / UPPER_WICK_DOM: wick/range >=0.50
- BULL / BEAR
- ENGULF / INSIDE / OUTSIDE relative to previous completed 5m candle.

Continuous features remain primary; labels are interpretive only.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import s50_saturday_parent_forensics as s50
import s50a_saturday_adaptive_atlas_v2 as a50
import s52a_post_failure_recovery_forensics as a52
import s52b_selective_runner_protect as b52
import s57_saturday_giveback_sequence_forensics as s57

OUT=Path(os.getenv('S57B_OUT','s57b_out')); OUT.mkdir(parents=True,exist_ok=True)
SPLIT=83
EVENTS=['HINGE05','GIVEBACK40','REBUILD50']
CONT=['body_ratio','upper_wick_ratio','lower_wick_ratio','close_loc','range_pct_entry','signed_body_pct_entry','body_pct_entry','range_vs_prev','body_vs_prev']
FLAGS=['BULL','BEAR','DOJI_LIKE','STRONG_BODY','CLOSE_TOP_Q','CLOSE_BOTTOM_Q','LOWER_WICK_DOM','UPPER_WICK_DOM','ENGULF','INSIDE','OUTSIDE']


def rank_auc(x,y):
    x=np.asarray(x,dtype=float); y=np.asarray(y,dtype=bool)
    m=np.isfinite(x); x=x[m]; y=y[m]
    if len(x)==0 or y.sum()==0 or (~y).sum()==0:return np.nan
    r=pd.Series(x).rank(method='average').to_numpy(); n1=int(y.sum()); n0=int((~y).sum())
    return float((r[y].sum()-n1*(n1+1)/2)/(n1*n0))


def candle_features(k,decision_t,entry):
    """Features of completed candle known at decision_t (bar starts decision_t-5m)."""
    bt=decision_t-pd.Timedelta(minutes=5)
    if bt not in k.index:return None
    b=k.loc[bt]
    prev_t=bt-pd.Timedelta(minutes=5)
    prev=k.loc[prev_t] if prev_t in k.index else None
    o=float(b.open); h=float(b.high); l=float(b.low); c=float(b.close)
    rng=max(h-l,1e-12); body=abs(c-o)
    up=h-max(o,c); low=min(o,c)-l
    close_loc=(c-l)/rng
    bull=c>o; bear=c<o
    prev_rng=np.nan; prev_body=np.nan
    engulf=inside=outside=False
    if prev is not None:
        po=float(prev.open); ph=float(prev.high); pl=float(prev.low); pc=float(prev.close)
        prev_rng=max(ph-pl,1e-12); prev_body=abs(pc-po)
        engulf=(max(o,c)>=max(po,pc) and min(o,c)<=min(po,pc) and body>prev_body)
        inside=(h<=ph and l>=pl)
        outside=(h>=ph and l<=pl)
    br=body/rng; uw=up/rng; lw=low/rng
    return {
        'bar_t':str(bt),
        'open':o,'high':h,'low':l,'close':c,
        'body_ratio':br,'upper_wick_ratio':uw,'lower_wick_ratio':lw,'close_loc':close_loc,
        'range_pct_entry':rng/entry,'signed_body_pct_entry':(c-o)/entry,'body_pct_entry':body/entry,
        'range_vs_prev':rng/prev_rng if np.isfinite(prev_rng) and prev_rng>0 else np.nan,
        'body_vs_prev':body/prev_body if np.isfinite(prev_body) and prev_body>0 else np.nan,
        'BULL':bool(bull),'BEAR':bool(bear),
        'DOJI_LIKE':bool(br<=.20),'STRONG_BODY':bool(br>=.70),
        'CLOSE_TOP_Q':bool(close_loc>=.75),'CLOSE_BOTTOM_Q':bool(close_loc<=.25),
        'LOWER_WICK_DOM':bool(lw>=.50),'UPPER_WICK_DOM':bool(uw>=.50),
        'ENGULF':bool(engulf),'INSIDE':bool(inside),'OUTSIDE':bool(outside),
    }


def first_close_level(k,tr,start_decision,end_decision,op,level,deadline=None):
    return s57.first_close_level(k,tr,start_decision,end_decision,op,level,deadline)


def event_times(k,tr,h05,base_exit):
    gb=first_close_level(k,tr,h05,base_exit,'<=',.004)
    rb=None
    if gb is not None:
        deadline=min(base_exit,gb+pd.Timedelta(minutes=60))
        r=first_close_level(k,tr,gb,base_exit,'>=',.005,deadline)
        br=first_close_level(k,tr,gb,base_exit,'<=',.002,deadline)
        if r is not None and (br is None or r<br):rb=r
    return h05,gb,rb


def cont_compare(df,event,feat,period,mask):
    g=df[mask & df.event.eq(event)]
    de=g[g.deep]; sh=g[~g.deep]
    md=float(de[feat].median()) if len(de) and de[feat].notna().any() else np.nan
    ms=float(sh[feat].median()) if len(sh) and sh[feat].notna().any() else np.nan
    if np.isfinite(md) and np.isfinite(ms):
        direction='DEEP_HIGH' if md>ms else ('DEEP_LOW' if md<ms else 'TIE')
    else:direction='NA'
    return {'event':event,'feature':feat,'period':period,'n':len(g),'deep_n':len(de),'shallow_n':len(sh),
            'deep_median':md,'shallow_median':ms,'auc_deep_high':rank_auc(g[feat],g.deep),'direction':direction}


def flag_row(df,event,flag):
    out=[]
    for period,mask in [('full',np.ones(len(df),dtype=bool)),('disc',df.idx<SPLIT),('val',df.idx>=SPLIT)]:
        g=df[mask & df.event.eq(event)]
        a=g[g[flag]]; b=g[~g[flag]]
        dr=lambda x: float(x.deep.mean()) if len(x) else np.nan
        out.append({'event':event,'flag':flag,'period':period,'n_true':len(a),'deep_true':dr(a),'n_false':len(b),'deep_false':dr(b),
                    'delta_true_minus_false':dr(a)-dr(b) if len(a) and len(b) else np.nan,
                    'a719_true':float(a.a719_pnl.sum()),'a719_false':float(b.a719_pnl.sum())})
    return out


def candidate_flags(fdf):
    c=[]
    for event in EVENTS:
        for flag in FLAGS:
            q=fdf[(fdf.event==event)&(fdf.flag==flag)].set_index('period')
            if not {'disc','val'}.issubset(q.index):continue
            d=q.loc['disc']; v=q.loc['val']
            if d.n_true<5 or v.n_true<5 or not np.isfinite(d.delta_true_minus_false) or not np.isfinite(v.delta_true_minus_false):continue
            same=np.sign(d.delta_true_minus_false)==np.sign(v.delta_true_minus_false) and np.sign(d.delta_true_minus_false)!=0
            if same and abs(d.delta_true_minus_false)>=.15 and abs(v.delta_true_minus_false)>=.15:
                c.append({'event':event,'flag':flag,'disc_delta':float(d.delta_true_minus_false),'val_delta':float(v.delta_true_minus_false),
                          'disc_n_true':int(d.n_true),'val_n_true':int(v.n_true)})
    return c


def main():
    k=s50.load_klines(); f=s50.load_funding(); entries=s50.saturday_entries(k); trades=[s50.simulate(k,f,t) for t in entries]
    rows=[]
    hinge_n=deep_n=shallow_n=0; gb_n=rb_n=0
    for i,(t,tr) in enumerate(zip(entries,trades)):
        s240=a50.state240(k,t,tr); a719=float(a50.a719_pnl(k,f,t,tr,s240)); base_exit=b52.a719_exit_time(t,tr,s240)
        h05,h08=a52.first_hinges(k,t,tr)
        if h05 is None:continue
        hinge_n+=1; deep=bool(h08 is not None); deep_n+=int(deep); shallow_n+=int(not deep)
        ht,gb,rb=event_times(k,tr,h05,base_exit)
        for ev,dt in [('HINGE05',ht),('GIVEBACK40',gb),('REBUILD50',rb)]:
            if dt is None:continue
            if ev=='GIVEBACK40':gb_n+=1
            if ev=='REBUILD50':rb_n+=1
            feat=candle_features(k,dt,tr.entry)
            if feat is None:continue
            rows.append({'idx':i,'date':tr.date,'event':ev,'decision_t':str(dt),'deep':deep,'parent_pnl':float(tr.pnl),'a719_pnl':a719,**feat})
    df=pd.DataFrame(rows)
    # Frozen parity gates from prior milestones.
    all_parent=sum(float(x.pnl) for x in trades)
    all_a719=0.0
    for t,tr in zip(entries,trades):
        s240=a50.state240(k,t,tr); all_a719+=float(a50.a719_pnl(k,f,t,tr,s240))
    if abs(all_parent-87.199692)>.02 or abs(all_a719-103.3830997612)>.02:raise RuntimeError('control parity fail')
    if (hinge_n,deep_n,shallow_n)!=(89,61,28):raise RuntimeError(f'hinge parity fail {(hinge_n,deep_n,shallow_n)}')
    # S5.7 should have 34 rebuild-first events; giveback expected 81.
    if rb_n!=34 or gb_n!=81:raise RuntimeError(f'S5.7 event parity fail gb={gb_n} rb={rb_n}')
    df.to_csv(OUT/'s57b_event_candles.csv',index=False)

    masks={'full':np.ones(len(df),dtype=bool),'disc':df.idx<SPLIT,'val':df.idx>=SPLIT}
    cc=[]
    for ev in EVENTS:
        for feat in CONT:
            for p,m in masks.items():cc.append(cont_compare(df,ev,feat,p,m))
    cdf=pd.DataFrame(cc); cdf.to_csv(OUT/'s57b_continuous_compare.csv',index=False)

    fr=[]
    for ev in EVENTS:
        for flag in FLAGS:fr.extend(flag_row(df,ev,flag))
    fdf=pd.DataFrame(fr); fdf.to_csv(OUT/'s57b_flag_tables.csv',index=False)
    candidates=candidate_flags(fdf)

    # Sequence-pair morphology: giveback -> rebuild deltas for the 34 rebuild events.
    piv=df[df.event.isin(['GIVEBACK40','REBUILD50'])].pivot(index='idx',columns='event')
    seq=[]
    for idx in sorted(set(df[df.event.eq('REBUILD50')].idx)):
        g=df[(df.idx==idx)&(df.event=='GIVEBACK40')].iloc[0]
        r=df[(df.idx==idx)&(df.event=='REBUILD50')].iloc[0]
        seq.append({'idx':idx,'deep':bool(r.deep),
                    'body_ratio_change':float(r.body_ratio-g.body_ratio),
                    'close_loc_change':float(r.close_loc-g.close_loc),
                    'lower_wick_change':float(r.lower_wick_ratio-g.lower_wick_ratio),
                    'upper_wick_change':float(r.upper_wick_ratio-g.upper_wick_ratio),
                    'range_change_entry':float(r.range_pct_entry-g.range_pct_entry),
                    'giveback_bear':bool(g.BEAR),'rebuild_bull':bool(r.BULL),
                    'bear_to_bull':bool(g.BEAR and r.BULL)})
    sdf=pd.DataFrame(seq); sdf.to_csv(OUT/'s57b_rebuild_sequence_morphology.csv',index=False)

    seqsum=[]
    for period,g in [('full',sdf),('disc',sdf[sdf.idx<SPLIT]),('val',sdf[sdf.idx>=SPLIT])]:
        de=g[g.deep]; sh=g[~g.deep]
        rr={'period':period,'n':len(g),'deep_n':len(de),'shallow_n':len(sh),'bear_to_bull_rate_deep':float(de.bear_to_bull.mean()) if len(de) else np.nan,'bear_to_bull_rate_shallow':float(sh.bear_to_bull.mean()) if len(sh) else np.nan}
        for feat in ['body_ratio_change','close_loc_change','lower_wick_change','upper_wick_change','range_change_entry']:
            rr[f'deep_{feat}_med']=float(de[feat].median()) if len(de) else np.nan
            rr[f'shallow_{feat}_med']=float(sh[feat].median()) if len(sh) else np.nan
        seqsum.append(rr)
    pd.DataFrame(seqsum).to_csv(OUT/'s57b_sequence_compare.csv',index=False)

    summary={'parity':{'hinge_n':hinge_n,'deep_n':deep_n,'shallow_n':shallow_n,'giveback_n':gb_n,'rebuild_n':rb_n,'parent_pnl':all_parent,'a719_pnl':all_a719},
             'continuous':cc,'flags':fr,'candidate_flags':candidates,'sequence_compare':seqsum}
    (OUT/'s57b_summary.json').write_text(json.dumps(summary,indent=2,default=float))

    def pct(x):return 'NA' if not np.isfinite(x) else f'{100*x:.1f}%'
    lines=['# BTC Temporal Saturday T-Method S5.7B — Candle Morphology & Sequence Atlas','',
           '**Status:** COMPLETE — FORENSIC ONLY; NO CANDLE ACTION PROMOTED','**Research only:** live BBC untouched','',
           '## Frozen parity',f'- Hinge: **{hinge_n}** = {deep_n} deep / {shallow_n} shallow',f'- Giveback candles: **{gb_n}**',f'- Rebuild-first candles: **{rb_n}**',f'- Parent: **${all_parent:+.3f}**; A7.19: **${all_a719:+.3f}**','',
           '## Fixed morphology taxonomy','- DOJI_LIKE body/range <=20%; STRONG_BODY >=70%','- CLOSE_TOP_Q >=75%; CLOSE_BOTTOM_Q <=25%','- dominant wick >=50% of range; plus BULL/BEAR, ENGULF, INSIDE, OUTSIDE','',
           '## Continuous feature transfer','| Event / feature | Full deep vs shallow median | Discovery direction/AUC | Validation direction/AUC |','|---|---:|---:|---:|']
    for ev in EVENTS:
        for feat in CONT:
            q=cdf[(cdf.event==ev)&(cdf.feature==feat)].set_index('period'); ff=q.loc['full']; dd=q.loc['disc']; vv=q.loc['val']
            lines.append(f"| {ev} / {feat} | {ff.deep_median:.4f} / {ff.shallow_median:.4f} | {dd.direction}/{dd.auc_deep_high:.3f} | {vv.direction}/{vv.auc_deep_high:.3f} |")
    lines += ['', '## Fixed-label candidates with >=15pp same-direction separation in both halves',
              f"- **{', '.join([x['event']+'::'+x['flag'] for x in candidates]) if candidates else 'NONE'}**",'',
              '## Guardrail','- Future deep is outcome-only forensic labeling.','- No candle definition was optimized or swept.','- No entry/exit/protect/sizing rule is changed in S5.7B.']
    (OUT/'S5.7B_CHECKPOINT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(summary,indent=2,default=float))

if __name__=='__main__':main()
