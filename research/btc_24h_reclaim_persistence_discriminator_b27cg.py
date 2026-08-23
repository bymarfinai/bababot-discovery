#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/'BTC_24H_DIRECT_BREAK_RETEST_SHORT_B27BZ_Events.csv'
OUT_MD=ROOT/'BTC_24H_RECLAIM_PERSISTENCE_DISCRIMINATOR_B27CG_Result.md'
OUT_DETAIL=ROOT/'BTC_24H_RECLAIM_PERSISTENCE_DISCRIMINATOR_B27CG_Detail.csv'
OUT_SIGNALS=ROOT/'BTC_24H_RECLAIM_PERSISTENCE_DISCRIMINATOR_B27CG_Signals.csv'
OUT_NB=ROOT/'BTC_24H_RECLAIM_PERSISTENCE_DISCRIMINATOR_B27CG_NoBoundary.csv'
OUT_SEL=ROOT/'BTC_24H_RECLAIM_PERSISTENCE_DISCRIMINATOR_B27CG_Selection.csv'
OUT_STATUS=ROOT/'BTC_24H_RECLAIM_PERSISTENCE_DISCRIMINATOR_B27CG_Status.txt'

BAR5=pd.Timedelta(minutes=5)
MAJOR=('external','development','reference_validation')
OOS=('external','reference_validation')
CLOCKS=('00-04','04-08','08-12','12-16','16-20','20-00')
SIG_ORDER=(
 'RECLAIM_C05','RECLAIM_C10','RECLAIM_STRONG_BODY','QUICK_RECLAIM','SLOW_RECLAIM','TIME_LEFT_120',
 'HOLD_5M_ABOVE_L','HIGHER_CLOSE_5M','HOLD_10M_ABOVE_L','EXT10_CLOSE_BEFORE_REBREAK','EXT25_CLOSE_BEFORE_REBREAK')
OBS_RANK={
 'RECLAIM_C05':0,'RECLAIM_C10':0,'RECLAIM_STRONG_BODY':0,'QUICK_RECLAIM':0,'SLOW_RECLAIM':0,'TIME_LEFT_120':0,
 'HOLD_5M_ABOVE_L':1,'HIGHER_CLOSE_5M':1,'HOLD_10M_ABOVE_L':2,'EXT10_CLOSE_BEFORE_REBREAK':3,'EXT25_CLOSE_BEFORE_REBREAK':3}


def fast_slice(x5,start,end):
    a=int(x5.index.searchsorted(start,'left')); b=int(x5.index.searchsorted(end,'left'))
    return x5.iloc[a:b]


def load_source():
    d=pd.read_csv(SRC)
    for c in ('obs_start','obs_end','break_complete_ts','retest_ts','retest_complete_ts'):
        d[c]=pd.to_datetime(d[c],utc=True,errors='coerce')
    q=d[d.partition.isin(MAJOR)&d.retest_class.eq('RETEST_RECLAIMED')].copy()
    exp={'external':202,'development':336,'reference_validation':196}
    assert len(q)==734
    for p,n in exp.items(): assert len(q[q.partition==p])==n,(p,len(q[q.partition==p]),n)
    return q.sort_values(['partition','obs_start']).reset_index(drop=True)


