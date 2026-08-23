#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd
import btc_mtf_bull_cascade_b21 as b21

ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/'BTC_24H_RECLAIM_PERSISTENCE_DISCRIMINATOR_B27CG_Detail.csv'
OUT_MD=ROOT/'BTC_24H_CLOCK_CONFIRMATION_B27CQ_Result.md'
OUT_DETAIL=ROOT/'BTC_24H_CLOCK_CONFIRMATION_B27CQ_Detail.csv'
OUT_SUM=ROOT/'BTC_24H_CLOCK_CONFIRMATION_B27CQ_Summary.csv'
OUT_MAP=ROOT/'BTC_24H_CLOCK_CONFIRMATION_B27CQ_Map.csv'
OUT_STATUS=ROOT/'BTC_24H_CLOCK_CONFIRMATION_B27CQ_Status.txt'
OUT_AUDIT=ROOT/'BTC_24H_CLOCK_CONFIRMATION_B27CQ_Audit.txt'

BAR5=pd.Timedelta(minutes=5)
EXTRA=pd.Timedelta(hours=4)
MAJOR=('external','development','reference_validation')
REUSED=('external','reference_validation')
CLOCKS=('00-04','04-08','08-12','12-16','16-20','20-00')
WIB={'00-04':'07-11','04-08':'11-15','08-12':'15-19','12-16':'19-23','16-20':'23-03','20-00':'03-07'}
GATES=('BASE','WEAK_C05','WEAK_C10','NOT_STRONG_BODY','QUICK_RECLAIM','TIME_LEFT_120')
TIE_ORDER={'WEAK_C05':0,'WEAK_C10':1,'NOT_STRONG_BODY':2,'QUICK_RECLAIM':3,'TIME_LEFT_120':4}


def as_bool(s):
    if s.dtype==bool:return s.copy()
    return s.astype(str).str.lower().eq('true')


def fast_slice(x,start,end):
    a=int(x.index.searchsorted(start,'left')); b=int(x.index.searchsorted(end,'left'))
    return x.iloc[a:b]


def load_source():
    d=pd.read_csv(SRC)
    for c in ('obs_start','obs_end','reclaim_complete_ts'):
        d[c]=pd.to_datetime(d[c],utc=True,errors='coerce')
    d['eligible']=as_bool(d['eligible'])
    for c in ('RECLAIM_C05','RECLAIM_C10','RECLAIM_STRONG_BODY','QUICK_RECLAIM','TIME_LEFT_120'):
        d[c]=as_bool(d[c])
    q=d[d.partition.isin(MAJOR)&d.eligible].copy()
    exp={'external':202,'development':333,'reference_validation':194}
    assert len(q)==729,len(q)
    for p,n in exp.items(): assert len(q[q.partition.eq(p)])==n,(p,len(q[q.partition.eq(p)]),n)
    assert q.reclaim_complete_ts.notna().all()
    # Exact B27CG structural identity.
    got=q.outcome.value_counts().to_dict()
    assert int(got.get('REBREAK_LOW',0))==519,got
    assert int(got.get('HIGH_BREAK',0))==41,got
    assert int(got.get('NO_BOUNDARY',0))==169,got
    return q.sort_values(['partition','obs_start']).reset_index(drop=True)


def gate_pass(r,gate):
    if gate=='BASE': return True
    if gate=='WEAK_C05': return not bool(r.RECLAIM_C05)
    if gate=='WEAK_C10': return not bool(r.RECLAIM_C10)
    if gate=='NOT_STRONG_BODY': return not bool(r.RECLAIM_STRONG_BODY)
    if gate=='QUICK_RECLAIM': return bool(r.QUICK_RECLAIM)
    if gate=='TIME_LEFT_120': return bool(r.TIME_LEFT_120)
    raise KeyError(gate)


