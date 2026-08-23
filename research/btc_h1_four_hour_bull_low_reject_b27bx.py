#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_24h_swing_boundary_invalidation_b27bn as b27bn

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_H1_FOUR_HOUR_BULL_LOW_REJECT_B27BX_Result.md'
OUT_EVENTS = ROOT / 'BTC_H1_FOUR_HOUR_BULL_LOW_REJECT_B27BX_Events.csv'
OUT_SUM = ROOT / 'BTC_H1_FOUR_HOUR_BULL_LOW_REJECT_B27BX_Summary.csv'
OUT_STATUS = ROOT / 'BTC_H1_FOUR_HOUR_BULL_LOW_REJECT_B27BX_Status.txt'

MAJOR = ('external','development','reference_validation')
OOS = ('external','reference_validation')
EVENT_HOURS = {4:'11:00', 8:'15:00', 18:'01:00', 19:'02:00'}
H1 = pd.Timedelta(hours=1)
H4 = pd.Timedelta(hours=4)


def partition(ts: pd.Timestamp):
    for name,(a,b) in b21.PARTS.items():
        if name in MAJOR and a <= ts < b:
            return name
    return None


def aggregate_1h(x5: pd.DataFrame) -> pd.DataFrame:
    z = x5[['open','high','low','close']].resample(
        '1h', origin='start_day', label='left', closed='left'
    ).agg({'open':'first','high':'max','low':'min','close':'last'})
    cnt = x5.close.resample('1h', origin='start_day', label='left', closed='left').count()
    z['n5'] = cnt
    z = z[(z.n5 == 12) & z.open.notna() & z.close.notna()].copy()
    return z


def regime_at(reg: pd.DataFrame, ts: pd.Timestamp):
    eff = pd.DatetimeIndex(pd.to_datetime(reg.effective_ts, utc=True))
    j = int(eff.searchsorted(ts, side='right')) - 1
    if j < 0:
        return None, pd.NaT
    r = reg.iloc[j]
    et = pd.Timestamp(r.effective_ts)
    assert et <= ts
    assert ts - et < H4
    return str(r.regime), et


def build_events(x1: pd.DataFrame, reg: pd.DataFrame) -> pd.DataFrame:
    idx = x1.index
    rows=[]
    for i in range(3, len(x1)-3):
        event_ts = idx[i]
        if int(event_ts.hour) not in EVENT_HOURS:
            continue
        event_complete = event_ts + H1
        part = partition(event_complete)
        if part is None:
            continue
        expected_prior = pd.date_range(event_ts-3*H1, event_ts-H1, freq='1h', tz='UTC')
        expected_future = [event_ts+H1, event_ts+2*H1, event_ts+3*H1]
        prior = x1.iloc[i-3:i]
        if not prior.index.equals(expected_prior):
            continue
        if [idx[i+1],idx[i+2],idx[i+3]] != expected_future:
            continue
        cur=x1.iloc[i]
        ph=float(prior.high.max()); pl=float(prior.low.min())
        high_sweep=float(cur.high)>ph
        low_sweep=float(cur.low)<pl
        low_reject=bool(low_sweep and (not high_sweep) and float(cur.close)>=pl)
        if not low_reject:
            continue
        state, state_effective = regime_at(reg,event_complete)
        assert state is not None
        entry=float(x1.iloc[i+1].open)
        c1=float(x1.iloc[i+1].close)
        c3=float(x1.iloc[i+3].close)
        rows.append({
            'partition':part,
            'event_ts':event_ts,
            'event_complete_ts':event_complete,
            'event_hour_utc':int(event_ts.hour),
            'event_hour_wib':EVENT_HOURS[int(event_ts.hour)],
            'prior3_high':ph,'prior3_low':pl,
            'event_open':float(cur.open),'event_high':float(cur.high),'event_low':float(cur.low),'event_close':float(cur.close),
            'regime_effective_ts':state_effective,
            'regime':state,
            'entry_ts':event_ts+H1,
            'entry_open':entry,
            'close1h':c1,'close3h':c3,
            'long_positive_1h':bool(c1>entry),
            'long_positive_3h':bool(c3>entry),
            'signed_ret_1h':c1/entry-1.0,
            'signed_ret_3h':c3/entry-1.0,
        })
    d=pd.DataFrame(rows)
    assert not d.empty
    assert set(d.event_hour_utc.unique()).issubset(set(EVENT_HOURS))
    assert (pd.to_datetime(d.regime_effective_ts,utc=True) <= pd.to_datetime(d.event_complete_ts,utc=True)).all()
    assert ((pd.to_datetime(d.event_complete_ts,utc=True)-pd.to_datetime(d.regime_effective_ts,utc=True)) < H4).all()
    return d


