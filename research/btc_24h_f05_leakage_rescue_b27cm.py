#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'BTC_24H_F05_STATE_MACHINE_B27CL_Trades.csv'
OUT_MD = ROOT / 'BTC_24H_F05_LEAKAGE_RESCUE_B27CM_Result.md'
OUT_DETAIL = ROOT / 'BTC_24H_F05_LEAKAGE_RESCUE_B27CM_Detail.csv'
OUT_CAND = ROOT / 'BTC_24H_F05_LEAKAGE_RESCUE_B27CM_Candidates.csv'
OUT_STATUS = ROOT / 'BTC_24H_F05_LEAKAGE_RESCUE_B27CM_Status.txt'
OUT_AUDIT = ROOT / 'BTC_24H_F05_LEAKAGE_RESCUE_B27CM_Audit.txt'

BAR5 = pd.Timedelta(minutes=5)
BREATH = pd.Timedelta(hours=4)
MAJOR = ('external','development','reference_validation')
OOS = ('external','reference_validation')
CLOCKS = ('00-04','04-08','08-12','12-16','16-20','20-00')
WIB = {'00-04':'07-11','04-08':'11-15','08-12':'15-19','12-16':'19-23','16-20':'23-03','20-00':'03-07'}
CANDIDATES = ('REBREAK_AT_EXIT','T5_AT_EXIT','FAST_L_TOUCH_10M','NO_F25_CLOSE_BEFORE_EXIT','LAST_CLOSE_LE_F05')


def as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.copy()
    return s.astype(str).str.lower().eq('true')


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def load_source() -> pd.DataFrame:
    d = pd.read_csv(SRC)
    for c in ('obs_start','obs_end','reclaim_complete_ts','fill_ts','rebreak_complete_ts','exit_ts'):
        d[c] = pd.to_datetime(d[c], utc=True, errors='coerce')
    for c in ('filled','l_touch_after_fill','rebreak_confirmed','t5_reached','t75_reached','t10_reached'):
        d[c] = as_bool(d[c])
    q = d[d.partition.isin(MAJOR) & d.filled].copy()
    exp_fills={'external':183,'development':297,'reference_validation':172}
    for p,n in exp_fills.items():
        assert len(q[q.partition.eq(p)])==n,(p,len(q[q.partition.eq(p)]),n)
    assert len(q)==652
    assert len(q[q.partition.isin(OOS)])==355

    q['leak_type']='OTHER'
    q.loc[q.exit_ceiling_kind.eq('BE'),'leak_type']='BE'
    q.loc[q.exit_ceiling_kind.eq('TIME') & ~q.t10_reached,'leak_type']='TIME_OTHER'

    exp_be={'external':67,'development':107,'reference_validation':61}
    exp_time={'external':37,'development':55,'reference_validation':39}
    for p,n in exp_be.items(): assert len(q[(q.partition.eq(p))&(q.leak_type.eq('BE'))])==n
    for p,n in exp_time.items(): assert len(q[(q.partition.eq(p))&(q.leak_type.eq('TIME_OTHER'))])==n
    leak=q[q.leak_type.isin(('BE','TIME_OTHER'))].copy()
    assert len(leak)==366
    assert len(leak[leak.partition.isin(OOS)])==204
    return leak.sort_values(['partition','exit_ts','obs_start']).reset_index(drop=True)


