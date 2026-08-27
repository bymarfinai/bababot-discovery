#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
PFX = 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_M7'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_SEL = ROOT / f'{PFX}_Selection.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

LOCKED = {
    'ALT_0330': ('F95', 0.95),
    'RAW_0530': ('F90', 0.90),
    'LONDON': ('F90', 0.90),
    'RAW_2330': ('F95', 0.95),
}
EXTS = [0.05,0.10,0.15,0.20,0.25,0.30,0.40,0.50]
MAJOR = ('external','development','reference_validation')

spec = importlib.util.spec_from_file_location('eth_m2_base', HERE / 'eth_f85_f15_transfer_m2_pre_h2_entry_grid.py')
m = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m)


def corrected_find_window(exe, H, L, side):
    hi_touch = lo_touch = False
    hi_vis = lo_vis = 0
    state = 'SEEK'
    k1 = pd.NaT
    leave_bar = pd.NaT
    eligible_start = pd.NaT
    for ts, r in exe.iterrows():
        hi, lo, cl = float(r.high), float(r.low), float(r.close)
        if state == 'SEEK':
            if cl > H or cl < L:
                return None
            hh = hi >= H and cl <= H
            ll = lo <= L and cl >= L
            if hh and ll:
                return None
            if side == 'LONG':
                if ll and not lo_touch:
                    lo_vis += 1
                if hh and not hi_touch:
                    hi_vis += 1
                    if hi_vis == 1 and lo_vis == 0:
                        k1 = ts
                        state = 'EP'
                hi_touch, lo_touch = hh, ll
                if lo_vis > 0 and state == 'SEEK':
                    return None
            else:
                if hh and not hi_touch:
                    hi_vis += 1
                if ll and not lo_touch:
                    lo_vis += 1
                    if lo_vis == 1 and hi_vis == 0:
                        k1 = ts
                        state = 'EP'
                hi_touch, lo_touch = hh, ll
                if hi_vis > 0 and state == 'SEEK':
                    return None
            continue
        if state == 'EP':
            if cl > H or cl < L:
                return {'k1':k1,'clean':False,'leave_bar':pd.NaT,'eligible_start':pd.NaT,
                        'terminal':'BREAK_DURING_K1','terminal_bar':ts}
            same = (hi >= H and cl <= H) if side == 'LONG' else (lo <= L and cl >= L)
            if same:
                continue
            leave_bar = ts
            eligible_start = ts + m.BAR5
            state = 'POST'
            continue
        if state == 'POST':
            h2 = (hi >= H) if side == 'LONG' else (lo <= L)
            opp = (cl < L) if side == 'LONG' else (cl > H)
            if h2 and opp:
                term = 'AMBIGUOUS'
            elif h2:
                term = 'H2'
            elif opp:
                term = 'OPPOSITE'
            else:
                continue
            return {'k1':k1,'clean':True,'leave_bar':leave_bar,'eligible_start':eligible_start,
                    'terminal':term,'terminal_bar':ts}
    if state == 'EP':
        return {'k1':k1,'clean':False,'leave_bar':pd.NaT,'eligible_start':pd.NaT,
                'terminal':'NO_LEAVE','terminal_bar':pd.NaT}
    if state == 'POST':
        return {'k1':k1,'clean':True,'leave_bar':leave_bar,'eligible_start':eligible_start,
                'terminal':'NO_H2','terminal_bar':pd.NaT}
    return None


def extension_metrics(post, H, R, h2_ts):
    out = {}
    out['max_high_ext'] = (float(post.high.max()) - H) / R
    out['max_close_ext'] = (float(post.close.max()) - H) / R
    z = post[post.close > H]
    out['first_close_break_ts'] = z.index[0] if len(z) else pd.NaT
    for e in EXTS:
        tag = f'E{int(round(e*100)):02d}'
        px = H + e*R
        wh = post[post.high >= px]
        ch = post[post.close >= px]
        out[f'{tag}_price'] = px
        out[f'{tag}_wick_reach'] = bool(len(wh))
        out[f'{tag}_close_accept'] = bool(len(ch))
        out[f'{tag}_first_wick_ts'] = wh.index[0] if len(wh) else pd.NaT
        out[f'{tag}_first_close_ts'] = ch.index[0] if len(ch) else pd.NaT
        out[f'{tag}_min_h2_to_wick'] = float((wh.index[0]-h2_ts)/pd.Timedelta(minutes=1)) if len(wh) else np.nan
    return out