def eval_one(x5,r):
    start=pd.Timestamp(r.retest_complete_ts); end=pd.Timestamp(r.obs_end)
    L=float(r.L); H=float(r.H); R4=H-L
    assert R4>0 and start<=end
    base={'partition':str(r.partition),'regime':str(r.regime),'clock_block':str(r.clock_block),
          'obs_start':pd.Timestamp(r.obs_start),'obs_end':end,'reclaim_complete_ts':start,'H':H,'L':L,'R4':R4,
          'minutes_break_to_retest':float(r.minutes_break_to_retest) if pd.notna(r.minutes_break_to_retest) else np.nan}
    reclaim_start=start-BAR5
    pos=int(x5.index.searchsorted(reclaim_start,'left'))
    assert pos<len(x5) and x5.index[pos]==reclaim_start
    rb=x5.iloc[pos]
    ro, rh, rl, rc=map(float,(rb.open,rb.high,rb.low,rb.close))
    candle_range=rh-rl
    body=abs(rc-ro)
    body_ratio=body/candle_range if candle_range>0 else 0.0
    close_pos=(rc-rl)/candle_range if candle_range>0 else 0.5
    reclaim_close_ext=(rc-L)/R4
    time_left=float((end-start)/pd.Timedelta(minutes=1))
    avail={'RECLAIM_C05':reclaim_close_ext>=.05,
           'RECLAIM_C10':reclaim_close_ext>=.10,
           'RECLAIM_STRONG_BODY':bool(rc>ro and body_ratio>=.50 and close_pos>=.75),
           'QUICK_RECLAIM':bool(pd.notna(r.minutes_break_to_retest) and float(r.minutes_break_to_retest)<=10.0),
           'SLOW_RECLAIM':bool(pd.notna(r.minutes_break_to_retest) and float(r.minutes_break_to_retest)>=30.0),
           'TIME_LEFT_120':time_left>=120.0}
    if start>=end:
        out={**base,'eligible':False,'outcome':'NO_FOLLOWTHROUGH_WINDOW','persistent_like':np.nan,
             'reclaim_close':rc,'reclaim_close_ext_r4':reclaim_close_ext,'reclaim_body_ratio':body_ratio,'reclaim_close_pos':close_pos,
             'time_left_min':time_left,'final_close_loc_r4':np.nan,'net_from_reclaim_r4':np.nan,'close_span_r4':np.nan,
             'directionality_efficiency':np.nan,'nb_class':''}
        for s in SIG_ORDER: out[s]=np.nan
        return out
    q=fast_slice(x5,start,end)
    assert len(q)>=1 and q.index[0]==start
    term_idx=None; outcome='NO_BOUNDARY'
    for i,b in enumerate(q.itertuples()):
        c=float(b.close)
        if c<L: term_idx=i; outcome='REBREAK_LOW'; break
        if c>H: term_idx=i; outcome='HIGH_BREAK'; break
    z=q if term_idx is None else q.iloc[:term_idx+1]
    persistent=outcome!='REBREAK_LOW'

    c1=float(q.iloc[0].close)
    avail['HOLD_5M_ABOVE_L']=c1>L
    avail['HIGHER_CLOSE_5M']=c1>rc
    avail['HOLD_10M_ABOVE_L']=bool(len(q)>=2 and float(q.iloc[0].close)>L and float(q.iloc[1].close)>L)

    ext10=False; ext25=False
    for b in q.itertuples():
        c=float(b.close)
        if c<L: break
        if c>=L+.10*R4: ext10=True
        if c>=L+.25*R4: ext25=True
    avail['EXT10_CLOSE_BEFORE_REBREAK']=ext10
    avail['EXT25_CLOSE_BEFORE_REBREAK']=ext25

    final_loc=np.nan; net=np.nan; span=np.nan; eff=np.nan; nb_class=''
    if outcome=='NO_BOUNDARY':
        final=float(q.iloc[-1].close)
        closes=q.close.astype(float)
        final_loc=(final-L)/R4
        net=(final-rc)/R4
        span=(float(closes.max())-float(closes.min()))/R4
        denom=float(closes.max())-float(closes.min())
        eff=min(1.0,abs(final-rc)/denom) if denom>0 else np.nan
        if net>=.10: nb_class='INTERNAL_UP'
        elif net<=-.10: nb_class='INTERNAL_DOWN'
        elif abs(net)<.10 and pd.notna(eff) and eff<.35: nb_class='FLAT_CHOP_LIKE'
        else: nb_class='MIXED_INTERNAL'
    out={**base,'eligible':True,'outcome':outcome,'persistent_like':persistent,
         'reclaim_close':rc,'reclaim_close_ext_r4':reclaim_close_ext,'reclaim_body_ratio':body_ratio,'reclaim_close_pos':close_pos,
         'time_left_min':time_left,'final_close_loc_r4':final_loc,'net_from_reclaim_r4':net,'close_span_r4':span,
         'directionality_efficiency':eff,'nb_class':nb_class}
    for s in SIG_ORDER: out[s]=bool(avail[s])
    return out


def signal_metrics(g,sig):
    e=g[g.eligible].copy(); n=len(e)
    baseline=float(e.persistent_like.astype(float).mean()) if n else np.nan
    z=e[e[sig].astype(bool)].copy(); ns=len(z)
    pr=float(z.persistent_like.astype(float).mean()) if ns else np.nan
    return {'eligible_n':int(n),'signal_n':int(ns),'prevalence':ns/n if n else np.nan,
            'persistent_rate':pr,'baseline_persistent_rate':baseline,'lift':pr-baseline if ns else np.nan,
            'rebreak_rate':1-pr if ns else np.nan}


def build_signal_summary(d):
    rows=[]
    for sig in SIG_ORDER:
        for p in MAJOR: rows.append({'signal':sig,'scope':'PARTITION','name':p,**signal_metrics(d[d.partition==p],sig)})
        rows.append({'signal':sig,'scope':'POOL','name':'POOLED_OOS',**signal_metrics(d[d.partition.isin(OOS)],sig)})
        rows.append({'signal':sig,'scope':'POOL','name':'POOLED_MAJOR',**signal_metrics(d,sig)})
        for cb in CLOCKS: rows.append({'signal':sig,'scope':'CLOCK','name':cb,**signal_metrics(d[d.clock_block==cb],sig)})
    return pd.DataFrame(rows)