def signal_state(x5: pd.DataFrame, r) -> dict:
    fill=pd.Timestamp(r.fill_ts); ex=pd.Timestamp(r.exit_ts)
    L=float(r.L); R4=float(r.R4); F05=float(r.F05); F25=L+.25*R4

    # The close of an intrabar stop bar was not known when the stop fired.
    if str(r.exit_reason)=='CEILING_STOP':
        decision_bar_start=ex-BAR5
    else:
        decision_bar_start=ex
    pre=fast_slice(x5,fill,decision_bar_start)

    post_fill=pre[pre.index>fill]
    touches=post_fill[post_fill.low.astype(float)<=L]
    if len(touches):
        first_touch=touches.index[0]
        fast_touch=((first_touch-fill)/pd.Timedelta(minutes=1))<=10.0
        first_touch_min=float((first_touch-fill)/pd.Timedelta(minutes=1))
    else:
        fast_touch=False; first_touch_min=np.nan

    no_f25=bool(len(pre)==0 or not (pre.close.astype(float)>=F25).any())
    last_le=bool(len(pre)>0 and float(pre.iloc[-1].close)<=F05)
    return {
        'REBREAK_AT_EXIT':bool(r.rebreak_confirmed),
        'T5_AT_EXIT':bool(r.t5_reached),
        'FAST_L_TOUCH_10M':bool(fast_touch),
        'NO_F25_CLOSE_BEFORE_EXIT':bool(no_f25),
        'LAST_CLOSE_LE_F05':bool(last_le),
        'first_l_touch_min':first_touch_min,
    }


def counterfactual(x5: pd.DataFrame, r) -> dict:
    ex=pd.Timestamp(r.exit_ts); end=ex+BREATH
    H=float(r.H); L=float(r.L); T5=float(r.T5); T10=float(r.T10)
    q=fast_slice(x5,ex,end)

    carried=bool(r.rebreak_confirmed)
    state=carried
    fresh=False
    rebreak_ts=ex if carried else pd.NaT
    t5=False; t10=False; high_break=False
    t5_ts=pd.NaT; t10_ts=pd.NaT; high_ts=pd.NaT

    for ts,b in q.iterrows():
        lo=float(b.low); c=float(b.close)
        if not state:
            if c>H:
                high_break=True; high_ts=ts+BAR5; break
            if c<L:
                state=True; fresh=True; rebreak_ts=ts+BAR5
            continue

        # Carried state may scan from the first available bar. Fresh rebreak scans only next bar.
        if fresh and ts < rebreak_ts:
            continue

        if (not t5) and lo<=T5:
            t5=True; t5_ts=ts
        if (not t10) and lo<=T10:
            t5=True; t10=True; t10_ts=ts
        # High invalidation is knowable only at completed close, so same-bar favorable touch counts.
        if c>H:
            high_break=True; high_ts=ts+BAR5
            break
        if t10:
            break

    available=bool(carried or fresh)
    no_resolution=bool((not t10) and (not high_break))
    def mins(ts):
        return np.nan if pd.isna(ts) else float((pd.Timestamp(ts)-ex)/pd.Timedelta(minutes=1))
    return {
        'carried_rebreak_at_exit':carried,
        'fresh_rebreak_after_exit':fresh,
        'rebreak_available':available,
        'rebreak_available_min':0.0 if carried else mins(rebreak_ts),
        'future_t5':t5,'future_t5_min':mins(t5_ts),
        'future_t10':t10,'future_t10_min':mins(t10_ts),
        'future_high_break':high_break,'future_high_break_min':mins(high_ts),
        'no_resolution_4h':no_resolution,
        'breath_rows':int(len(q)),
    }


def metrics(g: pd.DataFrame) -> dict:
    n=len(g)
    if n==0:
        return {'n':0,'carried_n':0,'fresh_rebreak_n':0,'rebreak_available_n':0,'rebreak_available_rate':np.nan,
                't5_n':0,'t5_rate':np.nan,'t10_n':0,'t10_rate':np.nan,'high_n':0,'high_rate':np.nan,
                'nores_n':0,'nores_rate':np.nan,'med_rebreak_min':np.nan,'med_t5_min':np.nan,'med_t10_min':np.nan}
    return {
        'n':int(n),
        'carried_n':int(g.carried_rebreak_at_exit.sum()),
        'fresh_rebreak_n':int(g.fresh_rebreak_after_exit.sum()),
        'rebreak_available_n':int(g.rebreak_available.sum()),
        'rebreak_available_rate':float(g.rebreak_available.mean()),
        't5_n':int(g.future_t5.sum()),'t5_rate':float(g.future_t5.mean()),
        't10_n':int(g.future_t10.sum()),'t10_rate':float(g.future_t10.mean()),
        'high_n':int(g.future_high_break.sum()),'high_rate':float(g.future_high_break.mean()),
        'nores_n':int(g.no_resolution_4h.sum()),'nores_rate':float(g.no_resolution_4h.mean()),
        'med_rebreak_min':float(g.loc[g.rebreak_available,'rebreak_available_min'].median()) if g.rebreak_available.any() else np.nan,
        'med_t5_min':float(g.loc[g.future_t5,'future_t5_min'].median()) if g.future_t5.any() else np.nan,
        'med_t10_min':float(g.loc[g.future_t10,'future_t10_min'].median()) if g.future_t10.any() else np.nan,
    }