def eval_f05(x5,r):
    start=pd.Timestamp(r.reclaim_complete_ts); obs_end=pd.Timestamp(r.obs_end); horizon=obs_end+EXTRA
    H=float(r.H); L=float(r.L); R4=float(r.R4); F05=L+.05*R4; T10=L-.10*R4
    assert R4>0 and abs(R4-(H-L))<1e-7*max(1.0,R4) and start<obs_end
    q0=fast_slice(x5,start,obs_end); qall=fast_slice(x5,start,horizon)
    assert len(q0)>=1 and q0.index[0]==start and len(qall)>=len(q0)
    base={'partition':str(r.partition),'regime':str(r.regime),'clock_block':str(r.clock_block),
          'obs_start':pd.Timestamp(r.obs_start),'obs_end':obs_end,'reclaim_complete_ts':start,
          'H':H,'L':L,'R4':R4,'F05':F05,'T10':T10}
    fill_idx=None; fill_ts=pd.NaT; cancel='NO_FILL_BEFORE_BLOCK_END'
    for i,b in enumerate(q0.itertuples()):
        if float(b.high)>=F05:
            fill_idx=i; fill_ts=q0.index[i]; cancel=''; break
        if float(b.close)<L:
            cancel='LOW_BREAK_BEFORE_FILL'; break
        if float(b.close)>H:
            cancel='HIGH_BREAK_BEFORE_FILL'; break
    if fill_idx is None:
        return {**base,'base_filled':False,'base_fill_ts':pd.NaT,'base_cancel_reason':cancel,
                'rebreak_confirmed':False,'rebreak_complete_ts':pd.NaT,'t10_reached':False,'t10_ts':pd.NaT,
                'high_failure':False,'high_failure_ts':pd.NaT,'unresolved':False,
                'minutes_reclaim_to_fill':np.nan,'minutes_fill_to_rebreak':np.nan,'minutes_fill_to_t10':np.nan}

    rebreak=False; rb_complete=pd.NaT; t10=False; t10_ts=pd.NaT; hf=False; hf_ts=pd.NaT
    fb=qall.iloc[fill_idx]; fb_ts=qall.index[fill_idx]; c=float(fb.close)
    if c<L:
        rebreak=True; rb_complete=fb_ts+BAR5
    elif c>H:
        hf=True; hf_ts=fb_ts+BAR5
    if not hf:
        for i in range(fill_idx+1,len(qall)):
            ts=qall.index[i]; b=qall.iloc[i]; c=float(b.close); lo=float(b.low)
            if not rebreak:
                if c<L:
                    rebreak=True; rb_complete=ts+BAR5; continue
                if c>H:
                    hf=True; hf_ts=ts+BAR5; break
                continue
            if ts<rb_complete: continue
            if lo<=T10:
                t10=True; t10_ts=ts+BAR5; break
            if c>H:
                hf=True; hf_ts=ts+BAR5; break
    unresolved=bool((not t10) and (not hf))
    return {**base,'base_filled':True,'base_fill_ts':fill_ts,'base_cancel_reason':'',
            'rebreak_confirmed':bool(rebreak),'rebreak_complete_ts':rb_complete,
            't10_reached':bool(t10),'t10_ts':t10_ts,'high_failure':bool(hf),'high_failure_ts':hf_ts,
            'unresolved':unresolved,
            'minutes_reclaim_to_fill':float((fill_ts-start)/pd.Timedelta(minutes=1)),
            'minutes_fill_to_rebreak':float((rb_complete-fill_ts)/pd.Timedelta(minutes=1)) if rebreak else np.nan,
            'minutes_fill_to_t10':float((t10_ts-fill_ts)/pd.Timedelta(minutes=1)) if t10 else np.nan}


def build_detail(x5,src):
    rows=[]
    for r in src.itertuples(index=False):
        base=eval_f05(x5,r)
        for gate in GATES:
            gp=gate_pass(r,gate)
            filled=bool(gp and base['base_filled'])
            rows.append({**base,'gate':gate,'gate_pass':gp,'filled':filled,
                         'fill_ts':base['base_fill_ts'] if filled else pd.NaT,
                         'cancel_reason':('GATE_REJECT' if not gp else base['base_cancel_reason']),
                         'rebreak_after_fill':bool(base['rebreak_confirmed']) if filled else False,
                         't10_after_fill':bool(base['t10_reached']) if filled else False,
                         'high_failure_after_fill':bool(base['high_failure']) if filled else False,
                         'unresolved_after_fill':bool(base['unresolved']) if filled else False})
    d=pd.DataFrame(rows)
    assert len(d)==len(src)*len(GATES)
    return d