def nb_metrics(g):
    z=g[g.eligible & g.outcome.eq('NO_BOUNDARY')].copy(); n=len(z)
    if not n:
        return {'n':0,'final_loc_p25':np.nan,'final_loc_p50':np.nan,'final_loc_p75':np.nan,'net_p50':np.nan,'net_p75_abs':np.nan,
                'close_span_p50':np.nan,'eff_p50':np.nan,'internal_up_rate':np.nan,'internal_down_rate':np.nan,'near10_rate':np.nan,'flat_chop_rate':np.nan,'mixed_rate':np.nan}
    absnet=z.net_from_reclaim_r4.abs()
    return {'n':int(n),'final_loc_p25':float(z.final_close_loc_r4.quantile(.25)),'final_loc_p50':float(z.final_close_loc_r4.quantile(.5)),'final_loc_p75':float(z.final_close_loc_r4.quantile(.75)),
            'net_p50':float(z.net_from_reclaim_r4.quantile(.5)),'net_p75_abs':float(absnet.quantile(.75)),'close_span_p50':float(z.close_span_r4.quantile(.5)),
            'eff_p50':float(z.directionality_efficiency.dropna().median()) if z.directionality_efficiency.notna().any() else np.nan,
            'internal_up_rate':float((z.nb_class=='INTERNAL_UP').mean()),'internal_down_rate':float((z.nb_class=='INTERNAL_DOWN').mean()),
            'near10_rate':float((absnet<.10).mean()),'flat_chop_rate':float((z.nb_class=='FLAT_CHOP_LIKE').mean()),
            'mixed_rate':float((z.nb_class=='MIXED_INTERNAL').mean())}


def build_nb_summary(d):
    rows=[]
    for p in MAJOR: rows.append({'scope':'PARTITION','name':p,**nb_metrics(d[d.partition==p])})
    rows.append({'scope':'POOL','name':'POOLED_OOS',**nb_metrics(d[d.partition.isin(OOS)])})
    rows.append({'scope':'POOL','name':'POOLED_MAJOR',**nb_metrics(d)})
    for cb in CLOCKS: rows.append({'scope':'CLOCK','name':cb,**nb_metrics(d[d.clock_block==cb])})
    return pd.DataFrame(rows)


def get_sig(s,sig,scope,name):
    q=s[(s.signal==sig)&(s.scope==scope)&(s.name==name)]; assert len(q)==1; return q.iloc[0]

def get_nb(s,scope,name):
    q=s[(s.scope==scope)&(s.name==name)]; assert len(q)==1; return q.iloc[0]
def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v): return '-' if pd.isna(v) else f'{float(v):.2f}'


