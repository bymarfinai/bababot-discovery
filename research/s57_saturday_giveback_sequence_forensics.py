#!/usr/bin/env python3
"""Saturday T-Method S5.7 — Giveback Sequence Forensic.

Research only; live BBC untouched. No management action is applied.

Purpose
-------
After Saturday BUY causally reaches the frozen +0.50% favorable hinge, map the
*sequence* of giveback and recovery rather than using a single EMA/price snapshot.

Predeclared natural levels already used in prior Saturday research:
- +0.50% proven impulse hinge
- <=+0.40% completed-close giveback
- >=+0.50% completed-close rebuild
- <=+0.20% deeper breakdown
- <=+0.30% second failure after a rebuild
- 60m observation windows

Forensic outcome: future deep runner >=+0.80% (same frozen S5.2/S5.4 label).
No threshold sweep, no protect/exit simulation, no future label in a trading rule.
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

OUT=Path(os.getenv('S57_OUT','s57_out')); OUT.mkdir(parents=True,exist_ok=True)
SPLIT=83


def met(g):
    if len(g)==0:
        return {'n':0,'deep_rate':np.nan,'shallow_rate':np.nan,'parent_pnl':0.0,'a719_pnl':0.0}
    return {'n':len(g),'deep_rate':float(g.deep.mean()),'shallow_rate':float((~g.deep).mean()),
            'parent_pnl':float(g.parent_pnl.sum()),'a719_pnl':float(g.a719_pnl.sum())}


def splitrow(df,mask,label):
    g=df[mask]; d=g[g.idx<SPLIT]; v=g[g.idx>=SPLIT]
    r={'label':label,**met(g)}
    for p,x in [('disc',d),('val',v)]:
        m=met(x)
        for k,z in m.items(): r[f'{p}_{k}']=z
    return r


def completed_rows(k,start_decision,end_decision):
    """Bars whose completed information is known after start_decision and before exit."""
    if start_decision is None or end_decision is None or end_decision<=start_decision:
        return k.iloc[0:0]
    # bar timestamp b.ts completes at b.ts+5m; first post-decision bar starts at start_decision
    return k[(k.index>=start_decision)&(k.index<end_decision)]


def first_close_level(k,tr,start_decision,end_decision,op,level,deadline=None):
    bars=completed_rows(k,start_decision,end_decision)
    for b in bars.itertuples(index=False):
        d=b.ts+pd.Timedelta(minutes=5)
        if deadline is not None and d>deadline: break
        p=float(b.close)/tr.entry-1
        if (op=='>=' and p>=level) or (op=='<=' and p<=level):
            return d
    return None


def giveback_features(k,tr,h05,gb40):
    bt=gb40-pd.Timedelta(minutes=5)
    b=k.loc[bt]
    bars=k[(k.index>=h05)&(k.index<gb40)]
    def slope(col,mins):
        old=bt-pd.Timedelta(minutes=mins)
        if old not in k.index:return np.nan
        a=float(k.loc[bt,col]); z=float(k.loc[old,col]); return a/z-1 if z else np.nan
    return {
        'gb40_progress':float(b.close)/tr.entry-1,
        'gb40_ema7_dist':float(b.close)/float(b.ema7)-1,
        'gb40_ema20_dist':float(b.close)/float(b.ema20)-1,
        'gb40_ema7_slope60':slope('ema7',60),
        'gb40_ema20_slope60':slope('ema20',60),
        'gb40_posthinge_taker':float(np.nanmean(bars.taker_imb.to_numpy(dtype=float))) if len(bars) else np.nan,
        'gb40_posthinge_floor':float((bars.close/tr.entry-1).min()) if len(bars) else np.nan,
        'gb40_posthinge_highclose':float((bars.close/tr.entry-1).max()) if len(bars) else np.nan,
    }


def sequence(k,tr,h05,base_exit):
    out={
        'gb40':False,'gb40_min':np.nan,'stage1':'NO_GB40',
        'rebuild50_t':None,'break20_t':None,'rebuild50_delay':np.nan,'break20_delay':np.nan,
        'second_fail30':False,'second_fail30_delay':np.nan,
        'stage2':'NO_REBUILD','sequence':'NO_GB40'
    }
    gb40=first_close_level(k,tr,h05,base_exit,'<=',.004)
    if gb40 is None:return out
    out['gb40']=True; out['gb40_min']=(gb40-h05).total_seconds()/60
    out.update(giveback_features(k,tr,h05,gb40))
    deadline=min(base_exit,gb40+pd.Timedelta(minutes=60))
    rb=first_close_level(k,tr,gb40,base_exit,'>=',.005,deadline)
    br=first_close_level(k,tr,gb40,base_exit,'<=',.002,deadline)
    out['rebuild50_t']=None if rb is None else str(rb)
    out['break20_t']=None if br is None else str(br)
    if rb is not None:out['rebuild50_delay']=(rb-gb40).total_seconds()/60
    if br is not None:out['break20_delay']=(br-gb40).total_seconds()/60
    if rb is not None and (br is None or rb<br):
        out['stage1']='REBUILD50_FIRST'
        # After a real completed-close rebuild, ask whether a second failure <=+0.30
        # appears within another 60m. This is observed causally; no action attached.
        d2=min(base_exit,rb+pd.Timedelta(minutes=60))
        sf=first_close_level(k,tr,rb,base_exit,'<=',.003,d2)
        if sf is not None:
            out['second_fail30']=True; out['second_fail30_delay']=(sf-rb).total_seconds()/60
            out['stage2']='SECOND_FAIL30'
            out['sequence']='GB40_REBUILD50_SECONDFAIL30'
        else:
            out['stage2']='HOLD_AFTER_REBUILD'
            out['sequence']='GB40_REBUILD50_HOLD60'
    elif br is not None and (rb is None or br<rb):
        out['stage1']='BREAK20_FIRST'; out['sequence']='GB40_BREAK20_FIRST'
    elif rb is not None and br is not None and rb==br:
        out['stage1']='SAME_DECISION_AMBIG'; out['sequence']='GB40_AMBIG'
    else:
        out['stage1']='NEITHER_60'; out['sequence']='GB40_NEITHER60'
    return out


def med(g,c):
    return float(g[c].median()) if len(g) and c in g and g[c].notna().any() else np.nan


def compare_features(df):
    feats=['gb40_min','gb40_progress','gb40_ema7_dist','gb40_ema20_dist','gb40_ema7_slope60','gb40_ema20_slope60','gb40_posthinge_taker','gb40_posthinge_floor','gb40_posthinge_highclose']
    rows=[]
    for period,g in [('full',df),('disc',df[df.idx<SPLIT]),('val',df[df.idx>=SPLIT])]:
        g=g[g.gb40]
        de=g[g.deep]; sh=g[~g.deep]
        for c in feats:
            rows.append({'period':period,'feature':c,'deep_n':len(de),'shallow_n':len(sh),
                         'deep_median':med(de,c),'shallow_median':med(sh,c)})
    return rows


def main():
    k=s50.load_klines();
    # ensure EMA columns exist regardless of upstream loader implementation
    if 'ema7' not in k.columns:k['ema7']=k['close'].ewm(span=7,adjust=False).mean()
    if 'ema20' not in k.columns:k['ema20']=k['close'].ewm(span=20,adjust=False).mean()
    f=s50.load_funding(); entries=s50.saturday_entries(k); trades=[s50.simulate(k,f,t) for t in entries]
    rows=[]
    for i,(t,tr) in enumerate(zip(entries,trades)):
        s240=a50.state240(k,t,tr); a719=float(a50.a719_pnl(k,f,t,tr,s240)); base_exit=b52.a719_exit_time(t,tr,s240)
        h05,h08=a52.first_hinges(k,t,tr)
        if h05 is None:continue
        r={'idx':i,'date':tr.date,'parent_pnl':float(tr.pnl),'a719_pnl':a719,'deep':bool(h08 is not None),
           'time_to05_min':(h05-t).total_seconds()/60}
        r.update(sequence(k,tr,h05,base_exit)); rows.append(r)
    df=pd.DataFrame(rows).sort_values('idx').reset_index(drop=True)

    # frozen parity gates
    if len(df)!=89 or int(df.deep.sum())!=61 or int((~df.deep).sum())!=28:raise RuntimeError('hinge/deep parity fail')
    all_parent=sum(float(x.pnl) for x in trades)
    all_a719=0.0
    for t,tr in zip(entries,trades):
        s240=a50.state240(k,t,tr); all_a719+=float(a50.a719_pnl(k,f,t,tr,s240))
    if abs(all_parent-87.199692)>.02 or abs(all_a719-103.3830997612)>.02:raise RuntimeError('control parity fail')

    df.to_csv(OUT/'s57_sequence_rows.csv',index=False)
    tables={}
    tables['gb40']=[splitrow(df,df.gb40,'HAS_GB40'),splitrow(df,~df.gb40,'NO_GB40')]
    tables['stage1']=[]
    for st in ['REBUILD50_FIRST','BREAK20_FIRST','NEITHER_60','SAME_DECISION_AMBIG']:
        tables['stage1'].append(splitrow(df,df.stage1.eq(st),st))
    tables['sequence']=[]
    for st in ['GB40_REBUILD50_SECONDFAIL30','GB40_REBUILD50_HOLD60','GB40_BREAK20_FIRST','GB40_NEITHER60','GB40_AMBIG','NO_GB40']:
        tables['sequence'].append(splitrow(df,df.sequence.eq(st),st))

    # speed views are predeclared descriptive bins, not trading rules
    tables['gb40_speed']=[]
    for label,lo,hi in [('GB40_<=15M',0,15),('GB40_20_60M',15,60),('GB40_>60M',60,np.inf)]:
        m=df.gb40&(df.gb40_min>lo)&(df.gb40_min<=hi)
        if label=='GB40_<=15M':m=df.gb40&(df.gb40_min<=15)
        tables['gb40_speed'].append(splitrow(df,m,label))

    fc=compare_features(df); pd.DataFrame(fc).to_csv(OUT/'s57_giveback_feature_compare.csv',index=False)
    flat=[]
    for family,rr in tables.items():
        for r in rr:flat.append({'family':family,**r})
    pd.DataFrame(flat).to_csv(OUT/'s57_sequence_tables.csv',index=False)

    # Shadow eligibility for S5.8: descriptive only. No action is run here.
    eligible=[]
    for r in tables['sequence']:
        if r['disc_n']>=5 and r['val_n']>=5 and np.isfinite(r['disc_deep_rate']) and np.isfinite(r['val_deep_rate']):
            if r['disc_deep_rate']<.40 and r['val_deep_rate']<.40:
                eligible.append(r['label'])

    summary={'hinge_n':len(df),'deep_n':int(df.deep.sum()),'shallow_n':int((~df.deep).sum()),
             'parent_all_pnl':all_parent,'a719_all_pnl':all_a719,'tables':tables,
             'feature_compare':fc,'s58_shadow_eligible_sequences':eligible}
    (OUT/'s57_summary.json').write_text(json.dumps(summary,indent=2,default=float))

    def pct(x):return 'NA' if not np.isfinite(x) else f'{100*x:.1f}%'
    def money(x):return f'${x:+.3f}'
    def tab(rr):
        z=['| State | N | Deep | A7.19 PnL | Discovery N/Deep/PnL | Validation N/Deep/PnL |','|---|---:|---:|---:|---:|---:|']
        for r in rr:
            z.append(f"| {r['label']} | {r['n']} | {pct(r['deep_rate'])} | {money(r['a719_pnl'])} | {r['disc_n']} / {pct(r['disc_deep_rate'])} / {money(r['disc_a719_pnl'])} | {r['val_n']} / {pct(r['val_deep_rate'])} / {money(r['val_a719_pnl'])} |")
        return '\n'.join(z)

    md=['# BTC Temporal Saturday T-Method S5.7 — Giveback Sequence Forensic','',
        '**Status:** COMPLETE — FORENSIC ONLY; NO MANAGEMENT ACTION PROMOTED','**Research only:** live BBC untouched','',
        '## Frozen parity',f'- +0.50 hinge trades: **{len(df)}** = 61 future-deep / 28 shallow',f'- Parent all-trade PnL: **{money(all_parent)}**',f'- A7.19 all-trade PnL: **{money(all_a719)}**','',
        '## Predeclared sequence geometry','- after +0.50 hinge, first completed close <=+0.40 = giveback event','- for 60m after giveback: >=+0.50 rebuild vs <=+0.20 breakdown, whichever occurs first','- after rebuild-first: observe whether <=+0.30 second failure occurs within 60m','- no action/exit/protect is attached to any state','',
        '## Giveback occurrence',tab(tables['gb40']),'','## First post-giveback branch',tab(tables['stage1']),'','## Full sequence taxonomy',tab(tables['sequence']),'','## Giveback speed',tab(tables['gb40_speed']),'',
        '## S5.8 shadow eligibility',f"- sequences with >=5 observations in both halves and <40% deep rate in both: **{', '.join(eligible) if eligible else 'NONE'}**",'',
        '## Guardrail','- Future deep is forensic outcome only.','- Thresholds are inherited natural levels from prior Saturday work; no sweep performed.','- No S5.8 FastMR action is run in this milestone.']
    (OUT/'S5.7_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(summary,indent=2,default=float))

if __name__=='__main__':main()