def subset(d:pd.DataFrame, part:str):
    if part=='POOLED_OOS': return d[d.partition.isin(OOS)].copy()
    if part=='POOLED_MAJOR': return d[d.partition.isin(MAJOR)].copy()
    return d[d.partition==part].copy()


def metrics(g:pd.DataFrame):
    return {
        'n':len(g),
        'positive1h':float(g.long_positive_1h.mean()) if len(g) else np.nan,
        'positive3h':float(g.long_positive_3h.mean()) if len(g) else np.nan,
        'mean_ret1h':float(g.signed_ret_1h.mean()) if len(g) else np.nan,
        'mean_ret3h':float(g.signed_ret_3h.mean()) if len(g) else np.nan,
        'median_ret3h':float(g.signed_ret_3h.median()) if len(g) else np.nan,
    }


def summarize(d:pd.DataFrame):
    rows=[]
    for part in (*MAJOR,'POOLED_OOS','POOLED_MAJOR'):
        q=subset(d,part)
        for hour in (*EVENT_HOURS.keys(),'ALL4'):
            z=q if hour=='ALL4' else q[q.event_hour_utc==hour]
            ctrl=metrics(z)
            bull=metrics(z[z.regime=='BULL'])
            rows.append({
                'partition':part,
                'event_hour_utc':hour,
                'event_hour_wib':'ALL4' if hour=='ALL4' else EVENT_HOURS[int(hour)],
                'control_n':ctrl['n'],'control_positive1h':ctrl['positive1h'],'control_positive3h':ctrl['positive3h'],
                'control_mean_ret3h':ctrl['mean_ret3h'],
                'bull_n':bull['n'],'bull_positive1h':bull['positive1h'],'bull_positive3h':bull['positive3h'],
                'bull_mean_ret3h':bull['mean_ret3h'],'bull_median_ret3h':bull['median_ret3h'],
                'bull_lift_3h':bull['positive3h']-ctrl['positive3h'] if bull['n'] and ctrl['n'] else np.nan,
            })
    return pd.DataFrame(rows)


def getrow(s,part,hour='ALL4'):
    q=s[(s.partition==part)&(s.event_hour_utc.astype(str)==str(hour))]
    assert len(q)==1,(part,hour,len(q))
    return q.iloc[0]


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def pp(v):
    return '-' if pd.isna(v) else f'{100*float(v):+.1f}pp'


