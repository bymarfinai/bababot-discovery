#!/usr/bin/env python3
from pathlib import Path
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b
import btc_previous_session_direct_sweep_b26c as b26c
import btc_prev_session_level_retest_atlas_b27l as b27l

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_PREV_SESSION_LEVEL_RETEST_ATLAS_B27M_Result.md'
OUT_SUM=ROOT/'BTC_PREV_SESSION_LEVEL_RETEST_ATLAS_B27M_Summary.csv'
OUT_COMBO=ROOT/'BTC_PREV_SESSION_LEVEL_RETEST_ATLAS_B27M_Combos.csv'
OUT_EVENTS=ROOT/'BTC_PREV_SESSION_LEVEL_RETEST_ATLAS_B27M_Events.csv'
PARTS=b22b.PARTS; TRANSITIONS=b26c.TRANSITIONS
TF_MINUTES=b27l.TF_MINUTES; TOLS=b27l.TOLS; BAR5=pd.Timedelta(minutes=5)


def fast_slice(x5,start,end):
    a=int(x5.index.searchsorted(start,side='left')); b=int(x5.index.searchsorted(end,side='left'))
    return x5.iloc[a:b]


def main():
    x5,coverage=b21.load5(); rows=[]
    for part,(start,end) in PARTS.items():
        for day in pd.date_range(start.normalize(),(end-pd.Timedelta(seconds=1)).normalize(),freq='D',tz='UTC'):
            if day.weekday()>=5: continue
            for transition,cfg in TRANSITIONS.items():
                ps=b26c.ts_for_day(day,cfg['prev_start']); pe=b26c.ts_for_day(day,cfg['prev_end'])
                ns=b26c.ts_for_day(day,cfg['next_start']); ne=b26c.ts_for_day(day,cfg['next_end'])
                if ps<start or ne>end: continue
                prev=fast_slice(x5,ps,pe); q5=fast_slice(x5,ns,ne)
                if len(prev)!=int((pe-ps)/BAR5) or len(q5)!=int((ne-ns)/BAR5): continue
                phi=float(prev.high.max()); plo=float(prev.low.min())
                bars_by_tf={tf:b27l.session_bars(q5,ns,ne,m) for tf,m in TF_MINUTES.items()}
                for tf,bars in bars_by_tf.items():
                    for tol_name,tol in TOLS.items():
                        obs=b27l.observe(bars,phi,plo,tol)
                        rows.append({'partition':part,'transition':transition,'date_utc':str(day.date()),'tf':tf,
                                     'tolerance':tol_name,'tol_value':tol,'previous_session_high':phi,
                                     'previous_session_low':plo,'active_session_start':ns,'active_session_end':ne,
                                     'active_tf_bars':int(len(bars)),'partial_tf_bars':int(bars.partial_bar.sum()),**obs})
    events=pd.DataFrame(rows); events.to_csv(OUT_EVENTS,index=False)
    sums=[]
    for tf in TF_MINUTES:
        for tol in TOLS:
            for tr in TRANSITIONS:
                for part in PARTS:
                    base=events[(events.tf==tf)&(events.tolerance==tol)&(events.transition==tr)&(events.partition==part)]
                    for d in ['BULL','BEAR','NO_BREAK']:
                        sums.append({'tf':tf,'tolerance':tol,'transition':tr,'partition':part,'direction':d,
                                     **b27l.summarize(base[base.direction==d])})
    s=pd.DataFrame(sums); s.to_csv(OUT_SUM,index=False)
    combos=(events.groupby(['tf','tolerance','transition','partition','direction','high_retests','low_retests'],dropna=False)
            .size().reset_index(name='n'))
    combos['share_within_group']=combos['n']/combos.groupby(['tf','tolerance','transition','partition','direction'])['n'].transform('sum')
    combos.to_csv(OUT_COMBO,index=False)

    md=['# B27M — Previous-Session High/Low Retest Atlas (Optimized Rerun)','',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**. Definitions identical to B27L.','',
        'BULL = first strict active-TF close above completed previous-session High. BEAR = first strict close below completed previous-session Low. Counts are accumulated before that breakout. Zones: ±0.10% and ±0.20%.','',
        'Distinct retests collapse consecutive zone-intersecting bars into one visit. Raw touch bars count every active-TF bar intersecting the level zone before breakout.','',
        '## Bull/Bear retest summary','',
        '| TF | Tol | Transition | Partition | Dir | N | High distinct med/mean/P75/max | Low distinct med/mean/P75/max | High raw med/mean/P75/max | Low raw med/mean/P75/max | H>=2 | H>=3 | L>=2 | L>=3 |',
        '|---|---|---|---|---|---:|---|---|---|---|---:|---:|---:|---:|']
    use=s[s.direction.isin(['BULL','BEAR'])]
    for r in use.itertuples(index=False):
        if int(r.n)==0: continue
        md.append(f'| {r.tf} | {r.tolerance} | {r.transition} | {r.partition} | {r.direction} | {int(r.n)} | '
                  f'{r.hi_median:.1f}/{r.hi_mean:.2f}/{r.hi_p75:.1f}/{int(r.hi_max)} | '
                  f'{r.lo_median:.1f}/{r.lo_mean:.2f}/{r.lo_p75:.1f}/{int(r.lo_max)} | '
                  f'{r.hi_raw_median:.1f}/{r.hi_raw_mean:.2f}/{r.hi_raw_p75:.1f}/{int(r.hi_raw_max)} | '
                  f'{r.lo_raw_median:.1f}/{r.lo_raw_mean:.2f}/{r.lo_raw_p75:.1f}/{int(r.lo_raw_max)} | '
                  f'{100*r.hi_ge2:.1f}% | {100*r.hi_ge3:.1f}% | {100*r.lo_ge2:.1f}% | {100*r.lo_ge3:.1f}% |')
    md+=['','Exact `(High distinct retests, Low distinct retests)` frequencies are persisted in the Combos CSV; every day-level event is persisted in Events CSV.','',
         'Diagnostic only; no bucket is promoted to a trading rule. Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__=='__main__': main()
