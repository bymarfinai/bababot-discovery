#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BASE_PATH = HERE / 'eth_f85_f15_transfer_m2_pre_h2_entry_grid.py'
spec = importlib.util.spec_from_file_location('eth_m2_base', BASE_PATH)
m = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m)

PFX='ETH_LONDON_F85_BREAKOUT_ENTRY_M3D'
OUT_MD=ROOT/f'{PFX}_Result.md'
OUT_TRADES=ROOT/f'{PFX}_Trades.csv'
OUT_SUM=ROOT/f'{PFX}_Summary.csv'
OUT_STATUS=ROOT/f'{PFX}_Status.txt'
M3B_CASES=ROOT/'ETH_LONDON_F85_BREAKOUT_SEQUENCE_M3B_Cases.csv'
M3B_STATUS=ROOT/'ETH_LONDON_F85_BREAKOUT_SEQUENCE_M3B_Status.txt'
REQ='ETH_LONDON_F85_BREAKOUT_SEQUENCE_M3B_COMPLETED'
MAJOR=('external','development','reference_validation')
NOTIONAL=500.0
FEE=0.40
SLIP=0.0005


def raw_slice(x,start,end):
    i=int(x.index.searchsorted(start,'left')); j=int(x.index.searchsorted(end,'left'))
    return x.iloc[i:j]


def pnl_long(entry,exit_):
    return NOTIONAL*(exit_/entry-1.0)-FEE


def score_trade(x,r):
    H=float(r.H); L=float(r.L); R=H-L
    E20=H+0.20*R; F35=L+0.35*R
    breakout_ts=pd.Timestamp(r.breakout_ts)
    execution_start=pd.Timestamp(r.execution_start)
    execution_end=execution_start+m.EXE
    entry_ts=breakout_ts+m.BAR5
    out={'partition':r.partition,'reference_start':r.reference_start,'execution_start':execution_start,
         'breakout_ts':breakout_ts,'entry_ts':entry_ts,'H':H,'L':L,'R':R,'E20':E20,'F35':F35,
         'eligible':False,'skip_reason':'','entry_price':np.nan,'exit_ts':pd.NaT,'exit_price':np.nan,
         'exit_reason':'','net_pnl':np.nan,'win':False,'net_pnl_5bps':np.nan,'win_5bps':False}
    if entry_ts>=execution_end:
        out['skip_reason']='NO_NEXT_BAR_INSIDE_SESSION'; return out
    if entry_ts not in x.index:
        out['skip_reason']='MISSING_ENTRY_BAR'; return out
    entry=float(x.loc[entry_ts,'open'])
    out['entry_price']=entry
    if entry>=E20:
        out['skip_reason']='ENTRY_OPEN_AT_OR_ABOVE_TARGET'; return out
    out['eligible']=True
    q=raw_slice(x,entry_ts,execution_end)
    exit_ts=pd.NaT; exit_px=np.nan; reason=''
    for ts,b in q.iterrows():
        if float(b.high)>=E20:
            exit_ts=ts; exit_px=E20; reason='TARGET_E20'; break
        if float(b.close)<F35:
            exit_ts=ts; exit_px=float(b.close); reason='CLOSE_BELOW_F35'; break
    if pd.isna(exit_ts):
        if execution_end not in x.index:
            out['eligible']=False; out['skip_reason']='MISSING_TIME_EXIT_BAR'; return out
        exit_ts=execution_end; exit_px=float(x.loc[execution_end,'open']); reason='SESSION_END'
    net=pnl_long(entry,exit_px)
    # 5 bps adverse execution sensitivity: worse entry and worse exit.
    entry5=entry*(1+SLIP); exit5=exit_px*(1-SLIP)
    net5=pnl_long(entry5,exit5)
    out.update({'exit_ts':exit_ts,'exit_price':exit_px,'exit_reason':reason,'net_pnl':net,'win':net>0,
                'net_pnl_5bps':net5,'win_5bps':net5>0})
    return out


def max_loss_streak(z,wincol):
    if z.empty:return 0
    z=z.sort_values(['entry_ts','reference_start'])
    cur=mx=0
    for w in z[wincol].astype(bool):
        if w:cur=0
        else:cur+=1;mx=max(mx,cur)
    return mx


