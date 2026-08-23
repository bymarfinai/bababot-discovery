#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b
import btc_london_ny_4h_regime_alignment_b27ag as b27ag

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_24H_4H_REGIME_SHORT_ATLAS_B27BE_Result.md'
OUT_DETAIL = ROOT / 'BTC_24H_4H_REGIME_SHORT_ATLAS_B27BE_Detail.csv'
OUT_REGIME = ROOT / 'BTC_24H_4H_REGIME_SHORT_ATLAS_B27BE_RegimeSummary.csv'
OUT_CLOCK = ROOT / 'BTC_24H_4H_REGIME_SHORT_ATLAS_B27BE_ClockSummary.csv'
OUT_STATUS = ROOT / 'BTC_24H_4H_REGIME_SHORT_ATLAS_B27BE_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
H4 = pd.Timedelta(hours=4)
PARTS = b22b.PARTS
MAJOR = ('external','development','reference_validation')
REGIMES = ('BULL','BEAR','SIDEWAYS')
CLOCKS = (0,4,8,12,16,20)


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def scan_block(q: pd.DataFrame, H: float, L: float) -> dict:
    assert H > L
    low_visits = 0
    high_visits = 0
    low_touching = False
    high_touching = False
    k1_opp0 = False
    k1_ts = pd.NaT
    k2_ts = pd.NaT
    k3_ts = pd.NaT
    status = 'NO_BREAK'
    breakout_side = None

    for ts, r in q.iterrows():
        hi = float(r.high); lo = float(r.low); c = float(r.close)
        break_hi = c > H
        break_lo = c < L
        if break_hi and break_lo:
            raise AssertionError('impossible strict close beyond both boundaries')
        if break_hi or break_lo:
            breakout_side = 'HIGH' if break_hi else 'LOW'
            status = f'BREAK_{breakout_side}'
            break

        hit_hi = hi >= H and c <= H
        hit_lo = lo <= L and c >= L
        if hit_hi and hit_lo:
            return {
                'status':'AMBIGUOUS_BOTH_LEVELS','breakout_side':None,
                'low_visits':np.nan,'high_visits':np.nan,
                'k1_opp0':False,'k1_ts':pd.NaT,'k2_ts':pd.NaT,'k3_ts':pd.NaT,
            }

        if hit_lo and not low_touching:
            low_visits += 1
            if low_visits == 1:
                k1_ts = ts + BAR5
                k1_opp0 = (high_visits == 0)
            elif low_visits == 2:
                k2_ts = ts + BAR5
            elif low_visits == 3:
                k3_ts = ts + BAR5
        if hit_hi and not high_touching:
            high_visits += 1

        low_touching = bool(hit_lo)
        high_touching = bool(hit_hi)

    return {
        'status':status,'breakout_side':breakout_side,
        'low_visits':int(low_visits),'high_visits':int(high_visits),
        'k1_opp0':bool(k1_opp0),'k1_ts':k1_ts,'k2_ts':k2_ts,'k3_ts':k3_ts,
    }


