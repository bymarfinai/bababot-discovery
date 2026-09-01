#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, math
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent; ROOT=HERE.parent
S9A_PATH=HERE/'eth_b27dx_s9a_stale_entry_cancellation.py'
spec=importlib.util.spec_from_file_location('eth_s9a',S9A_PATH); s9a=importlib.util.module_from_spec(spec)
assert spec.loader is not None; spec.loader.exec_module(s9a)
s4=s9a.s4

PFX='ETH_B27DX_S11A_1600_FRESHNESS_AUDIT'
OUT_MD=ROOT/f'{PFX}_Result.md'; OUT_CSV=ROOT/f'{PFX}_Summary.csv'; OUT_STATUS=ROOT/f'{PFX}_Status.txt'
PARTS=s4.PARTS

def fmt(v,nd=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{nd}f}'
def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'

def main():
    x,cov=s4.b.m.m.load5()
    raw=s4.build_candidates(x)
    parity=s4.parity_check(x,raw); parity_ok=bool(len(parity) and parity['pass'].all())
    c,audit=s9a.annotate_freshness(x,raw)
    audit_ok=bool(len(audit)==len(c) and audit[['fill_match','eligible_before_or_at_fill','delay_is_5m_multiple']].all().all())
    dec,_,_=s4.summarize(c)
    a=dec[(dec.accepted)&(dec.exec_min==960)].copy()
    rows=[]
    for p in [*PARTS,'POOLED_MAJOR']:
        q=a if p=='POOLED_MAJOR' else a[a.partition==p]
        for imm,label in ((True,'IMMEDIATE'),(False,'STALE')):
            g=q[q.immediate_fill==imm].sort_values('entry_bar_start')
            m=s4.metrics(g,'pnl_0')
            rows.append({'partition':p,'freshness':label,'n':len(g),'losses':int((g.pnl_0<0).sum()),'loss_rate':float((g.pnl_0<0).mean()) if len(g) else np.nan,'median_delay_bars':float(g.delay_bars.median()) if len(g) else np.nan,**m})
    out=pd.DataFrame(rows); out.to_csv(OUT_CSV,index=False)
    consistent=True; adequate=True
    for p in PARTS:
        q=out[out.partition==p].set_index('freshness')
        if int(q.loc['IMMEDIATE','n'])<10 or int(q.loc['STALE','n'])<10: adequate=False
        if not (q.loc['STALE','loss_rate']>q.loc['IMMEDIATE','loss_rate'] and q.loc['STALE','pf']<q.loc['IMMEDIATE','pf']): consistent=False
    status='ETH_S11A_1600_STALE_MECHANICALLY_WORSE' if parity_ok and audit_ok and adequate and consistent else 'ETH_S11A_1600_FRESHNESS_NOT_CONSISTENT'
    lines=['# ETH B27DX — S11A 16:00 Freshness Audit — Result','',f'ETH raw 5m coverage: **{cov:.4%}**.','',f'- Candidate parity: **{"PASS" if parity_ok else "FAIL"}**.',f'- Freshness causal audit: **{"PASS" if audit_ok else "FAIL"}**.','',
           '## 16:00 accepted-trade freshness anatomy','',
           '| Partition | Freshness | N | Losses | Loss rate | WR | PF | Exp | Net | Median delay bars |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for p in [*PARTS,'POOLED_MAJOR']:
        for label in ('IMMEDIATE','STALE'):
            r=out[(out.partition==p)&(out.freshness==label)].iloc[0]
            lines.append(f'| {p} | {label} | {int(r.n)} | {int(r.losses)} | {pct(r.loss_rate)} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {fmt(r.median_delay_bars,1)} |')
    lines += ['', '## Frozen diagnostic', '', f'- Adequate N (>=10 each group in each major partition): **{"PASS" if adequate else "FAIL"}**.', f'- STALE has higher loss rate and lower PF in all three major partitions: **{"PASS" if consistent else "FAIL"}**.', '', '## Decision','',f'**Status: {status}**','', '- Diagnostic only; no strategy rule is changed in S11A.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); OUT_STATUS.write_text(status+'\n'); print(OUT_MD.read_text())
if __name__=='__main__': main()
