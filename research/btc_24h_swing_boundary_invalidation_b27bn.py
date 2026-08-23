#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_24h_regime_detector_audit_b27bg as b27bg
import btc_london_ny_4h_regime_alignment_b27ag as b27ag

ROOT = Path(__file__).resolve().parent.parent
EP_FILE = ROOT / 'BTC_24H_SIDEWAYS_TRANSITION_ANATOMY_B27BH_SidewaysEpisodes.csv'
OUT_MD = ROOT / 'BTC_24H_SWING_BOUNDARY_INVALIDATION_B27BN_Result.md'
OUT_EP = ROOT / 'BTC_24H_SWING_BOUNDARY_INVALIDATION_B27BN_Episodes.csv'
OUT_SUM = ROOT / 'BTC_24H_SWING_BOUNDARY_INVALIDATION_B27BN_Summary.csv'
OUT_STATUS = ROOT / 'BTC_24H_SWING_BOUNDARY_INVALIDATION_B27BN_Status.txt'

H4 = pd.Timedelta(hours=4)
MAJOR = ('external','development','reference_validation')
OOS = ('external','reference_validation')
ORIGINS = ('BULL','BEAR')


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def pp(v):
    return '-' if pd.isna(v) else f'{100*float(v):+.1f}pp'


def as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.copy()
    return s.astype(str).str.lower().eq('true')


def build_instrumented_regime(x5: pd.DataFrame) -> pd.DataFrame:
    z = x5[['open','high','low','close']].copy()
    agg = z.resample('4h', origin='epoch', label='left', closed='left').agg(
        open=('open','first'), high=('high','max'), low=('low','min'), close=('close','last')
    )
    cnt = z.close.resample('4h', origin='epoch', label='left', closed='left').count()
    agg['n5'] = cnt
    agg = agg[(agg.n5 == 48) & agg.open.notna() & agg.close.notna()].copy()
    assert len(agg) >= 1000
    assert (agg.n5 == 48).all()

    H = agg.high.to_numpy(float)
    L = agg.low.to_numpy(float)
    C = agg.close.to_numpy(float)
    ef = b27ag.ema(C, 7)
    es = b27ag.ema(C, 20)
    at = b27ag.atr(H, L, C, 14)
    det = b27ag.SwingRegime(5, 0.5)

    states=[]; hhs=[]; hls=[]; lhs=[]; lls=[]
    lshs=[]; lsls=[]; pshs=[]; psls=[]
    for i in range(len(agg)):
        st = det.process(i, H, L, C, ef, es, at)
        states.append(st)
        hhs.append(int(det.hh)); hls.append(int(det.hl)); lhs.append(int(det.lh)); lls.append(int(det.ll))
        lshs.append(np.nan if det.lsh is None else float(det.lsh))
        lsls.append(np.nan if det.lsl is None else float(det.lsl))
        pshs.append(np.nan if det.psh is None else float(det.psh))
        psls.append(np.nan if det.psl is None else float(det.psl))

    agg['ema7']=ef; agg['ema20']=es; agg['atr14']=at
    agg['hh']=hhs; agg['hl']=hls; agg['lh']=lhs; agg['ll']=lls
    agg['lsh']=lshs; agg['lsl']=lsls; agg['psh']=pshs; agg['psl']=psls
    agg['regime']=states
    agg['source_bar_start']=agg.index
    agg['effective_ts']=pd.to_datetime(agg.index + H4, utc=True)
    agg['available_ts']=agg['effective_ts']
    agg['partition']=agg['effective_ts'].map(b27bg.assign_partition)

    # Instrumentation must reproduce exact existing detector outputs.
    base = b27ag.build_regime(x5)
    assert agg.index.equals(base.index)
    assert agg.regime.equals(base.regime)
    assert np.array_equal(agg.n5.to_numpy(int), base.n5.to_numpy(int))
    assert np.allclose(agg.ema7.to_numpy(float), base.ema7.to_numpy(float), rtol=0, atol=0)
    assert np.allclose(agg.ema20.to_numpy(float), base.ema20.to_numpy(float), rtol=0, atol=0)
    assert np.allclose(agg.atr14.to_numpy(float), base.atr14.to_numpy(float), rtol=0, atol=0)
    return agg.reset_index(drop=True)


def load_parent_episodes() -> pd.DataFrame:
    e = pd.read_csv(EP_FILE)
    e['first_sideways_ts'] = pd.to_datetime(e['first_sideways_ts'], utc=True)
    e['last_sideways_ts'] = pd.to_datetime(e['last_sideways_ts'], utc=True)
    e['bracketed_directional'] = as_bool(e['bracketed_directional'])
    e['same_direction_resume'] = as_bool(e['same_direction_resume'])
    e['opposite_direction_transition'] = as_bool(e['opposite_direction_transition'])
    e['n_intervals'] = pd.to_numeric(e['n_intervals'], errors='raise').astype(int)
    b = e[e.partition.isin(MAJOR) & e.bracketed_directional].copy()
    assert len(b) == 1023
    assert int(b.same_direction_resume.sum()) == 527
    assert int(b.opposite_direction_transition.sum()) == 496
    assert int((b.origin_state == 'BULL').sum()) == 532
    assert int((b.origin_state == 'BEAR').sum()) == 491
    assert (b.same_direction_resume ^ b.opposite_direction_transition).all()
    return b