def candidate_rows(d: pd.DataFrame) -> tuple[pd.DataFrame,dict]:
    rows=[]; selected={}
    for leak in ('BE','TIME_OTHER'):
        dev=d[(d.partition.eq('development'))&(d.leak_type.eq(leak))]
        base=float(dev.future_t10.mean())
        min_n=30 if leak=='BE' else 20
        temp=[]
        for order,c in enumerate(CANDIDATES):
            z=dev[dev[c]]
            n=len(z); rate=float(z.future_t10.mean()) if n else np.nan
            uplift=rate-base if n else np.nan
            eligible=bool(n>=min_n and np.isfinite(uplift) and uplift>=.10)
            rec={'leak_type':leak,'candidate':c,'partition':'development','n':int(n),'baseline_t10':base,
                 't10_rate':rate,'uplift':uplift,'eligible_dev':eligible,'order':order}
            rows.append(rec); temp.append(rec)
        elig=[r for r in temp if r['eligible_dev']]
        if elig:
            elig=sorted(elig,key=lambda r:(-r['t10_rate'],-r['n'],r['order']))
            selected[leak]=elig[0]['candidate']
        else:
            selected[leak]='NONE'

    # Append confirmation rows for selected candidates and baselines.
    for leak in ('BE','TIME_OTHER'):
        sel=selected[leak]
        for scope,parts in [('external',('external',)),('reference_validation',('reference_validation',)),('POOLED_OOS',OOS)]:
            baseg=d[d.partition.isin(parts)&d.leak_type.eq(leak)]
            base=float(baseg.future_t10.mean()) if len(baseg) else np.nan
            if sel=='NONE':
                n=0; rate=np.nan; uplift=np.nan
            else:
                z=baseg[baseg[sel]]; n=len(z); rate=float(z.future_t10.mean()) if n else np.nan; uplift=rate-base if n else np.nan
            rows.append({'leak_type':leak,'candidate':sel,'partition':scope,'n':int(n),'baseline_t10':base,
                         't10_rate':rate,'uplift':uplift,'eligible_dev':False,'order':-1})
    return pd.DataFrame(rows),selected


def support_status(cand: pd.DataFrame, selected: dict) -> dict:
    out={}
    for leak in ('BE','TIME_OTHER'):
        sel=selected[leak]
        if sel=='NONE': out[leak]=False; continue
        def row(part):
            z=cand[(cand.leak_type.eq(leak))&(cand.candidate.eq(sel))&(cand.partition.eq(part))]
            assert len(z)==1,(leak,sel,part,len(z)); return z.iloc[0]
        ext=row('external'); val=row('reference_validation'); oos=row('POOLED_OOS')
        out[leak]=bool(int(ext.n)>=10 and int(val.n)>=10 and float(ext.t10_rate)>float(ext.baseline_t10)
                       and float(val.t10_rate)>float(val.baseline_t10) and float(oos.uplift)>=.075)
    return out


def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def num(x): return '-' if pd.isna(x) else f'{float(x):.1f}'


