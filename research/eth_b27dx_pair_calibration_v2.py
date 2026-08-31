#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BASE_PATH = HERE / 'eth_f85_f15_transfer_m2_causal_correction.py'
spec = importlib.util.spec_from_file_location('eth_causal_m2', BASE_PATH)
m = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m)

PFX = 'ETH_B27DX_PAIR_CALIBRATION_V2'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_DISC = ROOT / f'{PFX}_Discovery.csv'
OUT_ADV = ROOT / f'{PFX}_Advanced.csv'
OUT_VAL = ROOT / f'{PFX}_Validation.csv'
OUT_STRESS = ROOT / f'{PFX}_Stress.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
NOTIONAL = 500.0
FEE = 0.40
MAJOR_VAL = ('external', 'reference_validation')

EXEC_START_MIN = tuple(range(0, 24 * 60, 120))
REF_MINS = (180, 270, 330, 420)
HORIZON_MINS = (240, 390, 480)
LONG_ENTRIES = (0.95, 0.90, 0.85, 0.80, 0.75)
SHORT_ENTRIES = tuple(1.0 - x for x in LONG_ENTRIES)
TARGET_EXTS = (0.10, 0.20, 0.30)
LONG_STOPS = (0.50, 0.35, 0.20)
SHORT_STOPS = tuple(1.0 - x for x in LONG_STOPS)
SIDES = ('LONG', 'SHORT')


def fast_slice(x: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x.index.searchsorted(start, side='left'))
    b = int(x.index.searchsorted(end, side='left'))
    return x.iloc[a:b]


def partition(ts: pd.Timestamp) -> str | None:
    return m.m.part(ts)


def metrics(pnls: list[float]) -> dict:
    if not pnls:
        return {'n': 0, 'wins': 0, 'wr': np.nan, 'pf': np.nan, 'expectancy': np.nan, 'net': 0.0, 'max_ls': 0}
    a = np.asarray(pnls, dtype=float)
    pos = a[a > 0]
    neg = a[a < 0]
    gp = float(pos.sum()) if len(pos) else 0.0
    gl = float(-neg.sum()) if len(neg) else 0.0
    pf = math.inf if gl == 0.0 and gp > 0 else (gp / gl if gl > 0 else np.nan)
    wins = int((a > 0).sum())
    cur = mx = 0
    for z in a:
        if z < 0:
            cur += 1
            mx = max(mx, cur)
        else:
            cur = 0
    return {
        'n': int(len(a)), 'wins': wins, 'wr': wins / len(a), 'pf': pf,
        'expectancy': float(a.mean()), 'net': float(a.sum()), 'max_ls': int(mx)
    }


def entry_level(L: float, H: float, f: float) -> float:
    return L + f * (H - L)


def target_level(L: float, H: float, side: str, ext: float) -> float:
    R = H - L
    return H + ext * R if side == 'LONG' else L - ext * R


def stop_level(L: float, H: float, f: float) -> float:
    return L + f * (H - L)


def find_fill(exe: pd.DataFrame, w: dict, level: float) -> pd.Timestamp | None:
    if not bool(w.get('clean', False)):
        return None
    q = exe[exe.index >= pd.Timestamp(w['eligible_start'])]
    terminal = w.get('terminal_bar', pd.NaT)
    if pd.notna(terminal):
        q = q[q.index < pd.Timestamp(terminal)]
    for ts, r in q.iterrows():
        if float(r.low) <= level <= float(r.high):
            return pd.Timestamp(ts)
    return None


def time_exit_open(x: pd.DataFrame, ee: pd.Timestamp) -> float | None:
    pos = int(x.index.searchsorted(ee, side='left'))
    if pos >= len(x) or x.index[pos] != ee:
        return None
    return float(x.iloc[pos].open)