def summarize(t,part):
    z=t[t.partition.isin(MAJOR)] if part=='POOLED_MAJOR' else t[t.partition==part]
    z=z[z.eligible.astype(bool)].copy().sort_values('entry_ts')
    n=len(z); wins=int(z.win.sum()) if n else 0
    gp=float(z.loc[z.net_pnl>0,'net_pnl'].sum()) if n else 0.0
    gl=float(-z.loc[z.net_pnl<0,'net_pnl'].sum()) if n else 0.0
    gp5=float(z.loc[z.net_pnl_5bps>0,'net_pnl_5bps'].sum()) if n else 0.0
    gl5=float(-z.loc[z.net_pnl_5bps<0,'net_pnl_5bps'].sum()) if n else 0.0
    return {'partition':part,'N':n,'wins':wins,'losses':n-wins,'WR':wins/n if n else np.nan,
            'PF':gp/gl if gl>0 else np.inf if gp>0 else np.nan,'net':float(z.net_pnl.sum()) if n else 0.0,
            'expectancy':float(z.net_pnl.mean()) if n else np.nan,'max_loss_streak':max_loss_streak(z,'win'),
            'target':int((z.exit_reason=='TARGET_E20').sum()),'f35':int((z.exit_reason=='CLOSE_BELOW_F35').sum()),
            'session_end':int((z.exit_reason=='SESSION_END').sum()),
            'WR_5bps':float(z.win_5bps.mean()) if n else np.nan,
            'PF_5bps':gp5/gl5 if gl5>0 else np.inf if gp5>0 else np.nan,
            'net_5bps':float(z.net_pnl_5bps.sum()) if n else 0.0,'max_loss_streak_5bps':max_loss_streak(z,'win_5bps')}


def fmt_pct(v): return '-' if pd.isna(v) else f'{100*v:.1f}%'
def fmt_num(v): return '-' if pd.isna(v) else f'{v:.2f}'


def main():
    if not M3B_STATUS.exists() or M3B_STATUS.read_text().strip()!=REQ:
        raise RuntimeError('M3B status gate not satisfied')
    c=pd.read_csv(M3B_CASES)
    for col in ['reference_start','execution_start','breakout_ts']:
        c[col]=pd.to_datetime(c[col],utc=True,errors='coerce')
    br=c[c.partition.isin(MAJOR) & c.breakout.astype(str).str.lower().isin(['true','1'])].copy()
    if len(br)!=120:
        raise RuntimeError(f'Expected 120 pooled-major breakouts from M3B, got {len(br)}')
    x,cov=m.load5()
    if cov<.995:raise RuntimeError(f'coverage below gate {cov:.6%}')
    t=pd.DataFrame([score_trade(x,r) for _,r in br.iterrows()])
    t.to_csv(OUT_TRADES,index=False)
    parts=['external','development','reference_validation','POOLED_MAJOR']
    s=pd.DataFrame([summarize(t,p) for p in parts]);s.to_csv(OUT_SUM,index=False)
    p=s[s.partition=='POOLED_MAJOR'].iloc[0]
    skips=t[~t.eligible.astype(bool)].skip_reason.value_counts().to_dict()
    lines=['# ETH London F85 — Breakout Entry Trading Test M3D — Result','',
           f'Raw ETH 5-minute coverage: **{cov:.4%}**.',
           'Trading rule: confirmed breakout -> next 5m open entry; target E20; completed close below F35 invalidates; otherwise exit at session end.',
           f'Illustrative notional **${NOTIONAL:.0f}**, round-trip fee **${FEE:.2f}**.','',
           '## Hasil trading','',
           '| Periode | Trade | Win | Loss | WR | PF | Net | Rata-rata / trade | Loss beruntun maks |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    names={'external':'2020-2021','development':'2022-2024','reference_validation':'2025-Jul 2026','POOLED_MAJOR':'Semua periode utama'}
    for _,r in s.iterrows():
        lines.append(f"| {names[r.partition]} | {int(r.N)} | {int(r.wins)} | {int(r.losses)} | {fmt_pct(r.WR)} | {fmt_num(r.PF)} | ${r.net:+.2f} | ${r.expectancy:+.2f} | {int(r.max_loss_streak)} |")
    lines += ['', '## Cara trade berakhir', '',
              '| Akhir trade | Jumlah |', '|---|---:|',
              f"| Target E20 kena | {int(p.target)} |",
              f"| Close di bawah F35 | {int(p.f35)} |",
              f"| Masih terbuka sampai sesi selesai | {int(p.session_end)} |", '',
              '## Sensitivitas slippage 5 bps', '',
              '| Trade | WR | PF | Net | Loss beruntun maks |','|---:|---:|---:|---:|---:|',
              f"| {int(p.N)} | {fmt_pct(p.WR_5bps)} | {fmt_num(p.PF_5bps)} | ${p.net_5bps:+.2f} | {int(p.max_loss_streak_5bps)} |", '']
    if skips:
        lines += ['Skipped breakout cases: '+', '.join(f'{k}={v}' for k,v in skips.items())+'.','']
    lines += ['**Status: ETH_LONDON_F85_BREAKOUT_ENTRY_M3D_COMPLETED**','',
              'Research only. No parameter optimization and no live BBC change. Stop after M3D.']
    OUT_MD.write_text('\n'.join(lines)+'\n');OUT_STATUS.write_text('ETH_LONDON_F85_BREAKOUT_ENTRY_M3D_COMPLETED\n')
    print(OUT_MD.read_text())

if __name__=='__main__':main()