def main() -> None:
    src=load_source()
    x5,cov=b21.load5()
    assert len(x5)==698112 and abs(float(cov)-1.0)<1e-12

    rows=[]
    for r in src.itertuples(index=False):
        sig=signal_state(x5,r); cf=counterfactual(x5,r)
        rows.append({
            'partition':str(r.partition),'regime':str(r.regime),'clock_block':str(r.clock_block),'leak_type':str(r.leak_type),
            'obs_start':pd.Timestamp(r.obs_start),'obs_end':pd.Timestamp(r.obs_end),'fill_ts':pd.Timestamp(r.fill_ts),
            'exit_ts':pd.Timestamp(r.exit_ts),'exit_reason':str(r.exit_reason),'H':float(r.H),'L':float(r.L),'R4':float(r.R4),
            'F05':float(r.F05),'T5':float(r.T5),'T10':float(r.T10),
            **sig,**cf,
        })
    d=pd.DataFrame(rows)
    assert len(d)==366 and len(d[d.partition.isin(OOS)])==204
    d.to_csv(OUT_DETAIL,index=False)

    cand,selected=candidate_rows(d)
    support=support_status(cand,selected)
    cand['selected_dev']=False
    for leak,sel in selected.items():
        if sel!='NONE':
            cand.loc[(cand.leak_type.eq(leak))&(cand.partition.eq('development'))&(cand.candidate.eq(sel)),'selected_dev']=True
    cand.to_csv(OUT_CAND,index=False)

    overall=bool(any(support.values()))
    verdict='B27CM_LEAKAGE_RESCUE_SIGNAL_SUPPORTED' if overall else 'B27CM_LEAKAGE_RESCUE_SIGNAL_NOT_SUPPORTED'
    OUT_STATUS.write_text(verdict+'\n')
    OUT_AUDIT.write_text(
        f'audit=PASS\nrows5={len(x5)}\ncoverage={cov:.8f}\nleak_major={len(d)}\nleak_oos={len(d[d.partition.isin(OOS)])}\n'
        f'be_selected={selected["BE"]}\nbe_supported={support["BE"]}\ntime_selected={selected["TIME_OTHER"]}\ntime_supported={support["TIME_OTHER"]}\n')

    lines=['# B27CM — BTC 24H F05 BE/TIME Leakage Rescue Anatomy — Result','',
           f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
           '**Audit status: PASS.** Exact B27CL filled/leakage identities reproduced. Anatomy/counterfactual only; trading WR/PF/PnL/expectancy are **N/A**.','',
           'Counterfactual breath is frozen at exactly **4 hours after actual B27CL exit**. Existing confirmed-rebreak state is carried forward; otherwise a fresh close <L is required before T5/T10 scanning.','',
           '## Six-clock untouched OOS leakage rescue — first','',
           '| UTC / WIB | BE N | BE -> T10 | TIME N | TIME -> T10 | Combined N | Rebreak available | ->T5 | ->T10 | High break | No resolution |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for cb in CLOCKS:
        z=d[d.partition.isin(OOS)&d.clock_block.eq(cb)]
        be=z[z.leak_type.eq('BE')]; tm=z[z.leak_type.eq('TIME_OTHER')]; m=metrics(z)
        lines.append(f'| {cb} / {WIB[cb]} | {len(be)} | {pct(be.future_t10.mean()) if len(be) else "-"} | {len(tm)} | {pct(tm.future_t10.mean()) if len(tm) else "-"} | {m["n"]} | {pct(m["rebreak_available_rate"])} | {pct(m["t5_rate"])} | {pct(m["t10_rate"])} | {pct(m["high_rate"])} | {pct(m["nores_rate"])} |')

    lines += ['', '## Major partitions / pools by leakage family','',
              '| Scope | Leak | N | Carried rebreak | Fresh rebreak | Rebreak available | Future T5 | Future T10 | Future High break | No resolution | Med exit->T10 |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    scopes=[('external',('external',)),('development',('development',)),('reference_validation',('reference_validation',)),('POOLED_OOS',OOS),('POOLED_MAJOR',MAJOR)]
    for scope,parts in scopes:
        for leak in ('BE','TIME_OTHER','COMBINED'):
            z=d[d.partition.isin(parts)] if leak=='COMBINED' else d[d.partition.isin(parts)&d.leak_type.eq(leak)]
            m=metrics(z)
            lines.append(f'| {scope} | {leak} | {m["n"]} | {m["carried_n"]} | {m["fresh_rebreak_n"]} | {m["rebreak_available_n"]} ({pct(m["rebreak_available_rate"])}) | {m["t5_n"]} ({pct(m["t5_rate"])}) | {m["t10_n"]} ({pct(m["t10_rate"])}) | {m["high_n"]} ({pct(m["high_rate"])}) | {m["nores_n"]} ({pct(m["nores_rate"])}) | {num(m["med_t10_min"])}m |')

    lines += ['', '## Development-only signal selection','',
              '| Leak | Candidate | N | Baseline T10 | Candidate T10 | Uplift | Eligible | Selected |',
              '|---|---|---:|---:|---:|---:|---|---|']
    for leak in ('BE','TIME_OTHER'):
        for c in CANDIDATES:
            r=cand[(cand.leak_type.eq(leak))&(cand.partition.eq('development'))&(cand.candidate.eq(c))].iloc[0]
            lines.append(f'| {leak} | {c} | {int(r.n)} | {pct(r.baseline_t10)} | {pct(r.t10_rate)} | {pct(r.uplift)} | {"YES" if bool(r.eligible_dev) else "NO"} | {"YES" if bool(r.selected_dev) else "NO"} |')

    lines += ['', '## Untouched OOS confirmation of development selection','',
              '| Leak | Selected signal | External N/rate vs base | Validation N/rate vs base | Pooled OOS rate vs base | Supported |',
              '|---|---|---|---|---|---|']
    for leak in ('BE','TIME_OTHER'):
        sel=selected[leak]
        if sel=='NONE':
            lines.append(f'| {leak} | NONE | - | - | - | NO |')
        else:
            vals={}
            for part in ('external','reference_validation','POOLED_OOS'):
                r=cand[(cand.leak_type.eq(leak))&(cand.partition.eq(part))&(cand.candidate.eq(sel))].iloc[0]
                vals[part]=r
            e=vals['external']; v=vals['reference_validation']; o=vals['POOLED_OOS']
            lines.append(f'| {leak} | {sel} | {int(e.n)} / {pct(e.t10_rate)} vs {pct(e.baseline_t10)} | {int(v.n)} / {pct(v.t10_rate)} vs {pct(v.baseline_t10)} | {pct(o.t10_rate)} vs {pct(o.baseline_t10)} ({pct(o.uplift)} uplift) | {"YES" if support[leak] else "NO"} |')

    oos=d[d.partition.isin(OOS)]
    be=oos[oos.leak_type.eq('BE')]; tm=oos[oos.leak_type.eq('TIME_OTHER')]
    original_oos_fills=355
    lines += ['', '## Counterfactual opportunities per 100 original OOS F05 fills','',
              f'- actual B27CL BE leakage: **{100*len(be)/original_oos_fills:.1f} per 100 fills**; of those, **{100*int(be.future_t10.sum())/original_oos_fills:.1f} per 100 original fills** would reach T10 inside the frozen extra-4h counterfactual.','',
              f'- actual B27CL unresolved TIME leakage: **{100*len(tm)/original_oos_fills:.1f} per 100 fills**; of those, **{100*int(tm.future_t10.sum())/original_oos_fills:.1f} per 100 original fills** would reach T10 inside the extra-4h counterfactual.','',
              f'- combined BE+TIME leakage potentially reaching T10 with extra breath: **{100*int(oos.future_t10.sum())/original_oos_fills:.1f} per 100 original fills**. This is a counterfactual opportunity count, **not realized trading WR**.','',
              f'**Frozen verdict: `{verdict}`.**','',
              f'- BE rescue signal: **{"SUPPORTED" if support["BE"] else "NOT SUPPORTED"}** ({selected["BE"]}).',
              f'- TIME rescue signal: **{"SUPPORTED" if support["TIME_OTHER"] else "NOT SUPPORTED"}** ({selected["TIME_OTHER"]}).','',
              'No economic or live-rule implication is authorized by B27CM. Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))


if __name__=='__main__':
    main()