def score_trade(x: pd.DataFrame, exe: pd.DataFrame, fill_ts: pd.Timestamp, ee: pd.Timestamp,
                side: str, ep: float, target: float, stop: float,
                stress_bps: float = 0.0) -> tuple[float, str] | None:
    # Avoid unknown same-bar ordering: exit evaluation begins on the next completed 5m bar.
    q = exe[exe.index >= fill_ts + BAR5]
    reason = None
    xp = None
    for ts, r in q.iterrows():
        if side == 'LONG':
            if float(r.high) >= target:
                xp = target; reason = 'TARGET'; break
            if float(r.close) < stop:
                xp = float(r.close); reason = 'CLOSE_INVALIDATION'; break
        else:
            if float(r.low) <= target:
                xp = target; reason = 'TARGET'; break
            if float(r.close) > stop:
                xp = float(r.close); reason = 'CLOSE_INVALIDATION'; break
    if reason is None:
        xp = time_exit_open(x, ee)
        if xp is None:
            return None
        reason = 'TIME_EXIT'

    bps = stress_bps / 10000.0
    if side == 'LONG':
        entry_exec = ep * (1.0 + bps)
        exit_exec = xp if reason == 'TARGET' else xp * (1.0 - bps)
        gross = exit_exec / entry_exec - 1.0
    else:
        entry_exec = ep * (1.0 - bps)
        exit_exec = xp if reason == 'TARGET' else xp * (1.0 + bps)
        gross = (entry_exec - exit_exec) / entry_exec
    pnl = NOTIONAL * gross - FEE
    return float(pnl), reason


def sessions_for(x: pd.DataFrame, part_name: str, exec_min: int, ref_min: int,
                 horizon_min: int, side: str, entry_f: float) -> list[dict]:
    a, z = m.m.PARTS[part_name]
    rows = []
    start_day = a.normalize()
    end_day = min(z, m.m.END).normalize()
    for day in pd.date_range(start_day, end_day, freq='D', tz='UTC'):
        es = day + pd.Timedelta(minutes=exec_min)
        if not (a <= es < z) or es.weekday() >= 5:
            continue
        rs = es - pd.Timedelta(minutes=ref_min)
        ee = es + pd.Timedelta(minutes=horizon_min)
        if rs < m.m.START or ee >= m.m.END:
            continue
        ref = fast_slice(x, rs, es)
        exe = fast_slice(x, es, ee)
        if len(ref) != ref_min // 5 or len(exe) != horizon_min // 5:
            continue
        H = float(ref.high.max()); L = float(ref.low.min())
        if not H > L:
            continue
        w = m.corrected_find_window(exe, H, L, side)
        if w is None or not bool(w.get('clean', False)):
            continue
        ep = entry_level(L, H, entry_f)
        fill = find_fill(exe, w, ep)
        if fill is None:
            continue
        rows.append({'es': es, 'ee': ee, 'H': H, 'L': L, 'entry': ep, 'fill_ts': fill, 'exe': exe})
    return rows


def config_id(side: str, exec_min: int, ref_min: int, horizon_min: int,
              entry_f: float, target_ext: float, stop_f: float) -> str:
    return f'{side}|E{exec_min:04d}|R{ref_min}|X{horizon_min}|F{entry_f:.2f}|T{target_ext:.2f}|S{stop_f:.2f}'


def score_config(x: pd.DataFrame, part_name: str, side: str, exec_min: int, ref_min: int,
                 horizon_min: int, entry_f: float, target_ext: float, stop_f: float,
                 stress_bps: float = 0.0, cached: list[dict] | None = None) -> dict:
    sess = cached if cached is not None else sessions_for(x, part_name, exec_min, ref_min, horizon_min, side, entry_f)
    pnls = []
    targets = stops = times = 0
    for s in sess:
        target = target_level(s['L'], s['H'], side, target_ext)
        stop = stop_level(s['L'], s['H'], stop_f)
        out = score_trade(x, s['exe'], s['fill_ts'], s['ee'], side, s['entry'], target, stop, stress_bps)
        if out is None:
            continue
        pnl, reason = out
        pnls.append(pnl)
        targets += reason == 'TARGET'
        stops += reason == 'CLOSE_INVALIDATION'
        times += reason == 'TIME_EXIT'
    d = metrics(pnls)
    d.update({
        'partition': part_name, 'side': side, 'exec_min': exec_min, 'ref_min': ref_min,
        'horizon_min': horizon_min, 'entry_f': entry_f, 'target_ext': target_ext,
        'stop_f': stop_f, 'stress_bps': stress_bps, 'targets': int(targets),
        'stops': int(stops), 'time_exits': int(times),
        'config_id': config_id(side, exec_min, ref_min, horizon_min, entry_f, target_ext, stop_f)
    })
    return d