def main():
    x5,coverage=b21.load5()
    assert len(x5)==698112
    assert abs(float(coverage)-1.0)<1e-12
    x1=aggregate_1h(x5)
    reg=b27bn.build_instrumented_regime(x5)
    d=build_events(x1,reg)
    d.to_csv(OUT_EVENTS,index=False)
    s=summarize(d)
    s.to_csv(OUT_SUM,index=False)

    o=getrow(s,'POOLED_OOS')
    ext=getrow(s,'external')
    val=getrow(s,'reference_validation')
    gate_sample=int(o.bull_n)>=40
    gate_rate=float(o.bull_positive3h)>=.65
    gate_parts=float(ext.bull_positive3h)>=.60 and float(val.bull_positive3h)>=.60
    gate_lift=float(o.bull_lift_3h)>0 and float(ext.bull_lift_3h)>0 and float(val.bull_lift_3h)>0
    good_hours=0
    for h in EVENT_HOURS:
        r=getrow(s,'POOLED_OOS',h)
        if int(r.bull_n)>=10 and pd.notna(r.bull_positive3h) and float(r.bull_positive3h)>.50:
            good_hours+=1
    gate_hours=good_hours>=3
    supported=all([gate_sample,gate_rate,gate_parts,gate_lift,gate_hours])
    verdict='B27BX_FOUR_HOUR_BULL_LOW_REJECT_SUPPORTED' if supported else 'B27BX_FOUR_HOUR_BULL_LOW_REJECT_NOT_SUPPORTED'
    OUT_STATUS.write_text(verdict+'\n')

    lines=[
        '# B27BX — BTC Four Fixed H1 Hours × Causal 24H BULL LOW_REJECT — Result','',
        '**Audit status: PASS.** Directional anatomy only; no TP/SL/RR/fee or live-rule optimization.','',
        f'Raw BTCUSDT 5m identity: **{len(x5):,} rows / {100*coverage:.4f}% coverage**.','',
        'Fixed hours: **11:00 / 15:00 / 01:00 / 02:00 WIB**. Event = 1H LOW_REJECT versus the exact completed prior3H range. Primary filter = latest causally available 24H regime is **BULL** at event completion.','',
        '## Major-partition pooled four-hour readout','',
        '| Partition | Control N | Control +3H | BULL N | BULL +1H | BULL +3H | BULL lift | BULL mean +3H return |',
        '|---|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for part in MAJOR:
        r=getrow(s,part)
        lines.append(f'| {part} | {int(r.control_n)} | {pct(r.control_positive3h)} | {int(r.bull_n)} | {pct(r.bull_positive1h)} | {pct(r.bull_positive3h)} | {pp(r.bull_lift_3h)} | {pct(r.bull_mean_ret3h)} |')
    lines += ['', '## Pooled readout','',
              '| Pool | Control N | Control +3H | BULL N | BULL +1H | BULL +3H | Lift |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for part in ('POOLED_OOS','POOLED_MAJOR'):
        r=getrow(s,part)
        lines.append(f'| {part} | {int(r.control_n)} | {pct(r.control_positive3h)} | {int(r.bull_n)} | {pct(r.bull_positive1h)} | {pct(r.bull_positive3h)} | {pp(r.bull_lift_3h)} |')
    lines += ['', '## Per-hour pooled OOS','',
              '| WIB hour | Control N | Control +3H | BULL N | BULL +1H | BULL +3H | Lift |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for h in EVENT_HOURS:
        r=getrow(s,'POOLED_OOS',h)
        lines.append(f'| {EVENT_HOURS[h]} | {int(r.control_n)} | {pct(r.control_positive3h)} | {int(r.bull_n)} | {pct(r.bull_positive1h)} | {pct(r.bull_positive3h)} | {pp(r.bull_lift_3h)} |')
    lines += ['', '## Frozen support gate','',
              f'- Pooled-OOS BULL N >=40: **{"PASS" if gate_sample else "FAIL"}**.',
              f'- Pooled-OOS BULL +3H >=65%: **{"PASS" if gate_rate else "FAIL"}**.',
              f'- External and validation BULL +3H each >=60%: **{"PASS" if gate_parts else "FAIL"}**.',
              f'- Positive BULL-vs-control lift in pooled OOS + external + validation: **{"PASS" if gate_lift else "FAIL"}**.',
              f'- At least 3/4 hours have OOS BULL N>=10 and +3H >50%: **{"PASS" if gate_hours else "FAIL"}** ({good_hours}/4).','',
              f'**Frozen verdict: `{verdict}`.**','',
              'A supported result would only justify a separately preregistered execution experiment.','',
              'Research only. Live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