def main():
    src=load_source(); x5,cov=b21.load5(); assert len(x5)==698112 and abs(float(cov)-1)<1e-12
    d=pd.DataFrame([eval_one(x5,r) for r in src.itertuples(index=False)])
    assert len(d)==734
    exp={'external':202,'development':333,'reference_validation':194}
    for p,n in exp.items(): assert int((d.partition.eq(p)&d.eligible).sum())==n,(p,int((d.partition.eq(p)&d.eligible).sum()),n)
    assert int((d.partition.isin(OOS)&d.eligible).sum())==396 and int(d.eligible.sum())==729
    # exact B27CE outcome identity
    assert int((d.eligible & d.outcome.eq('REBREAK_LOW')).sum())==519
    assert int((d.eligible & d.outcome.eq('HIGH_BREAK')).sum())==41
    assert int((d.eligible & d.outcome.eq('NO_BOUNDARY')).sum())==169
    d.to_csv(OUT_DETAIL,index=False)
    ss=build_signal_summary(d); ss.to_csv(OUT_SIGNALS,index=False)
    nb=build_nb_summary(d); nb.to_csv(OUT_NB,index=False)

    devbase=float(d[d.partition.eq('development')&d.eligible].persistent_like.astype(float).mean())
    candidates=[]
    for sig in SIG_ORDER:
        r=get_sig(ss,sig,'PARTITION','development')
        ok=bool(int(r.signal_n)>=30 and float(r.persistent_rate)>=.45 and float(r.lift)>=.15)
        candidates.append({'signal':sig,'development_n':int(r.signal_n),'development_persistent_rate':float(r.persistent_rate) if pd.notna(r.persistent_rate) else np.nan,
                           'development_lift':float(r.lift) if pd.notna(r.lift) else np.nan,'development_eligible':ok,'observability_rank':OBS_RANK[sig]})
    sel=pd.DataFrame(candidates)
    eligible=sel[sel.development_eligible].copy()
    selected=None; supported=False
    if len(eligible):
        eligible=eligible.sort_values(['development_lift','observability_rank'],ascending=[False,True])
        selected=str(eligible.iloc[0].signal)
        ext=get_sig(ss,selected,'PARTITION','external'); val=get_sig(ss,selected,'PARTITION','reference_validation'); oos=get_sig(ss,selected,'POOL','POOLED_OOS')
        supported=bool(int(ext.signal_n)>=20 and float(ext.lift)>=.05 and int(val.signal_n)>=20 and float(val.lift)>=.05 and int(oos.signal_n)>=50 and float(oos.persistent_rate)>=.40 and float(oos.lift)>=.10)
    sel['selected']=sel.signal.eq(selected) if selected else False
    sel['oos_supported']=sel.signal.eq(selected)&supported if selected else False
    sel.to_csv(OUT_SEL,index=False)
    if selected is None: verdict='B27CG_PERSISTENCE_SIGN_NONE'
    elif supported: verdict='B27CG_PERSISTENCE_SIGN_SUPPORTED'
    else: verdict='B27CG_PERSISTENCE_SIGN_NOT_SUPPORTED'
    OUT_STATUS.write_text(verdict+'\n')

    lines=['# B27CG — BTC 24H Reclaim Persistence Discriminator + No-Boundary Anatomy — Result','',
           f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
           '**Audit status: PASS.** Exact B27CE reclaim cohort/outcomes reproduced: 734 total, 729 eligible, 519 Low rebreak, 41 High break, 169 no-boundary. Anatomy only; trading WR/PF/PnL/expectancy are N/A.','',
           '## Persistence-sign readout — development and untouched OOS','',
           '| Signal | Dev N | Dev persistent | Dev lift | OOS N | OOS persistent | OOS lift | OOS rebreak |',
           '|---|---:|---:|---:|---:|---:|---:|---:|']
    for sig in SIG_ORDER:
        dr=get_sig(ss,sig,'PARTITION','development'); oo=get_sig(ss,sig,'POOL','POOLED_OOS')
        lines.append(f'| {sig} | {int(dr.signal_n)} | {pct(dr.persistent_rate)} | {pct(dr.lift)} | {int(oo.signal_n)} | {pct(oo.persistent_rate)} | {pct(oo.lift)} | {pct(oo.rebreak_rate)} |')
    lines += ['', '## Frozen discriminator selection','']
    if selected:
        oo=get_sig(ss,selected,'POOL','POOLED_OOS'); ext=get_sig(ss,selected,'PARTITION','external'); val=get_sig(ss,selected,'PARTITION','reference_validation')
        lines += [f'Development selected **{selected}**. OOS support: **{"PASS" if supported else "FAIL"}**.',
                  f'External: N={int(ext.signal_n)}, persistent={pct(ext.persistent_rate)}, lift={pct(ext.lift)}. Validation: N={int(val.signal_n)}, persistent={pct(val.persistent_rate)}, lift={pct(val.lift)}. Pooled OOS: N={int(oo.signal_n)}, persistent={pct(oo.persistent_rate)}, lift={pct(oo.lift)}.']
    else:
        lines += ['No candidate met the frozen development discriminator gate.']
    lines += ['', '## NO_BOUNDARY anatomy','',
              '| Scope | N | Final location P25/P50/P75 in R4 | Median net from reclaim | P75 abs net | Median close span | Median efficiency | Internal up | Internal down | |net|<10% | Flat/chop-like | Mixed |',
              '|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for scope,name in [('PARTITION','external'),('PARTITION','development'),('PARTITION','reference_validation'),('POOL','POOLED_OOS'),('POOL','POOLED_MAJOR')]:
        r=get_nb(nb,scope,name)
        loc=f'{pct(r.final_loc_p25)} / {pct(r.final_loc_p50)} / {pct(r.final_loc_p75)}'
        lines.append(f'| {name} | {int(r.n)} | {loc} | {pct(r.net_p50)} | {pct(r.net_p75_abs)} | {pct(r.close_span_p50)} | {num(r.eff_p50)} | {pct(r.internal_up_rate)} | {pct(r.internal_down_rate)} | {pct(r.near10_rate)} | {pct(r.flat_chop_rate)} | {pct(r.mixed_rate)} |')
    lines += ['', '## NO_BOUNDARY by 4H clock — pooled major','',
              '| UTC block | N | Median net | Median close span | Flat/chop-like | Internal up | Internal down |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for cb in CLOCKS:
        r=get_nb(nb,'CLOCK',cb)
        lines.append(f'| {cb} | {int(r.n)} | {pct(r.net_p50)} | {pct(r.close_span_p50)} | {pct(r.flat_chop_rate)} | {pct(r.internal_up_rate)} | {pct(r.internal_down_rate)} |')
    lines += ['',f'**Frozen verdict: `{verdict}`.**','',
              '“Persistent-like” and “no-boundary” are same-block structural labels, not trade outcomes. A supported sign is a causal discriminator, not proof of economic causation.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); print('\n'.join(lines))

if __name__=='__main__': main()