def metrics(g):
    source_n=len(g); gp=g[g.gate_pass].copy(); pass_n=len(gp); z=g[g.filled].copy(); fills=len(z)
    rb=int(z.rebreak_after_fill.sum()) if fills else 0
    t10=int(z.t10_after_fill.sum()) if fills else 0
    hf=int(z.high_failure_after_fill.sum()) if fills else 0
    un=int(z.unresolved_after_fill.sum()) if fills else 0
    return {'source_n':int(source_n),'gate_pass_n':int(pass_n),'gate_pass_rate':pass_n/source_n if source_n else np.nan,
            'fills_n':int(fills),'fill_rate_gatepass':fills/pass_n if pass_n else np.nan,
            'rebreak_n':rb,'rebreak_rate_fill':rb/fills if fills else np.nan,
            't10_n':t10,'t10_rate_fill':t10/fills if fills else np.nan,'t10_yield_source':t10/source_n if source_n else np.nan,
            'high_failure_n':hf,'high_failure_rate_fill':hf/fills if fills else np.nan,
            'unresolved_n':un,'unresolved_rate_fill':un/fills if fills else np.nan,
            'median_reclaim_fill_min':float(z.minutes_reclaim_to_fill.median()) if fills else np.nan,
            'median_fill_rebreak_min':float(z.loc[z.rebreak_after_fill,'minutes_fill_to_rebreak'].median()) if rb else np.nan,
            'median_fill_t10_min':float(z.loc[z.t10_after_fill,'minutes_fill_to_t10'].median()) if t10 else np.nan}


def summarize(d):
    rows=[]
    for gate in GATES:
        z=d[d.gate.eq(gate)]
        for p in MAJOR: rows.append({'gate':gate,'scope':'PARTITION','name':p,**metrics(z[z.partition.eq(p)])})
        rows.append({'gate':gate,'scope':'POOL','name':'POOLED_REUSED_EXTVAL',**metrics(z[z.partition.isin(REUSED)])})
        rows.append({'gate':gate,'scope':'POOL','name':'POOLED_MAJOR',**metrics(z)})
        for p in MAJOR:
            for cb in CLOCKS:
                rows.append({'gate':gate,'scope':'CLOCK_'+p.upper(),'name':cb,**metrics(z[z.partition.eq(p)&z.clock_block.eq(cb)])})
        for cb in CLOCKS:
            rows.append({'gate':gate,'scope':'CLOCK_REUSED','name':cb,**metrics(z[z.partition.isin(REUSED)&z.clock_block.eq(cb)])})
    return pd.DataFrame(rows)


def row(s,gate,scope,name):
    q=s[(s.gate.eq(gate))&(s.scope.eq(scope))&(s.name.eq(name))]
    assert len(q)==1,(gate,scope,name,len(q))
    return q.iloc[0]


def safe(v,default=-math.inf):
    return default if pd.isna(v) else float(v)


def select_map(s):
    rows=[]
    for cb in CLOCKS:
        b=row(s,'BASE','CLOCK_DEVELOPMENT',cb); bf=int(b.fills_n)
        br=safe(b.t10_rate_fill); bh=safe(b.high_failure_rate_fill,default=math.inf)
        candidates=[]
        for gate in GATES[1:]:
            r=row(s,gate,'CLOCK_DEVELOPMENT',cb)
            retain=int(r.fills_n)/bf if bf else 0.0
            elig=bool(int(r.fills_n)>=20 and retain>=.50-1e-12 and safe(r.t10_rate_fill)>=br+.05-1e-12 and safe(r.high_failure_rate_fill,math.inf)<=bh+1e-12)
            if elig:
                candidates.append((safe(r.t10_rate_fill),safe(r.t10_yield_source),retain,-TIE_ORDER[gate],gate))
        sel=max(candidates)[-1] if candidates else 'BASE'
        dr=row(s,sel,'CLOCK_DEVELOPMENT',cb)
        ext=row(s,sel,'CLOCK_EXTERNAL',cb); val=row(s,sel,'CLOCK_REFERENCE_VALIDATION',cb)
        extb=row(s,'BASE','CLOCK_EXTERNAL',cb); valb=row(s,'BASE','CLOCK_REFERENCE_VALIDATION',cb)
        alt=sel!='BASE'
        extretain=int(ext.fills_n)/int(extb.fills_n) if int(extb.fills_n) else 0.0
        valretain=int(val.fills_n)/int(valb.fills_n) if int(valb.fills_n) else 0.0
        confirmed=bool(alt and int(ext.fills_n)>=10 and int(val.fills_n)>=10 and extretain>=.40-1e-12 and valretain>=.40-1e-12 and
                       safe(ext.t10_rate_fill)>=safe(extb.t10_rate_fill)-1e-12 and safe(val.t10_rate_fill)>=safe(valb.t10_rate_fill)-1e-12 and
                       safe(ext.high_failure_rate_fill,math.inf)<=safe(extb.high_failure_rate_fill,math.inf)+1e-12 and
                       safe(val.high_failure_rate_fill,math.inf)<=safe(valb.high_failure_rate_fill,math.inf)+1e-12)
        rows.append({'clock_block':cb,'wib':WIB[cb],'selected_gate':sel,'alternate':alt,'reused_confirmed':confirmed,
                     'dev_base_fills':int(b.fills_n),'dev_selected_fills':int(dr.fills_n),
                     'dev_base_t10_fill':safe(b.t10_rate_fill),'dev_selected_t10_fill':safe(dr.t10_rate_fill),
                     'dev_base_high_fail':safe(b.high_failure_rate_fill),'dev_selected_high_fail':safe(dr.high_failure_rate_fill),
                     'ext_base_t10_fill':safe(extb.t10_rate_fill),'ext_selected_t10_fill':safe(ext.t10_rate_fill),
                     'val_base_t10_fill':safe(valb.t10_rate_fill),'val_selected_t10_fill':safe(val.t10_rate_fill)})
    return pd.DataFrame(rows)


