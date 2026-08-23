#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/'BTC_24H_4H_REGIME_SHORT_ATLAS_B27BE_Detail.csv'
OUT_MD=ROOT/'BTC_24H_PREBREAK_RETEST_LADDER_B27CA_Result.md'
OUT_EV=ROOT/'BTC_24H_PREBREAK_RETEST_LADDER_B27CA_Events.csv'
OUT_CAND=ROOT/'BTC_24H_PREBREAK_RETEST_LADDER_B27CA_Candidates.csv'
OUT_ANAT=ROOT/'BTC_24H_PREBREAK_RETEST_LADDER_B27CA_Anatomy.csv'
OUT_SEL=ROOT/'BTC_24H_PREBREAK_RETEST_LADDER_B27CA_Selection.csv'
OUT_STATUS=ROOT/'BTC_24H_PREBREAK_RETEST_LADDER_B27CA_Status.txt'
BAR5=pd.Timedelta(minutes=5)
MAJOR=('external','development','reference_validation')
OOS=('external','reference_validation')
REGIMES=('BULL','BEAR','SIDEWAYS')
CLOCKS=('00-04','04-08','08-12','12-16','16-20','20-00')
FRACS=(0.05,0.10,0.15,0.20,0.25)


def as_bool(s):
    return s if s.dtype==bool else s.astype(str).str.lower().eq('true')

def fast_slice(x5,start,end):
    a=int(x5.index.searchsorted(start,'left')); b=int(x5.index.searchsorted(end,'left'))
    return x5.iloc[a:b]

def low_touch(b,L):
    return float(b.low)<=L and float(b.close)>=L

def load_source():
    d=pd.read_csv(SRC); d['k1_opp0']=as_bool(d.k1_opp0)
    for c in ('obs_start','obs_end','k1_ts','regime_available_ts'):
        d[c]=pd.to_datetime(d[c],utc=True,errors='coerce')
    q=d[d.partition.isin(MAJOR)&d.k1_opp0].copy()
    exp={'external':862,'development':1264,'reference_validation':641}
    assert len(q)==2767
    for p,n in exp.items(): assert len(q[q.partition==p])==n
    assert len(q[q.regime=='BULL'])==1146 and len(q[q.regime=='BEAR'])==1122 and len(q[q.regime=='SIDEWAYS'])==499
    return q.sort_values(['partition','obs_start']).reset_index(drop=True)

