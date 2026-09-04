#!/usr/bin/env python3
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
INFILE = ROOT / 'SOL_LONG_THREE_ZONE_BENCHMARK_A24_COMPONENTS.csv'
OUT = ROOT / 'SOL_LONG_THREE_ZONE_METRICS_A25B_ZONES.md'
STATUS = ROOT / 'SOL_LONG_THREE_ZONE_METRICS_A25B_Status.txt'
ZONES = [('03UTC_PARENT','03UTC/R420 parent'),('15UTC_PARENT','15UTC/R360 parent'),('18UTC_MATURE','18UTC/R240 parent + H2 entries')]
PARTS = ['development','external','reference_validation']
YEARS = {'development':3.0,'external':2.0,'reference_validation':(pd.Timestamp('2026-07-30',tz='UTC')-pd.Timestamp('2025-01-01',tz='UTC'))/pd.Timedelta(days=365.2425)}

def pf(x):
    x=pd.to_numeric(x,errors='coerce').dropna(); gp=float(x[x>0].sum()); gl=float(-x[x<=0].sum())
    return np.inf if gl==0 and gp>0 else (np.nan if gl==0 else gp/gl)

def streak(vals, win=False):
    b=c=0
    for v in vals:
        ok=float(v)>0 if win else float(v)<=0
        c=c+1 if ok else 0; b=max(b,c)
    return b

def dd(q,col):
    z=q.sort_values(['exit_ts','entry_ts']); eq=pd.to_numeric(z[col],errors='coerce').fillna(0).cumsum(); peak=eq.cummax().clip(lower=0)
    return float((peak-eq).max()) if len(eq) else 0.0

def weekly(q,col):
    z=q.copy(); z['wk']=z.exit_ts.dt.to_period('W-MON').dt.start_time.dt.tz_localize('UTC'); return z.groupby('wk')[col].sum().sort_index()

def daily(q,col):
    z=q.copy(); z['dy']=z.exit_ts.dt.floor('D'); return z.groupby('dy')[col].sum().sort_index()

def fmt(v):
    if pd.isna(v): return '-'
    if np.isinf(v): return 'inf'
    return f'{float(v):.2f}'

def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'

q=pd.read_csv(INFILE); q['entry_ts']=pd.to_datetime(q.entry_ts,utc=True); q['exit_ts']=pd.to_datetime(q.exit_ts,utc=True)
lines=['# SOL A25B Corrected Habitat Metrics','',
'Each actual entry is one trade; REC_H2 is a separate trade. Positive-week/day rate uses active periods only.','',
'## Raw','',
'| Partition | Habitat | N | Trades/wk | WR | PF | Exp | Net | Max DD | Loss streak | Win streak | Worst trade | Best trade | Min win | Avg win | Avg loss | Day +rate | Week +rate | Avg week | Worst week |',
'|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for part in PARTS:
  for code,name in ZONES:
    z=q[(q.partition==part)&(q.zone==code)].sort_values(['exit_ts','entry_ts']).copy()
    if z.empty: continue
    p=pd.to_numeric(z.pnl,errors='coerce'); wins=p[p>0]; losses=p[p<=0]; w=weekly(z,'pnl'); d=daily(z,'pnl')
    lines.append(f'| {part} | {name} | {len(z)} | {len(z)/(YEARS[part]*365.2425/7):.2f} | {pct((p>0).mean())} | {fmt(pf(p))} | ${fmt(p.mean())} | ${fmt(p.sum())} | ${fmt(dd(z,"pnl"))} | {streak(p.tolist())} | {streak(p.tolist(),True)} | ${fmt(p.min())} | ${fmt(p.max())} | ${fmt(wins.min())} | ${fmt(wins.mean())} | ${fmt(losses.mean())} | {pct((d>0).mean())} | {pct((w>0).mean())} | ${fmt(w.mean())} | ${fmt(w.min())} |')
lines += ['', '## 5bps stress','',
'| Partition | Habitat | WR | PF | Exp | Net | Max DD | Loss streak | Worst trade | Min win | Avg win | Avg loss | Day +rate | Week +rate | Avg week | Worst week |',
'|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for part in PARTS:
  for code,name in ZONES:
    z=q[(q.partition==part)&(q.zone==code)].sort_values(['exit_ts','entry_ts']).copy()
    if z.empty: continue
    p=pd.to_numeric(z.pnl_5bps,errors='coerce'); wins=p[p>0]; losses=p[p<=0]; w=weekly(z,'pnl_5bps'); d=daily(z,'pnl_5bps')
    lines.append(f'| {part} | {name} | {pct((p>0).mean())} | {fmt(pf(p))} | ${fmt(p.mean())} | ${fmt(p.sum())} | ${fmt(dd(z,"pnl_5bps"))} | {streak(p.tolist())} | ${fmt(p.min())} | ${fmt(wins.min())} | ${fmt(wins.mean())} | ${fmt(losses.mean())} | {pct((d>0).mean())} | {pct((w>0).mean())} | ${fmt(w.mean())} | ${fmt(w.min())} |')
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8'); STATUS.write_text('SOL_LONG_A25B_ZONE_METRICS_COMPLETE\n',encoding='utf-8'); print('SOL_LONG_A25B_ZONE_METRICS_COMPLETE')