def synthetic_tests():
    idx = pd.date_range('2026-01-05 12:00', periods=3, freq='5min', tz='UTC')
    post = pd.DataFrame([
        [100.0,101.1,99.8,100.5],
        [100.5,102.5,100.2,102.1],
        [102.1,104.2,101.9,103.0],
    ], index=idx, columns=['open','high','low','close'])
    a = extension_metrics(post,100.0,10.0,idx[0])
    assert a['E10_wick_reach'] and a['E10_first_wick_ts'] == idx[0]
    assert not a['E10_close_accept'] or a['E10_first_close_ts'] >= idx[0]
    assert a['E20_wick_reach'] and a['E20_first_wick_ts'] == idx[1]
    assert not a['E50_wick_reach']


def main():
    synthetic_tests()
    assert set(LOCKED) == {'ALT_0330','RAW_0530','LONDON','RAW_2330'}
    x, cov = m.load5()
    assert cov >= .995
    details = []
    for d in pd.date_range(m.START.normalize(), m.END.normalize(), freq='D', tz='UTC'):
        for clock, (lvl, f) in LOCKED.items():
            cm = m.CLOCKS[clock]
            rs = d + pd.Timedelta(minutes=cm)
            re = rs + m.REF
            es = re
            ee = es + m.EXE
            p = m.part(es)
            if p is None or es.weekday() >= 5 or ee > m.END:
                continue
            ref = m.sl(x, rs, re)
            exe = m.sl(x, es, ee)
            if len(ref) != 66 or len(exe) != 78:
                continue
            H = float(ref.high.max()); L = float(ref.low.min()); R = H-L
            if R <= 0:
                continue
            w = corrected_find_window(exe,H,L,'LONG')
            if w is None or not w['clean']:
                continue
            c = m.candidate(exe,H,L,w,'LONG',lvl,f)
            if not c['filled']:
                continue
            row = {
                'clock':clock,'level':lvl,'fraction':f,'partition':p,
                'reference_start':rs,'execution_start':es,'execution_end':ee,
                'H':H,'L':L,'R':R,'fill_ts':c['fill_ts'],'m2_outcome':c['outcome'],
                'h2':bool(c['outcome']=='H2'),'h2_ts':w['terminal_bar'] if c['outcome']=='H2' else pd.NaT,
            }
            if c['outcome'] == 'H2':
                h2_ts = w['terminal_bar']
                assert pd.notna(h2_ts) and c['fill_ts'] < h2_ts
                post = exe[exe.index >= h2_ts]
                assert len(post) and post.index[0] == h2_ts and post.index[-1] < ee
                row.update(extension_metrics(post,H,R,h2_ts))
            else:
                row['max_high_ext'] = np.nan; row['max_close_ext'] = np.nan
                row['first_close_break_ts'] = pd.NaT
                for e in EXTS:
                    tag=f'E{int(round(e*100)):02d}'
                    row[f'{tag}_price']=H+e*R
                    row[f'{tag}_wick_reach']=False
                    row[f'{tag}_close_accept']=False
                    row[f'{tag}_first_wick_ts']=pd.NaT
                    row[f'{tag}_first_close_ts']=pd.NaT
                    row[f'{tag}_min_h2_to_wick']=np.nan
            details.append(row)
    D = pd.DataFrame(details)
    if D.empty:
        raise RuntimeError('no locked M7 entries')
    D.to_csv(OUT_DETAIL,index=False)

    rows=[]
    for clock,(lvl,f) in LOCKED.items():
        base = D[(D['clock']==clock)&(D['level']==lvl)]
        for e in EXTS:
            tag=f'E{int(round(e*100)):02d}'
            for p in ('external','development','reference_validation','august','POOLED_MAJOR'):
                g = base[base['partition'].isin(MAJOR)] if p=='POOLED_MAJOR' else base[base['partition']==p]
                h = g[g['h2']]
                fills=len(g); hn=len(h)
                wr=int(g[f'{tag}_wick_reach'].sum()) if fills else 0
                cr=int(g[f'{tag}_close_accept'].sum()) if fills else 0
                rows.append({
                    'clock':clock,'level':lvl,'target':tag,'extension':e,'partition':p,
                    'fills':fills,'h2_n':hn,'h2_rate':hn/fills if fills else np.nan,
                    'wick_reach_n':wr,'wick_reach_all':wr/fills if fills else np.nan,
                    'wick_reach_given_h2':wr/hn if hn else np.nan,
                    'close_accept_n':cr,'close_accept_all':cr/fills if fills else np.nan,
                    'close_accept_given_h2':cr/hn if hn else np.nan,
                    'first_close_break_given_h2':float(h['first_close_break_ts'].notna().mean()) if hn else np.nan,
                    'median_h2_to_wick_min':pd.to_numeric(h.loc[h[f'{tag}_wick_reach'],f'{tag}_min_h2_to_wick'],errors='coerce').median() if wr else np.nan,
                    'median_fill_to_wick_min':float(((pd.to_datetime(g.loc[g[f'{tag}_wick_reach'],f'{tag}_first_wick_ts'])-pd.to_datetime(g.loc[g[f'{tag}_wick_reach'],'fill_ts']))/pd.Timedelta(minutes=1)).median()) if wr else np.nan,
                    'max_high_ext_p25':pd.to_numeric(h['max_high_ext'],errors='coerce').quantile(.25) if hn else np.nan,
                    'max_high_ext_p50':pd.to_numeric(h['max_high_ext'],errors='coerce').quantile(.50) if hn else np.nan,
                    'max_high_ext_p75':pd.to_numeric(h['max_high_ext'],errors='coerce').quantile(.75) if hn else np.nan,
                    'max_high_ext_p90':pd.to_numeric(h['max_high_ext'],errors='coerce').quantile(.90) if hn else np.nan,
                    'max_close_ext_p50':pd.to_numeric(h['max_close_ext'],errors='coerce').quantile(.50) if hn else np.nan,
                    'session_end_unresolved_given_h2':1-(wr/hn) if hn else np.nan,
                })
    S=pd.DataFrame(rows)
    S.to_csv(OUT_SUM,index=False)

    selections=[]
    for clock,(lvl,f) in LOCKED.items():
        passing=[]
        for e in EXTS:
            tag=f'E{int(round(e*100)):02d}'
            major=S[(S['clock']==clock)&(S['level']==lvl)&(S['target']==tag)&(S['partition'].isin(MAJOR))]
            pooled=S[(S['clock']==clock)&(S['level']==lvl)&(S['target']==tag)&(S['partition']=='POOLED_MAJOR')].iloc[0]
            ok=(len(major)==3 and (major['h2_n']>=20).all() and
                (major['wick_reach_given_h2']>=.60).all() and
                float(pooled['wick_reach_given_h2'])>=.70 and
                float(pooled['wick_reach_all'])>=.55 and
                float(pooled['close_accept_given_h2'])>=.50)
            if ok:
                passing.append((e,tag,pooled))
        if passing:
            e,tag,pooled=max(passing,key=lambda z:z[0])
            selections.append({'clock':clock,'level':lvl,'selection':'TARGET_CANDIDATE','target':tag,'extension':e,
                               'pooled_fills':int(pooled['fills']),'pooled_h2_rate':float(pooled['h2_rate']),
                               'wick_reach_given_h2':float(pooled['wick_reach_given_h2']),
                               'wick_reach_all':float(pooled['wick_reach_all']),
                               'close_accept_given_h2':float(pooled['close_accept_given_h2']),
                               'median_h2_to_wick_min':float(pooled['median_h2_to_wick_min']) if pd.notna(pooled['median_h2_to_wick_min']) else np.nan})
        else:
            selections.append({'clock':clock,'level':lvl,'selection':'TARGET_NOT_LOCKED','target':'','extension':np.nan,
                               'pooled_fills':len(D[(D['clock']==clock)&(D['level']==lvl)]),'pooled_h2_rate':np.nan,
                               'wick_reach_given_h2':np.nan,'wick_reach_all':np.nan,'close_accept_given_h2':np.nan,'median_h2_to_wick_min':np.nan})
    SEL=pd.DataFrame(selections)
    SEL.to_csv(OUT_SEL,index=False)

    status='ETH_M7_TARGET_ATLAS_COMPLETED'
    OUT_STATUS.write_text(status+'\n')
    lines=['# ETH Transfer — M7 Post-H2 Target / Exit Atlas — Result','',f'Raw ETH 5m coverage: **{cov:.4%}**.','',
           'H2 remains a milestone, not TP. Structural target discovery only; no M6 stop, PnL, PF, fees, leverage, or M8.','',
           '| Habitat | Entry | Structural target candidate | Pooled H2 | Reach given H2 | Reach all entries | Close acceptance given H2 | Median H2→target |',
           '|---|---|---|---:|---:|---:|---:|---:|']
    for _,r in SEL.iterrows():
        if r['selection']=='TARGET_CANDIDATE':
            lines.append(f"| {r['clock']} | {r['level']} | **{r['target']}** | {100*r['pooled_h2_rate']:.1f}% | {100*r['wick_reach_given_h2']:.1f}% | {100*r['wick_reach_all']:.1f}% | {100*r['close_accept_given_h2']:.1f}% | {r['median_h2_to_wick_min']:.1f}m |")
        else:
            lines.append(f"| {r['clock']} | {r['level']} | NONE | - | - | - | - | - |")
    lines += ['',f'**Status: {status}**','','Stop after M7. No economic combination was run automatically.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