def summarize_groups(detail: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    rows=[]
    grouper = by[0] if len(by)==1 else by
    for key, g in detail.groupby(grouper, dropna=False):
        if not isinstance(key, tuple): key=(key,)
        base={c:v for c,v in zip(by,key)}
        q=g[g.k1_opp0].copy()
        n=len(q)
        k2=q[pd.to_numeric(q.low_visits,errors='coerce')>=2]
        rows.append({
            **base,
            'blocks':int(len(g)),
            'k1_opp0_n':int(n),
            'low_break_n':int((q.breakout_side=='LOW').sum()) if n else 0,
            'high_break_n':int((q.breakout_side=='HIGH').sum()) if n else 0,
            'no_break_n':int((q.status=='NO_BREAK').sum()) if n else 0,
            'low_break_prob':float((q.breakout_side=='LOW').mean()) if n else np.nan,
            'high_break_prob':float((q.breakout_side=='HIGH').mean()) if n else np.nan,
            'no_break_prob':float((q.status=='NO_BREAK').mean()) if n else np.nan,
            'second_low_n':int(len(k2)),
            'second_low_prob':float(len(k2)/n) if n else np.nan,
            'low_break_after_second_n':int((k2.breakout_side=='LOW').sum()) if len(k2) else 0,
            'low_break_after_second_prob':float((k2.breakout_side=='LOW').mean()) if len(k2) else np.nan,
        })
    return pd.DataFrame(rows)


def fmt_pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def main() -> None:
    x5, coverage = b21.load5()
    assert len(x5) == 698112 and abs(float(coverage)-1.0) < 1e-12
    reg = b27ag.build_regime(x5)

    rows=[]
    for part,(pstart,pend) in PARTS.items():
        first = pstart.normalize()
        last = (pend - pd.Timedelta(seconds=1)).normalize()
        for day in pd.date_range(first,last,freq='D',tz='UTC'):
            for hh in CLOCKS:
                obs_start = day + pd.Timedelta(hours=hh)
                obs_end = obs_start + H4
                prev_start = obs_start - H4
                prev_end = obs_start
                if prev_start < pstart or obs_end > pend:
                    continue
                prev = fast_slice(x5,prev_start,prev_end)
                obs = fast_slice(x5,obs_start,obs_end)
                if len(prev)!=48 or len(obs)!=48:
                    continue
                if not (prev.index[0]==prev_start and obs.index[0]==obs_start):
                    continue
                H=float(prev.high.max()); L=float(prev.low.min())
                if not H>L:
                    continue
                regime, regime_bar, regime_av = b27ag.state_at(reg,obs_start)
                if pd.isna(regime_av) or pd.Timestamp(regime_av) > obs_start:
                    raise AssertionError('non-causal regime attribution')
                s=scan_block(obs,H,L)
                rows.append({
                    'partition':part,'date_utc':str(day.date()),'weekday':int(day.weekday()),
                    'day_type':'WEEKEND' if day.weekday()>=5 else 'WEEKDAY',
                    'clock_start_hour':hh,'clock_block':f'{hh:02d}-{(hh+4)%24:02d}',
                    'prev_start':prev_start,'obs_start':obs_start,'obs_end':obs_end,
                    'H':H,'L':L,'range':H-L,
                    'regime':regime,'regime_bar_start':regime_bar,'regime_available_ts':regime_av,
                    **s,
                })

    d=pd.DataFrame(rows)
    if len(d) < 9000:
        raise AssertionError(f'too few complete full-day blocks: {len(d)}')
    if d.duplicated(['partition','obs_start']).any():
        raise AssertionError('duplicate observation blocks')
    d.to_csv(OUT_DETAIL,index=False)

    # Regime summaries by partition plus pooled major.
    reg_parts=summarize_groups(d,['partition','regime'])
    pooled=summarize_groups(d[d.partition.isin(MAJOR)].assign(partition='POOLED_MAJOR'),['partition','regime'])
    rs=pd.concat([reg_parts,pooled],ignore_index=True)
    rs.to_csv(OUT_REGIME,index=False)

    # Clock summaries, independent of regime, by partition plus pooled major.
    clock_parts=summarize_groups(d,['partition','clock_block'])
    clock_pool=summarize_groups(d[d.partition.isin(MAJOR)].assign(partition='POOLED_MAJOR'),['partition','clock_block'])
    cs=pd.concat([clock_parts,clock_pool],ignore_index=True)
    cs.to_csv(OUT_CLOCK,index=False)

    favored=[]
    for rg in REGIMES:
        ok=True
        for part in MAJOR:
            z=rs[(rs.partition==part)&(rs.regime==rg)]
            if len(z)!=1:
                ok=False; break
            r=z.iloc[0]
            ok = ok and int(r.k1_opp0_n)>=30 and float(r.low_break_prob)>=0.60 and float(r.second_low_prob)>=0.50
        if ok: favored.append(rg)

    clock_favored=[]
    for cb in sorted(d.clock_block.unique()):
        ok=True
        for part in MAJOR:
            z=cs[(cs.partition==part)&(cs.clock_block==cb)]
            if len(z)!=1:
                ok=False; break
            r=z.iloc[0]
            ok = ok and int(r.k1_opp0_n)>=30 and float(r.low_break_prob)>=0.60 and float(r.second_low_prob)>=0.50
        if ok: clock_favored.append(cb)

    status = f'B27BE_SHORT_STRUCTURALLY_FAVORED_{"_".join(favored) if favored else "NONE"}__CLOCK_{"_".join(clock_favored) if clock_favored else "NONE"}'
    OUT_STATUS.write_text(status+'\n')

    lines=[
        '# B27BE — BTC 24H Causal 4H Regime SHORT Compatibility Atlas — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
        '**Audit status: PASS.** Exact B27AG causal 4H SwingRegime semantics were reused. All seven calendar days were included. The full BTC day was covered by six sequential 4H observation blocks, each using the immediately previous completed 4H range as frozen liquidity H/L.','',
        'No Asia/London/New-York session label, entry fraction, stop, target, runner, or confirmation rule was used in selection.','',
        '## Pooled-major regime atlas','',
        '| Regime | Blocks | K1 OPP0 | Low break | High break | No break | 2nd Low | Low break after 2nd |',
        '|---|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for rg in REGIMES:
        r=rs[(rs.partition=='POOLED_MAJOR')&(rs.regime==rg)].iloc[0]
        lines.append(f'| {rg} | {int(r.blocks)} | {int(r.k1_opp0_n)} | {fmt_pct(r.low_break_prob)} | {fmt_pct(r.high_break_prob)} | {fmt_pct(r.no_break_prob)} | {fmt_pct(r.second_low_prob)} | {fmt_pct(r.low_break_after_second_prob)} |')

    lines += ['', '## Major partitions by regime','',
        '| Regime | Partition | K1 OPP0 | Low break | 2nd Low | Low break after 2nd |',
        '|---|---|---:|---:|---:|---:|']
    for rg in REGIMES:
        for part in MAJOR:
            r=rs[(rs.partition==part)&(rs.regime==rg)].iloc[0]
            lines.append(f'| {rg} | {part} | {int(r.k1_opp0_n)} | {fmt_pct(r.low_break_prob)} | {fmt_pct(r.second_low_prob)} | {fmt_pct(r.low_break_after_second_prob)} |')

    lines += ['', '## Pooled-major clock diagnostics','',
        '| UTC block | K1 OPP0 | Low break | 2nd Low | Low break after 2nd |',
        '|---|---:|---:|---:|---:|']
    for cb in sorted(d.clock_block.unique(), key=lambda x:int(x[:2])):
        r=cs[(cs.partition=='POOLED_MAJOR')&(cs.clock_block==cb)].iloc[0]
        lines.append(f'| {cb} | {int(r.k1_opp0_n)} | {fmt_pct(r.low_break_prob)} | {fmt_pct(r.second_low_prob)} | {fmt_pct(r.low_break_after_second_prob)} |')

    lines += ['', '## Frozen gate','',
        f'Regimes passing the preregistered three-partition structural gate: **{", ".join(favored) if favored else "NONE"}**.',
        f'Clock blocks passing the same gate independently: **{", ".join(clock_favored) if clock_favored else "NONE"}**.',
        '', f'**Status: {status}.**','',
        'B27BE is structural discovery only. It does not authorize a regime trading gate or alter live BBC. Economics must be tested separately after this atlas is frozen.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