def discovery(x: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for side in SIDES:
        entries = LONG_ENTRIES if side == 'LONG' else SHORT_ENTRIES
        stops = LONG_STOPS if side == 'LONG' else SHORT_STOPS
        for exec_min in EXEC_START_MIN:
            for ref_min in REF_MINS:
                for horizon_min in HORIZON_MINS:
                    for ef in entries:
                        sess = sessions_for(x, 'development', exec_min, ref_min, horizon_min, side, ef)
                        if len(sess) < 40:
                            continue
                        for te in TARGET_EXTS:
                            for sf in stops:
                                rows.append(score_config(x, 'development', side, exec_min, ref_min,
                                                         horizon_min, ef, te, sf, 0.0, sess))
    return pd.DataFrame(rows)


def choose_advanced(D: pd.DataFrame) -> pd.DataFrame:
    if D.empty:
        return D.copy()
    eligible = D[(D.n >= 40) & (D.wr >= .60) & (D.pf >= 1.25) &
                 (D.expectancy > 0) & (D.net > 0)].copy()
    if eligible.empty:
        return eligible
    eligible['_pf_rank'] = eligible.pf.replace([np.inf], 999999.0)
    eligible = eligible.sort_values(['_pf_rank', 'expectancy', 'n'], ascending=[False, False, False])
    # One parameter set per side x habitat x reference duration.
    eligible = eligible.drop_duplicates(['side', 'exec_min', 'ref_min'], keep='first')
    eligible = eligible.head(12).drop(columns=['_pf_rank'])
    return eligible.reset_index(drop=True)


def validate(x: pd.DataFrame, A: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    vals = []
    stress = []
    for _, c in A.iterrows():
        args = dict(side=str(c.side), exec_min=int(c.exec_min), ref_min=int(c.ref_min),
                    horizon_min=int(c.horizon_min), entry_f=float(c.entry_f),
                    target_ext=float(c.target_ext), stop_f=float(c.stop_f))
        part_rows = []
        for p in (*MAJOR_VAL, 'august'):
            r = score_config(x, p, **args)
            vals.append(r); part_rows.append(r)
        ok_parts = []
        for p in MAJOR_VAL:
            r = next(z for z in part_rows if z['partition'] == p)
            ok_parts.append(r['n'] >= 15 and r['wr'] >= .55 and r['pf'] >= 1.10 and r['expectancy'] > 0 and r['net'] > 0)
        pooled_pnls = []
        # Re-score pooled validation directly to preserve trade-level economics.
        pooled_rows = []
        for p in MAJOR_VAL:
            sess = sessions_for(x, p, args['exec_min'], args['ref_min'], args['horizon_min'], args['side'], args['entry_f'])
            for s in sess:
                target = target_level(s['L'], s['H'], args['side'], args['target_ext'])
                stop = stop_level(s['L'], s['H'], args['stop_f'])
                out = score_trade(x, s['exe'], s['fill_ts'], s['ee'], args['side'], s['entry'], target, stop, 0.0)
                if out is not None:
                    pooled_pnls.append(out[0])
        pm = metrics(pooled_pnls)
        pooled_gate = pm['n'] > 0 and pm['wr'] >= .60 and pm['pf'] >= 1.25 and pm['expectancy'] > 0
        survivor = bool(all(ok_parts) and pooled_gate)
        vals.append({**args, **pm, 'partition': 'POOLED_VALIDATION', 'stress_bps': 0.0,
                     'targets': np.nan, 'stops': np.nan, 'time_exits': np.nan,
                     'config_id': str(c.config_id), 'survivor': survivor})
        if survivor:
            spnls = []
            for p in MAJOR_VAL:
                sess = sessions_for(x, p, args['exec_min'], args['ref_min'], args['horizon_min'], args['side'], args['entry_f'])
                for s in sess:
                    target = target_level(s['L'], s['H'], args['side'], args['target_ext'])
                    stop = stop_level(s['L'], s['H'], args['stop_f'])
                    out = score_trade(x, s['exe'], s['fill_ts'], s['ee'], args['side'], s['entry'], target, stop, 5.0)
                    if out is not None:
                        spnls.append(out[0])
            sm = metrics(spnls)
            stress.append({**args, **sm, 'partition': 'POOLED_VALIDATION', 'stress_bps': 5.0,
                           'config_id': str(c.config_id),
                           'stress_pass': bool(sm['n'] > 0 and sm['pf'] >= 1.0 and sm['net'] >= 0)})
    return pd.DataFrame(vals), pd.DataFrame(stress)


def f_pct(x):
    return '-' if pd.isna(x) else f'{100 * float(x):.1f}%'


def f_num(x):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.2f}'


def main():
    x, cov = m.m.load5()
    D = discovery(x)
    D.to_csv(OUT_DISC, index=False)
    A = choose_advanced(D)
    A.to_csv(OUT_ADV, index=False)
    V, S = validate(x, A)
    V.to_csv(OUT_VAL, index=False)
    S.to_csv(OUT_STRESS, index=False)

    survivors = []
    if not V.empty and 'survivor' in V.columns:
        pv = V[(V.partition == 'POOLED_VALIDATION') & (V.survivor == True)]
        stress_ok = set(S.loc[S.stress_pass == True, 'config_id'].astype(str)) if not S.empty else set()
        survivors = [z for z in pv.config_id.astype(str).tolist() if z in stress_ok]

    status = 'ETH_B27DX_PAIR_CALIBRATION_V2_SURVIVOR_FOUND' if survivors else 'ETH_B27DX_PAIR_CALIBRATION_V2_NO_SURVIVOR'
    OUT_STATUS.write_text(status + '\n')

    lines = [
        '# ETH B27DX Pair Calibration V2 — Result', '',
        f'Raw ETH 5m coverage: **{cov:.4%}**.',
        '', 'Primary objective: profitable executable trades. H/H2 is not a ranking metric.', '',
        f'Development configurations scored: **{len(D):,}**.',
        f'Frozen candidates advanced to untouched validation: **{len(A)}**.',
        f'Final survivors after validation + 5 bps stress: **{len(survivors)}**.', ''
    ]
    if len(A):
        lines += ['## Advanced candidates', '', '| Config | Dev N | WR | PF | Exp | Net |', '|---|---:|---:|---:|---:|---:|']
        for _, r in A.iterrows():
            lines.append(f"| {r.config_id} | {int(r.n)} | {f_pct(r.wr)} | {f_num(r.pf)} | ${float(r.expectancy):+.2f} | ${float(r.net):+.2f} |")
        lines.append('')
    if survivors:
        lines += ['## Final survivors', '']
        for cid in survivors:
            r = V[(V.config_id == cid) & (V.partition == 'POOLED_VALIDATION')].iloc[0]
            s = S[S.config_id == cid].iloc[0]
            lines.append(f"- **{cid}** — validation N {int(r.n)}, WR {f_pct(r.wr)}, PF {f_num(r.pf)}, net ${float(r.net):+.2f}; 5bps PF {f_num(s.pf)}, net ${float(s.net):+.2f}.")
        lines.append('')
    lines += [f'**Status: {status}**', '', 'Research only. No live BBC changes.']
    OUT_MD.write_text('\n'.join(lines) + '\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
