from __future__ import annotations

from pathlib import Path
import sys
import math
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / 'research'
for p in (str(ROOT), str(RESEARCH)):
    if p not in sys.path:
        sys.path.insert(0, p)

import bnb_session_native_london_ny_long_m1_structure_b27em as b27em
import bnb_session_native_london_ny_long_m3_entry_b27eo as b27eo
import bnb_session_native_london_ny_long_m7_entry_economics_b27es as b27es

TARGET='BNBUSDT'
CAND='E5_MICRO_HL_BULL'
EXT_R=0.30
STOP_R=0.30
DEPTH_MAX_R=0.32452830188679327
NOTIONAL=500.0
BAR5=pd.Timedelta(minutes=5)
PFX='BNB_SESSION_NATIVE_LONDON_NY_LONG_M9_MICROHL_SHALLOW_B27EU'
OUT_DETAIL=ROOT/f'{PFX}_Detail.csv'
OUT_SUM=ROOT/f'{PFX}_Summary.csv'
OUT_MD=ROOT/f'{PFX}_Result.md'
OUT_STATUS=ROOT/f'{PFX}_Status.txt'


def build_external(x5):
    sessions=b27em.session_rows(x5)
    ext=sessions[(sessions.partition=='external') & sessions.leave.fillna(False).astype(bool)].copy()
    if len(ext)!=63:
        raise AssertionError(f'expected 63 external causal leaves, got {len(ext)}')
    if int((ext.terminal=='H2_ARRIVAL').sum())!=45:
        raise AssertionError('expected 45 external upstream H2')
    rows=[]
    exec_map={}
    for _,s in ext.iterrows():
        ny_open=pd.Timestamp(s.ny_open_utc); ny_close=pd.Timestamp(s.ny_close_utc)
        exe=b27em.fs(x5,ny_open,ny_close)
        H=float(s.H); L=float(s.L); R=float(s.R); leave_ts=pd.Timestamp(s.leave_ts)
        z=b27eo.discover_candidate(CAND,exe,leave_ts,H,L,R)
        if not bool(z.get('eligible',False)):
            continue
        entry_ts=pd.Timestamp(z['entry_ts'])
        entry_px=float(z['entry_px'])
        q=exe[exe.index>=entry_ts].copy()
        if q.empty:
            raise AssertionError(f'empty horizon {s.local_date}')
        sim=b27es.simulate_one(q,entry_px,H,R,EXT_R,STOP_R)
        rec={
            'local_date':str(s.local_date),'duration_regime':str(s.duration_regime),
            'entry_ts':entry_ts,'entry_px':entry_px,'H':H,'L':L,'R':R,
            'entry_depth_R':float(z['entry_depth_R']),
            'shallow':float(z['entry_depth_R'])<=DEPTH_MAX_R,
            'b27eo_h2':str(z['outcome'])=='H2_ARRIVAL',
            'exit_type':sim['exit_type'],'exit_ts':sim['exit_ts'],'gross_rr':sim['gross_rr'],
            'gross_return':sim['gross_return'],'net_return':sim['net_return'],'net_win':sim['net_win'],
            'pnl_usd_500':sim['pnl_usd_500'],'same_bar_collision':sim['same_bar_collision'],
        }
        # Strict-before-exit H diagnostic, matching B27ET.
        exit_ts=pd.Timestamp(sim['exit_ts'])
        pre=q[q.index<exit_ts] if sim['exit_type'] in ('SL','SL_BOTH') else q[q.index<=exit_ts]
        max_high=float(pre.high.max()) if len(pre) else np.nan
        rec['hit_H_strict_before_exit']=bool(not np.isnan(max_high) and max_high>=H)
        rec['sl_before_H']=bool(sim['exit_type'] in ('SL','SL_BOTH') and not rec['hit_H_strict_before_exit'])
        rows.append(rec)
        exec_map[str(s.local_date)]=q
    d=pd.DataFrame(rows).sort_values('entry_ts').reset_index(drop=True)
    if d.empty:
        raise AssertionError('no external E5 entries')
    return d


def max_drawdown(pnls):
    equity=0.0; peak=0.0; dd=0.0
    for v in pnls:
        equity+=float(v); peak=max(peak,equity); dd=max(dd,peak-equity)
    return dd