def build_episode_rows(reg: pd.DataFrame, e: pd.DataFrame) -> pd.DataFrame:
    z = reg.sort_values('effective_ts').reset_index(drop=True)
    by_ts = {pd.Timestamp(t): i for i,t in enumerate(z.effective_ts)}
    rows=[]
    for ep in e.itertuples(index=False):
        first_ts = pd.Timestamp(ep.first_sideways_ts)
        i = by_ts[first_ts]
        first = z.iloc[i]
        prev = z.iloc[i-1]
        origin = str(ep.origin_state)
        assert str(first.regime) == 'SIDEWAYS'
        assert str(prev.regime) == origin
        assert pd.Timestamp(first.effective_ts) - pd.Timestamp(prev.effective_ts) == H4
        assert pd.Timestamp(prev.effective_ts) < first_ts
        d = int(ep.n_intervals)
        seg = z.iloc[i:i+d].copy()
        assert len(seg) == d
        assert (seg.regime == 'SIDEWAYS').all()
        assert pd.Timestamp(seg.iloc[0].effective_ts) == first_ts
        assert pd.Timestamp(seg.iloc[-1].effective_ts) == pd.Timestamp(ep.last_sideways_ts)
        if d > 1:
            assert (seg.effective_ts.diff().dropna() == H4).all()

        if origin == 'BULL':
            boundary = float(prev.lsl) if pd.notna(prev.lsl) else np.nan
            def wick_break(r): return bool(pd.notna(boundary) and float(r.low) < boundary)
            def close_break(r): return bool(pd.notna(boundary) and float(r.close) < boundary)
            boundary_type='FROZEN_LATEST_SWING_LOW'
        else:
            boundary = float(prev.lsh) if pd.notna(prev.lsh) else np.nan
            def wick_break(r): return bool(pd.notna(boundary) and float(r.high) > boundary)
            def close_break(r): return bool(pd.notna(boundary) and float(r.close) > boundary)
            boundary_type='FROZEN_LATEST_SWING_HIGH'

        w = [wick_break(r) for _,r in seg.iterrows()]
        c = [close_break(r) for _,r in seg.iterrows()]
        first_w_age = next((j+1 for j,v in enumerate(w) if v), None)
        first_c_age = next((j+1 for j,v in enumerate(c) if v), None)
        def cum(arr,k):
            return bool(any(arr[:min(k,len(arr))])) if pd.notna(boundary) else False

        rows.append({
            'episode_id': int(ep.episode_id),
            'partition': str(ep.partition),
            'origin_state': origin,
            'exit_state': str(ep.exit_state),
            'outcome': 'RESUME' if bool(ep.same_direction_resume) else 'TRANSITION',
            'transition': bool(ep.opposite_direction_transition),
            'n_intervals': d,
            'first_sideways_ts': first_ts,
            'prior_directional_effective_ts': pd.Timestamp(prev.effective_ts),
            'boundary_type': boundary_type,
            'frozen_boundary': boundary,
            'boundary_available': bool(pd.notna(boundary)),
            'first_wick_break': bool(w[0]) if pd.notna(boundary) else False,
            'first_close_break': bool(c[0]) if pd.notna(boundary) else False,
            'wick_break_by_age2': cum(w,2),
            'wick_break_by_age3': cum(w,3),
            'close_break_by_age2': cum(c,2),
            'close_break_by_age3': cum(c,3),
            'ever_wick_break': bool(any(w)) if pd.notna(boundary) else False,
            'ever_close_break': bool(any(c)) if pd.notna(boundary) else False,
            'first_wick_break_age': np.nan if first_w_age is None else int(first_w_age),
            'first_close_break_age': np.nan if first_c_age is None else int(first_c_age),
        })
    out=pd.DataFrame(rows)
    assert len(out)==1023
    assert (out.prior_directional_effective_ts < out.first_sideways_ts).all()
    assert ((out.first_sideways_ts - out.prior_directional_effective_ts) == H4).all()
    return out


def subset(d: pd.DataFrame, part: str, origin: str) -> pd.DataFrame:
    q=d[d.origin_state==origin].copy()
    if part=='POOLED_OOS': return q[q.partition.isin(OOS)].copy()
    if part=='POOLED_MAJOR': return q[q.partition.isin(MAJOR)].copy()
    return q[q.partition==part].copy()