def selected_data(d,m):
    pieces=[]
    for rr in m.itertuples(index=False):
        pieces.append(d[d.clock_block.eq(rr.clock_block)&d.gate.eq(rr.selected_gate)].copy())
    q=pd.concat(pieces,ignore_index=True)
    assert len(q)==729
    return q


def pct(v): return '-' if pd.isna(v) or not np.isfinite(v) else f'{100*float(v):.1f}%'
def mins(v): return '-' if pd.isna(v) else f'{float(v):.1f}m'


def main():
    src=load_source(); x5,cov=b21.load5(); assert len(x5)==698112 and abs(float(cov)-1)<1e-12
    d=build_detail(x5,src); d.to_csv(OUT_DETAIL,index=False)
    s=summarize(d)
    # Retained fills relative to matching BASE row.
    retains=[]
    for rr in s.itertuples(index=False):
        b=row(s,'BASE',rr.scope,rr.name)
        retains.append(int(rr.fills_n)/int(b.fills_n) if int(b.fills_n) else np.nan)
    s['retained_fills_vs_base']=retains
    s.to_csv(OUT_SUM,index=False)
    m=select_map(s); m.to_csv(OUT_MAP,index=False)
    sd=selected_data(d,m); base=d[d.gate.eq('BASE')].copy(); assert len(base)==729

    mapmet={p:metrics(sd[sd.partition.eq(p)]) for p in MAJOR}; mapmet['POOLED_MAJOR']=metrics(sd)
    basemet={p:metrics(base[base.partition.eq(p)]) for p in MAJOR}; basemet['POOLED_MAJOR']=metrics(base)
    alt_n=int(m.alternate.sum()); conf_n=int(m.reused_confirmed.sum())
    dev_improve=safe(mapmet['development']['t10_rate_fill'])>=safe(basemet['development']['t10_rate_fill'])+.05-1e-12
    major_improve=safe(mapmet['POOLED_MAJOR']['t10_rate_fill'])>safe(basemet['POOLED_MAJOR']['t10_rate_fill'])+1e-12
    retain_major=mapmet['POOLED_MAJOR']['fills_n']/basemet['POOLED_MAJOR']['fills_n'] if basemet['POOLED_MAJOR']['fills_n'] else 0.0
    high_ok=safe(mapmet['POOLED_MAJOR']['high_failure_rate_fill'],math.inf)<=safe(basemet['POOLED_MAJOR']['high_failure_rate_fill'],math.inf)+1e-12
    verdict='B27CQ_CLOCK_CONFIRM_REUSED_CANDIDATE' if (alt_n>=2 and conf_n>=int(np.ceil(alt_n/2)) and dev_improve and major_improve and retain_major>=.60-1e-12 and high_ok) else 'B27CQ_CLOCK_CONFIRM_NOT_SUPPORTED'
    OUT_STATUS.write_text(verdict+'\n')

    # Exact B27CP BASE audit.
    expfills={'external':183,'development':297,'reference_validation':173}
    for p,n in expfills.items(): assert basemet[p]['fills_n']==n,(p,basemet[p]['fills_n'],n)
    assert basemet['POOLED_MAJOR']['fills_n']==653
    OUT_AUDIT.write_text(
        f'audit=PASS\nraw_rows={len(x5)}\ncoverage={float(cov)}\nsource_major={len(src)}\ngates={len(GATES)}\nrows={len(d)}\n'
        f'base_fills_external={basemet["external"]["fills_n"]}\nbase_fills_development={basemet["development"]["fills_n"]}\n'
        f'base_fills_validation={basemet["reference_validation"]["fills_n"]}\nbase_fills_major={basemet["POOLED_MAJOR"]["fills_n"]}\n'
        'base_b27cp_reproduced=TRUE\nuntouched_holdout=NONE\n')

    lines=['# B27CQ — BTC 24H Clock-Specific F05 Confirmation Anatomy — Result','',
           f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
           '**Audit status: PASS.** Exact B27CP F05 baseline reproduced: external 183 / development 297 / validation 173 / major 653 fills.','',
           '**Anatomy only:** trading WR/PF/expectancy/PnL are **N/A**. External/reference_validation are reused-data confirmation, not untouched OOS.','',
           'Frozen F05 confirmation candidates: BASE / WEAK_C05 / WEAK_C10 / NOT_STRONG_BODY / QUICK_RECLAIM / TIME_LEFT_120. Structural objective remains causal T10 with the frozen +4h horizon.','',
           '## Six clocks — development selection first','',
           '| UTC / WIB | Gate | Source | Pass | Fills | Retain | T10/fill | T10 yield/source | High fail/fill | Unresolved/fill | Fill→T10 | Selected |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for cb in CLOCKS:
        sel=str(m.loc[m.clock_block.eq(cb),'selected_gate'].iloc[0])
        for gate in GATES:
            r=row(s,gate,'CLOCK_DEVELOPMENT',cb)
            lines.append(f'| {cb} / {WIB[cb]} | {gate} | {int(r.source_n)} | {int(r.gate_pass_n)} | {int(r.fills_n)} | {pct(r.retained_fills_vs_base)} | **{pct(r.t10_rate_fill)}** | {pct(r.t10_yield_source)} | {pct(r.high_failure_rate_fill)} | {pct(r.unresolved_rate_fill)} | {mins(r.median_fill_t10_min)} | {"**YES**" if gate==sel else ""} |')

    lines += ['', '## Frozen clock-confirmation map + reused confirmation','',
              '| UTC / WIB | Selected gate | Dev fills | Dev BASE→selected T10/fill | Dev High fail BASE→selected | External BASE→selected T10/fill | Validation BASE→selected T10/fill | Reused confirmed |',
              '|---|---|---:|---:|---:|---:|---:|---|']
    for rr in m.itertuples(index=False):
        lines.append(f'| {rr.clock_block} / {rr.wib} | **{rr.selected_gate}** | {rr.dev_selected_fills}/{rr.dev_base_fills} | {pct(rr.dev_base_t10_fill)} → **{pct(rr.dev_selected_t10_fill)}** | {pct(rr.dev_base_high_fail)} → {pct(rr.dev_selected_high_fail)} | {pct(rr.ext_base_t10_fill)} → **{pct(rr.ext_selected_t10_fill)}** | {pct(rr.val_base_t10_fill)} → **{pct(rr.val_selected_t10_fill)}** | {"YES" if rr.reused_confirmed else "NO"} |')

    lines += ['', '## Selected map vs universal BASE F05','',
              '| Scope | Source | BASE fills | Map fills | Retain | BASE T10/fill | Map T10/fill | BASE T10 yield/source | Map T10 yield/source | BASE High fail/fill | Map High fail/fill |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for p in (*MAJOR,'POOLED_MAJOR'):
        b=basemet[p]; a=mapmet[p]; retain=a['fills_n']/b['fills_n'] if b['fills_n'] else np.nan
        lines.append(f'| {p} | {a["source_n"]} | {b["fills_n"]} | {a["fills_n"]} | {pct(retain)} | {pct(b["t10_rate_fill"])} | **{pct(a["t10_rate_fill"])}** | {pct(b["t10_yield_source"])} | {pct(a["t10_yield_source"])} | {pct(b["high_failure_rate_fill"])} | {pct(a["high_failure_rate_fill"])} |')

    lines += ['', f'Non-BASE gates selected in **{alt_n}/6** clocks; reused-confirmed **{conf_n}/{alt_n if alt_n else 0}**.',
              '', f'**Frozen verdict: `{verdict}`.**','',
              'This is not a trading-WR result. No SL economics were optimized. Any economic follow-up must be separately preregistered with RR >=1:1; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); print('\n'.join(lines))

if __name__=='__main__': main()