def summarize(name,q,raw_n):
    pnl=pd.to_numeric(q.pnl_usd_500,errors='coerce')
    pos=float(pnl[pnl>0].sum()); neg=float(-pnl[pnl<0].sum())
    pf=pos/neg if neg>0 else (math.inf if pos>0 else np.nan)
    losses=q[~q.net_win.astype(bool)]
    sl_before=int(losses.sl_before_H.sum()) if len(losses) else 0
    return {
        'cohort':name,'trades':len(q),'retention':len(q)/raw_n if raw_n else np.nan,
        'tp_exits':int((q.exit_type=='TP').sum()),
        'sl_exits':int(q.exit_type.isin(['SL','SL_BOTH']).sum()),
        'close_exits':int((q.exit_type=='SESSION_CLOSE').sum()),
        'same_bar_collisions':int(q.same_bar_collision.sum()),
        'net_wins':int(q.net_win.sum()),'net_win_rate':float(q.net_win.mean()),
        'avg_net_return':float(q.net_return.mean()),'total_pnl_usd_500':float(pnl.sum()),
        'profit_factor':pf,'max_drawdown_usd_500':max_drawdown(pnl.tolist()),
        'median_gross_rr':float(pd.to_numeric(q.gross_rr,errors='coerce').median()),
        'net_losses':len(losses),'sl_before_H_losses':sl_before,
        'sl_before_H_share_losses':sl_before/len(losses) if len(losses) else np.nan,
        'median_entry_depth_R':float(q.entry_depth_R.median()),
    }


def main():
    prereg=ROOT/f'{PFX}_Preregistration.md'
    if not prereg.exists(): raise AssertionError('B27EU preregistration missing')
    x5,cov=b27em.data_base.load5(TARGET)
    if cov<.995: raise AssertionError(f'coverage gate failed {cov}')
    d=build_external(x5); d.to_csv(OUT_DETAIL,index=False)
    raw=d.copy(); shallow=d[d.shallow].copy()
    rows=[summarize('RAW_MICRO_HL_EXTERNAL',raw,len(raw)), summarize('SHALLOW_MICRO_HL_EXTERNAL',shallow,len(raw))]
    s=pd.DataFrame(rows); s.to_csv(OUT_SUM,index=False)
    r=s.iloc[0]; h=s.iloc[1]
    delta=float(h.avg_net_return-r.avg_net_return)
    supported=(int(h.trades)>=10 and float(h.retention)>=.50 and float(h.avg_net_return)>0 and float(h.profit_factor)>1.0 and delta>=.0005)
    strong=bool(supported and float(h.profit_factor)>=1.20)
    verdict='STRONG_SUPPORT' if strong else ('SUPPORTED' if supported else 'NOT_SUPPORTED')
    lines=[
        '# BNB Session-Native LONG M9 MICRO_HL Shallow Guardrail — B27EU Result','',
        f'Raw BNB 5m coverage: **{cov:.4%}**.','',
        f'Frozen rule: **E5_MICRO_HL_BULL**, TP **H+0.30R**, SL **0.30R**, total cost **0.15%**, with one guardrail `entry_depth_R <= {DEPTH_MAX_R:.6f}R`.','',
        'Holdout: **external 2020-01-01 → 2022-01-01 only**.','',
        '## External economics','',
        '| Cohort | N | Retention | Net WR | Avg net/trade | Total PnL @ $500 | PF | Max DD | Median RR | SL-before-H share of losses | Med entry depth |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,z in s.iterrows():
        lines.append(f"| {z.cohort} | {int(z.trades)} | {100*z.retention:.1f}% | {100*z.net_win_rate:.1f}% | {100*z.avg_net_return:.3f}% | ${z.total_pnl_usd_500:.2f} | {z.profit_factor:.2f} | ${z.max_drawdown_usd_500:.2f} | {z.median_gross_rr:.2f} | {100*z.sl_before_H_share_losses:.1f}% | {z.median_entry_depth_R:.3f}R |")
    lines += ['', '## Preregistered support contract','',
              f'- Shallow N >= 10: **{int(h.trades)}** → {"PASS" if int(h.trades)>=10 else "FAIL"}',
              f'- Retention >= 50%: **{100*h.retention:.1f}%** → {"PASS" if h.retention>=.50 else "FAIL"}',
              f'- Shallow avg net > 0: **{100*h.avg_net_return:.3f}%** → {"PASS" if h.avg_net_return>0 else "FAIL"}',
              f'- Shallow PF > 1.0: **{h.profit_factor:.2f}** → {"PASS" if h.profit_factor>1 else "FAIL"}',
              f'- Avg-net improvement >= +0.050pp vs raw: **{100*delta:+.3f}pp** → {"PASS" if delta>=.0005 else "FAIL"}',
              f'- Strong-support PF >= 1.20: **{h.profit_factor:.2f}**','',
              f'**Verdict: {verdict}**','',
              'This is a frozen external replication of one development-derived guardrail; no alternate threshold is selected here.','',
              f'**Status: B27EU_BNB_MICROHL_SHALLOW_EXTERNAL_{verdict}**','',
              'STOP: no second feature, no threshold retuning, no reference-validation, no August, no SHORT/live integration.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    OUT_STATUS.write_text(f'B27EU_BNB_MICROHL_SHALLOW_EXTERNAL_{verdict}\n')
    print(OUT_MD.read_text())

if __name__=='__main__': main()