def rate(x: pd.Series) -> float:
    return float(x.mean()) if len(x) else np.nan


def summarize(d: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for part in (*MAJOR,'POOLED_OOS','POOLED_MAJOR'):
        for origin in ORIGINS:
            q=subset(d,part,origin)
            known=q[q.boundary_available].copy()
            trans=known[known.transition]
            resume=known[~known.transition]
            br=known[known.first_wick_break]
            hd=known[~known.first_wick_break]
            cbr=known[known.first_close_break]
            chd=known[~known.first_close_break]
            rows.append({
                'partition':part,'origin':origin,
                'total_n':len(q),'boundary_known_n':len(known),'boundary_known_rate':len(known)/len(q) if len(q) else np.nan,
                'first_wick_break_n':len(br),'first_wick_hold_n':len(hd),
                'transition_rate_first_wick_break':rate(br.transition),
                'transition_rate_first_wick_hold':rate(hd.transition),
                'first_wick_transition_lift':rate(br.transition)-rate(hd.transition) if len(br) and len(hd) else np.nan,
                'first_close_break_n':len(cbr),'first_close_hold_n':len(chd),
                'transition_rate_first_close_break':rate(cbr.transition),
                'transition_rate_first_close_hold':rate(chd.transition),
                'first_close_transition_lift':rate(cbr.transition)-rate(chd.transition) if len(cbr) and len(chd) else np.nan,
                'resume_n':len(resume),'transition_n':len(trans),
                'resume_wick_break_age1':rate(resume.first_wick_break),
                'transition_wick_break_age1':rate(trans.first_wick_break),
                'resume_wick_break_age2':rate(resume.wick_break_by_age2),
                'transition_wick_break_age2':rate(trans.wick_break_by_age2),
                'resume_wick_break_age3':rate(resume.wick_break_by_age3),
                'transition_wick_break_age3':rate(trans.wick_break_by_age3),
                'age3_break_rate_diff':rate(trans.wick_break_by_age3)-rate(resume.wick_break_by_age3) if len(trans) and len(resume) else np.nan,
                'resume_close_break_age3':rate(resume.close_break_by_age3),
                'transition_close_break_age3':rate(trans.close_break_by_age3),
                'transition_never_wick_break_rate':rate(~trans.ever_wick_break),
                'resume_ever_wick_break_rate':rate(resume.ever_wick_break),
            })
    return pd.DataFrame(rows)


def getrow(s,part,origin):
    q=s[(s.partition==part)&(s.origin==origin)]
    assert len(q)==1
    return q.iloc[0]


def main():
    x5,coverage=b21.load5()
    assert len(x5)==698112
    assert abs(float(coverage)-1.0)<1e-12
    reg=build_instrumented_regime(x5)
    e=load_parent_episodes()
    d=build_episode_rows(reg,e)
    s=summarize(d)

    gate_identity=True
    gate_boundary=True
    gate_first_pooled=True
    gate_first_partitions=True
    gate_age3_pooled=True
    gate_age3_partitions=True
    gate_sample=True

    for origin in ORIGINS:
        r=getrow(s,'POOLED_OOS',origin)
        gate_boundary = gate_boundary and float(r.boundary_known_rate) >= .95
        gate_first_pooled = gate_first_pooled and float(r.first_wick_transition_lift) > 0
        gate_age3_pooled = gate_age3_pooled and float(r.age3_break_rate_diff) >= .10
        gate_sample = gate_sample and int(r.first_wick_break_n) >= 20 and int(r.first_wick_hold_n) >= 20
        for part in OOS:
            p=getrow(s,part,origin)
            gate_first_partitions = gate_first_partitions and pd.notna(p.first_wick_transition_lift) and float(p.first_wick_transition_lift) > 0
            gate_age3_partitions = gate_age3_partitions and pd.notna(p.age3_break_rate_diff) and float(p.age3_break_rate_diff) > 0

    supported=all([gate_identity,gate_boundary,gate_first_pooled,gate_first_partitions,gate_age3_pooled,gate_age3_partitions,gate_sample])
    verdict='B27BN_SWING_BOUNDARY_INVALIDATION_SUPPORTED' if supported else 'B27BN_SWING_BOUNDARY_INVALIDATION_NOT_SUPPORTED'

    d.to_csv(OUT_EP,index=False)
    s.to_csv(OUT_SUM,index=False)
    OUT_STATUS.write_text(verdict+'\n')

    lines=[
        '# B27BN — BTC 24H Swing-Boundary Invalidation Audit — Result','',
        '**Audit status: PASS.** Regime-structure anatomy only; no LONG/SHORT mapping, entry, stop, target, fee, WR, PF, PnL, session filter, or live change was used.','',
        'B27BH parent identity reproduced exactly: **1,023 episodes = 527 RESUME + 496 TRANSITION; BULL-origin 532; BEAR-origin 491.**','',
        'Frozen boundary comes from the immediately preceding completed directional 4H state: latest confirmed swing low (`lsl`) for BULL, latest confirmed swing high (`lsh`) for BEAR.','',
        '## Pooled OOS — first SIDEWAYS bar','',
        '| Origin | Boundary known | Wick BREAK N | P(transition \| break) | HOLD N | P(transition \| hold) | Lift |',
        '|---|---:|---:|---:|---:|---:|---:|'
    ]
    for origin in ORIGINS:
        r=getrow(s,'POOLED_OOS',origin)
        lines.append(f'| {origin} | {int(r.boundary_known_n)}/{int(r.total_n)} = {pct(r.boundary_known_rate)} | {int(r.first_wick_break_n)} | {pct(r.transition_rate_first_wick_break)} | {int(r.first_wick_hold_n)} | {pct(r.transition_rate_first_wick_hold)} | {pp(r.first_wick_transition_lift)} |')

    lines += ['', '## Pooled OOS — cumulative frozen-boundary wick break by outcome','',
              '| Origin | Outcome | Age1 / 4h | By age2 / 8h | By age3 / 12h |',
              '|---|---|---:|---:|---:|']
    for origin in ORIGINS:
        r=getrow(s,'POOLED_OOS',origin)
        lines.append(f'| {origin} | RESUME | {pct(r.resume_wick_break_age1)} | {pct(r.resume_wick_break_age2)} | {pct(r.resume_wick_break_age3)} |')
        lines.append(f'| {origin} | TRANSITION | {pct(r.transition_wick_break_age1)} | {pct(r.transition_wick_break_age2)} | {pct(r.transition_wick_break_age3)} |')
        lines.append(f'| {origin} | TRANSITION - RESUME at age3 |  |  | {pp(r.age3_break_rate_diff)} |')

    lines += ['', '## OOS stability — first-bar wick-break lift and age3 break-rate separation','',
              '| Partition | Origin | First-bar transition lift | Age3 TRANSITION-RESUME break rate |',
              '|---|---|---:|---:|']
    for part in OOS:
        for origin in ORIGINS:
            r=getrow(s,part,origin)
            lines.append(f'| {part} | {origin} | {pp(r.first_wick_transition_lift)} | {pp(r.age3_break_rate_diff)} |')

    lines += ['', '## Close-break confirmation — pooled OOS','',
              '| Origin | First close-break N | P(transition \| close break) | P(transition \| close hold) | Lift | RESUME close-break by age3 | TRANSITION close-break by age3 |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for origin in ORIGINS:
        r=getrow(s,'POOLED_OOS',origin)
        lines.append(f'| {origin} | {int(r.first_close_break_n)} | {pct(r.transition_rate_first_close_break)} | {pct(r.transition_rate_first_close_hold)} | {pp(r.first_close_transition_lift)} | {pct(r.resume_close_break_age3)} | {pct(r.transition_close_break_age3)} |')

    lines += ['', '## Important diagnostic','']
    for origin in ORIGINS:
        r=getrow(s,'POOLED_OOS',origin)
        lines.append(f'- {origin}: genuine TRANSITION episodes that reached the opposite detector state **without ever wick-breaking** the frozen origin boundary during SIDEWAYS: **{pct(r.transition_never_wick_break_rate)}**.')
        lines.append(f'- {origin}: RESUME episodes that **did wick-break** the frozen boundary before returning to the origin state: **{pct(r.resume_ever_wick_break_rate)}**.')

    lines += ['', '## Frozen support gate','',
              f'- Exact source/detector/episode/timing identity: **{"PASS" if gate_identity else "FAIL"}**.',
              f'- Boundary available >=95% pooled OOS for both origins: **{"PASS" if gate_boundary else "FAIL"}**.',
              f'- First-bar wick break increases transition rate pooled OOS for both origins: **{"PASS" if gate_first_pooled else "FAIL"}**.',
              f'- First-bar wick-break lift positive in external and validation for both origins: **{"PASS" if gate_first_partitions else "FAIL"}**.',
              f'- Age3 transition-minus-resume wick-break rate >=10pp pooled OOS for both origins: **{"PASS" if gate_age3_pooled else "FAIL"}**.',
              f'- Age3 separation positive in external and validation for both origins: **{"PASS" if gate_age3_partitions else "FAIL"}**.',
              f'- First-bar BREAK and HOLD pooled-OOS N >=20 per origin: **{"PASS" if gate_sample else "FAIL"}**.','',
              f'**Frozen verdict: `{verdict}`.**','',
              '## Interpretation boundary','',
              'A supported result would validate only the frozen prior swing boundary as a causal regime-invalidation signal. It does not redesign the production detector or authorize any trading behavior.','',
              'Research only. Live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