def eval_event(x5,r):
    start=pd.Timestamp(r.obs_start); end=pd.Timestamp(r.obs_end); H=float(r.H); L=float(r.L); R=H-L
    q=fast_slice(x5,start,end); assert len(q)==48 and q.index[0]==start and q.index[-1]==end-BAR5
    k1_start=pd.Timestamp(r.k1_ts)-BAR5
    pos=int(q.index.searchsorted(k1_start,'left')); assert pos<len(q) and q.index[pos]==k1_start and low_touch(q.iloc[pos],L)

    visits=[]; touching=False; break_side='NONE'; break_idx=None
    for i in range(pos,len(q)):
        b=q.iloc[i]; c=float(b.close)
        if c<L: break_side='LOW'; break_idx=i; break
        if c>H: break_side='HIGH'; break_idx=i; break
        hit=low_touch(b,L)
        if hit and not touching: visits.append(i)
        touching=hit
    src_vis=int(pd.to_numeric(pd.Series([r.low_visits]),errors='raise').iloc[0])
    assert len(visits)==src_vis, (start,len(visits),src_vis)
    src_side=str(r.breakout_side) if pd.notna(r.breakout_side) else ''
    if break_side=='NONE': assert src_side in ('','None','nan')
    else: assert src_side==break_side

    l2_idx=visits[1] if len(visits)>=2 else None
    low_break=break_side=='LOW'
    low_break_after_l2=bool(low_break and l2_idx is not None and break_idx>l2_idx)

    # consume K1 episode then establish causal leave
    j=pos
    while j<len(q) and low_touch(q.iloc[j],L): j+=1
    clean=False; leave_idx=None; eligible_idx=None
    if j<len(q):
        c=float(q.iloc[j].close)
        if c>=L and c<=H and not low_touch(q.iloc[j],L):
            clean=True; leave_idx=j; eligible_idx=j+1
    terminal_idx=len(q)
    first_return_type='BLOCK_END'
    if clean and eligible_idx<len(q):
        # first later L interaction or boundary break
        for i in range(eligible_idx,len(q)):
            b=q.iloc[i]; c=float(b.close)
            if c<L:
                terminal_idx=i; first_return_type='BREAK_BEFORE_GENUINE_L2'; break
            if c>H:
                terminal_idx=i; first_return_type='OPPOSITE_HIGH_BREAK'; break
            if low_touch(b,L):
                terminal_idx=i; first_return_type='GENUINE_L2'; break
    else:
        terminal_idx=len(q)

    base={'partition':str(r.partition),'regime':str(r.regime),'clock_block':str(r.clock_block),'obs_start':start,'obs_end':end,
          'H':H,'L':L,'range':R,'k1_start':k1_start,'k1_complete':pd.Timestamp(r.k1_ts),
          'low_visits_before_terminal':len(visits),'low_break':low_break,'break_side':break_side,
          'break_ts':(q.index[break_idx]+BAR5 if break_idx is not None else pd.NaT),
          'genuine_l2':l2_idx is not None,'l2_ts':(q.index[l2_idx] if l2_idx is not None else pd.NaT),
          'low_break_after_l2':low_break_after_l2,'clean_leave':clean,
          'leave_complete':(q.index[leave_idx]+BAR5 if leave_idx is not None else pd.NaT),
          'eligible_start':(q.index[eligible_idx] if eligible_idx is not None and eligible_idx<len(q) else pd.NaT),
          'first_return_type':first_return_type,'first_return_ts':(q.index[terminal_idx] if terminal_idx<len(q) else pd.NaT)}
    cands=[]
    for f in FRACS:
        px=L+f*R; fill_idx=None
        if clean and eligible_idx is not None and eligible_idx<terminal_idx:
            for i in range(eligible_idx,terminal_idx):
                b=q.iloc[i]
                if float(b.low)<=px<=float(b.high): fill_idx=i; break
        filled=fill_idx is not None
        # eventual low break after fill = source first LOW boundary break later than fill
        eventual=bool(filled and low_break and break_idx is not None and break_idx>fill_idx)
        break_before_l2=bool(filled and first_return_type=='BREAK_BEFORE_GENUINE_L2')
        genuine_after_fill=bool(filled and l2_idx is not None and fill_idx<l2_idx)
        break_after_l2=bool(genuine_after_fill and low_break_after_l2)
        outcome='NO_FILL'
        if filled:
            if break_before_l2: outcome='BREAK_BEFORE_GENUINE_L2'
            elif genuine_after_fill and break_after_l2: outcome='GENUINE_L2_THEN_BREAK'
            elif genuine_after_fill: outcome='GENUINE_L2_NO_BREAK'
            else: outcome='NO_L_RETURN_OR_OPPOSITE'
        cands.append({**{k:base[k] for k in ('partition','regime','clock_block','obs_start','H','L','range')},
                      'fraction':f,'label':f'F{int(round(f*100)):02d}','price':px,'clean_leave':clean,
                      'filled':filled,'fill_ts':(q.index[fill_idx] if filled else pd.NaT),
                      'break_before_genuine_l2':break_before_l2,'genuine_l2_after_fill':genuine_after_fill,
                      'low_break_after_l2':break_after_l2,'eventual_low_break_after_fill':eventual,'outcome':outcome})
    return base,cands

def anatomy_metrics(g):
    lb=g[g.low_break]
    def nvis(n): return int((lb.low_visits_before_terminal==n).sum())
    fourp=int((lb.low_visits_before_terminal>=4).sum())
    l2=g[g.genuine_l2]
    return {'k1_n':len(g),'low_break_n':len(lb),'low_break_rate':len(lb)/len(g) if len(g) else np.nan,
            'break_after1_n':nvis(1),'break_after2_n':nvis(2),'break_after3_n':nvis(3),'break_after4p_n':fourp,
            'break_after1_share':nvis(1)/len(lb) if len(lb) else np.nan,'break_after2_share':nvis(2)/len(lb) if len(lb) else np.nan,
            'break_after3_share':nvis(3)/len(lb) if len(lb) else np.nan,'break_after4p_share':fourp/len(lb) if len(lb) else np.nan,
            'genuine_l2_n':len(l2),'low_break_after_l2_n':int(l2.low_break_after_l2.sum()),
            'low_break_after_l2_rate':float(l2.low_break_after_l2.mean()) if len(l2) else np.nan}
def cand_metrics(g):
    clean=g[g.clean_leave]; fills=g[g.filled]; l2=fills[fills.genuine_l2_after_fill]
    return {'rows':len(g),'clean_n':len(clean),'fill_n':len(fills),'fill_clean_rate':len(fills)/len(clean) if len(clean) else np.nan,
            'break_before_l2_n':int(fills.break_before_genuine_l2.sum()),'break_before_l2_rate':float(fills.break_before_genuine_l2.mean()) if len(fills) else np.nan,
            'genuine_l2_n':len(l2),'genuine_l2_rate':len(l2)/len(fills) if len(fills) else np.nan,
            'break_after_l2_n':int(l2.low_break_after_l2.sum()),'break_after_l2_rate':float(l2.low_break_after_l2.mean()) if len(l2) else np.nan,
            'eventual_break_n':int(fills.eventual_low_break_after_fill.sum()),
            'eventual_break_rate':float(fills.eventual_low_break_after_fill.mean()) if len(fills) else np.nan}
def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'

def main():
    src=load_source(); x5,cov=b21.load5(); assert len(x5)==698112 and abs(float(cov)-1)<1e-12
    ev=[]; cand=[]
    for r in src.itertuples(index=False):
        e,c=eval_event(x5,r); ev.append(e); cand.extend(c)
    e=pd.DataFrame(ev); c=pd.DataFrame(cand)
    assert len(e)==2767 and len(c)==2767*5
    # F15 fill identities must reproduce B27BY.
    f15=c[c.label=='F15']
    for p,n in {'external':441,'development':589,'reference_validation':228}.items(): assert int(f15[(f15.partition==p)&f15.filled].shape[0])==n
    e.to_csv(OUT_EV,index=False); c.to_csv(OUT_CAND,index=False)

    ar=[]
    for p in MAJOR: ar.append({'scope':'PARTITION','name':p,**anatomy_metrics(e[e.partition==p])})
    pm=e[e.partition.isin(MAJOR)]
    for rg in REGIMES: ar.append({'scope':'REGIME','name':rg,**anatomy_metrics(pm[pm.regime==rg])})
    for cb in CLOCKS: ar.append({'scope':'CLOCK','name':cb,**anatomy_metrics(pm[pm.clock_block==cb])})
    a=pd.DataFrame(ar); a.to_csv(OUT_ANAT,index=False)

    # development selection per clock
    sel=[]; chosen={}
    for cb in CLOCKS:
        rows=[]
        for f in FRACS:
            g=c[(c.partition=='development')&(c.clock_block==cb)&(c.fraction==f)]
            m=cand_metrics(g); rows.append((f,m))
        elig=[x for x in rows if x[1]['fill_n']>=20]
        assert elig, cb
        elig.sort(key=lambda x:(-(x[1]['eventual_break_rate'] if pd.notna(x[1]['eventual_break_rate']) else -1),
                                -(x[1]['genuine_l2_rate'] if pd.notna(x[1]['genuine_l2_rate']) else -1),
                                -x[1]['fill_n'],abs(x[0]-.15),x[0]))
        f,m=elig[0]; chosen[cb]=f
        sel.append({'clock_block':cb,'selected_fraction':f,'selected_label':f'F{int(round(f*100)):02d}',
                    'dev_fill_n':m['fill_n'],'dev_eventual_break_rate':m['eventual_break_rate'],'dev_genuine_l2_rate':m['genuine_l2_rate']})
    s=pd.DataFrame(sel)
    for part in ('external','reference_validation'):
        vals=[]
        for _,r in s.iterrows():
            g=c[(c.partition==part)&(c.clock_block==r.clock_block)&(c.fraction==r.selected_fraction)]
            m=cand_metrics(g); vals.append((m['fill_n'],m['eventual_break_rate']))
        s[f'{part}_fill_n']=[v[0] for v in vals]; s[f'{part}_eventual_break_rate']=[v[1] for v in vals]
    s.to_csv(OUT_SEL,index=False)

    def adaptive_rows(parts):
        z=[]
        for cb,f in chosen.items(): z.append(c[c.partition.isin(parts)&(c.clock_block==cb)&(c.fraction==f)])
        return pd.concat(z,ignore_index=True)
    comp=[]
    for name,parts in [('external',('external',)),('reference_validation',('reference_validation',)),('POOLED_OOS',OOS)]:
        ad=cand_metrics(adaptive_rows(parts)); fx=cand_metrics(c[c.partition.isin(parts)&(c.fraction==.15)])
        comp.append({'name':name,'adaptive_fill_n':ad['fill_n'],'adaptive_break_rate':ad['eventual_break_rate'],
                     'fixed_f15_fill_n':fx['fill_n'],'fixed_f15_break_rate':fx['eventual_break_rate'],
                     'lift':ad['eventual_break_rate']-fx['eventual_break_rate']})
    comp=pd.DataFrame(comp)
    ext=comp[comp.name=='external'].iloc[0]; val=comp[comp.name=='reference_validation'].iloc[0]; po=comp[comp.name=='POOLED_OOS'].iloc[0]
    supported=(ext.adaptive_fill_n>=100 and val.adaptive_fill_n>=60 and ext.adaptive_break_rate>=ext.fixed_f15_break_rate and
               val.adaptive_break_rate>=val.fixed_f15_break_rate and po.lift>=.03)
    verdict='B27CA_CLOCK_ADAPTIVE_CANDIDATE_SUPPORTED' if supported else 'B27CA_CLOCK_ADAPTIVE_NOT_SUPPORTED'
    OUT_STATUS.write_text(verdict+'\n')

    lines=['# B27CA — BTC 24H Pre-Break Retest Ladder + Adaptive Pre-L2 SHORT — Result','',
           f'5m rows: **{len(x5):,}**; coverage: **{100*float(cov):.4f}%**.','',
           '**Audit status: PASS.** Structural anatomy only; no trading WR, PF, PnL, stop, TP, RR, fee, or live change.','',
           '## Retest ladder by clock — pooled major','',
           '| UTC block | K1 | Low break | Break after 1 visit | after 2 | after 3 | after 4+ | Genuine L2 | Break after L2 |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for cb in CLOCKS:
        r=a[(a.scope=='CLOCK')&(a.name==cb)].iloc[0]
        lines.append(f'| {cb} | {int(r.k1_n)} | {pct(r.low_break_rate)} | {pct(r.break_after1_share)} | {pct(r.break_after2_share)} | {pct(r.break_after3_share)} | {pct(r.break_after4p_share)} | {int(r.genuine_l2_n)} | {pct(r.low_break_after_l2_rate)} |')
    lines += ['', '## Fixed F15 — major partitions','',
              '| Partition | Fills | Break before genuine L2 | Genuine L2 | Break after L2 | Eventual Low break after fill |',
              '|---|---:|---:|---:|---:|---:|']
    for p in MAJOR:
        m=cand_metrics(c[(c.partition==p)&(c.fraction==.15)])
        lines.append(f'| {p} | {m["fill_n"]} | {pct(m["break_before_l2_rate"])} | {pct(m["genuine_l2_rate"])} | {pct(m["break_after_l2_rate"])} | {pct(m["eventual_break_rate"])} |')
    lines += ['', '## Fixed F15 by clock — pooled major','',
              '| UTC block | Fills | Break before L2 | Genuine L2 | Break after L2 | Eventual break/fill |',
              '|---|---:|---:|---:|---:|---:|']
    for cb in CLOCKS:
        m=cand_metrics(c[(c.partition.isin(MAJOR))&(c.clock_block==cb)&(c.fraction==.15)])
        lines.append(f'| {cb} | {m["fill_n"]} | {pct(m["break_before_l2_rate"])} | {pct(m["genuine_l2_rate"])} | {pct(m["break_after_l2_rate"])} | {pct(m["eventual_break_rate"])} |')
    lines += ['', '## Development-selected fraction per clock + untouched OOS readout','',
              '| UTC block | Selected | Dev fills | Dev break/fill | External fills | External break/fill | Validation fills | Validation break/fill |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in s.iterrows():
        lines.append(f'| {r.clock_block} | {r.selected_label} | {int(r.dev_fill_n)} | {pct(r.dev_eventual_break_rate)} | {int(r.external_fill_n)} | {pct(r.external_eventual_break_rate)} | {int(r.reference_validation_fill_n)} | {pct(r.reference_validation_eventual_break_rate)} |')
    lines += ['', '## Adaptive vs fixed F15 — OOS aggregates','',
              '| Scope | Adaptive fills | Adaptive break/fill | Fixed F15 fills | Fixed F15 break/fill | Lift |',
              '|---|---:|---:|---:|---:|---:|']
    for _,r in comp.iterrows(): lines.append(f'| {r["name"]} | {int(r.adaptive_fill_n)} | {pct(r.adaptive_break_rate)} | {int(r.fixed_f15_fill_n)} | {pct(r.fixed_f15_break_rate)} | {100*r.lift:+.1f}pp |')
    lines += ['', f'**Frozen verdict: `{verdict}`.**','',
              'B27CA separates retest-count anatomy from pre-return entry geometry. Any supported structural candidate still requires a separately preregistered economic backtest.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); print('\n'.join(lines))

if __name__=='__main__': main()
