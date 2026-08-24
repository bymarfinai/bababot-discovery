#!/usr/bin/env python3
from pathlib import Path
import math
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
CASES=ROOT/'BTC_GENERIC_F85_LONG_CLOCK_SCAN_B27DE_Cases.csv'
OUT_MD=ROOT/'BTC_F85_LONG_SINGLE_POSITION_PORTFOLIO_B27DG_Result.md'
OUT_TRADES=ROOT/'BTC_F85_LONG_SINGLE_POSITION_PORTFOLIO_B27DG_Trades.csv'
OUT_SUM=ROOT/'BTC_F85_LONG_SINGLE_POSITION_PORTFOLIO_B27DG_Summary.csv'
OUT_STATUS=ROOT/'BTC_F85_LONG_SINGLE_POSITION_PORTFOLIO_B27DG_Status.txt'
PARTS=('external','development','reference_validation','august')
MAJOR=('external','development','reference_validation')
ZONE_MAP={480:'LONDON',210:'ALT_0330',330:'RAW_0530',570:'RAW_0930',1410:'RAW_2330'}
TIE_ORDER={'LONDON':0,'ALT_0330':1,'RAW_0530':2,'RAW_0930':3,'RAW_2330':4}


def b(s): return s.astype(str).str.lower().eq('true')
def pf(v):
    x=pd.to_numeric(pd.Series(v),errors='coerce').dropna(); p=float(x[x>0].sum()); n=float(-x[x<0].sum())
    if n==0 and p>0:return float('inf')
    return p/n if n>0 else np.nan

def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def num(x):
    if pd.isna(x):return '-'
    if math.isinf(float(x)):return 'inf'
    return f'{float(x):.2f}'
def usd(x): return '-' if pd.isna(x) else f'${float(x):+.2f}'


def load():
    c=pd.read_csv(CASES)
    for col in ('execution_start','touch_bar_start','entry_bar_start','exit_ts'):
        c[col]=pd.to_datetime(c[col],utc=True,errors='coerce')
    c['entry_b']=b(c.entry_executed)
    c['clock_min']=pd.to_numeric(c.clock_min,errors='coerce').astype('Int64')
    c['net_pnl_usd']=pd.to_numeric(c.net_pnl_usd,errors='coerce')
    c=c[c.clock_min.isin(ZONE_MAP)&c.entry_b&c.net_pnl_usd.notna()].copy()
    c['zone']=c.clock_min.map(ZONE_MAP)
    c['touch_elapsed_min']=(c.touch_bar_start-c.execution_start)/pd.Timedelta(minutes=1)
    c['primary_eligible']=c.zone.eq('LONDON') | (c.zone.eq('ALT_0330') & (c.touch_elapsed_min<=195.0))
    c['expanded_eligible']=c.primary_eligible | c.zone.isin(['RAW_0530','RAW_0930','RAW_2330'])
    assert c.entry_bar_start.notna().all() and c.exit_ts.notna().all()
    assert (c.exit_ts>=c.entry_bar_start).all()
    return c


def lock(g,portfolio):
    q=g.copy(); q['tie_order']=q.zone.map(TIE_ORDER)
    q=q.sort_values(['entry_bar_start','tie_order']).copy()
    locked_until=pd.NaT; accepted=[]; reasons=[]; blocker=[]
    active_zone=None
    for r in q.itertuples(index=False):
        if pd.isna(locked_until) or pd.Timestamp(r.entry_bar_start)>=pd.Timestamp(locked_until):
            accepted.append(True); reasons.append('ACCEPT'); blocker.append('')
            locked_until=pd.Timestamp(r.exit_ts); active_zone=r.zone
        else:
            accepted.append(False); reasons.append('SKIP_OPEN_POSITION'); blocker.append(active_zone)
    q['accepted']=accepted; q['decision']=reasons; q['blocked_by_zone']=blocker; q['portfolio']=portfolio
    return q


def metrics(g):
    v=pd.to_numeric(g.net_pnl_usd,errors='coerce')
    return dict(n=len(g),wins=int((v>0).sum()),wr=float((v>0).mean()) if len(g) else np.nan,pf=pf(v) if len(g) else np.nan,expectancy=float(v.mean()) if len(g) else np.nan,total_net=float(v.sum()) if len(g) else 0.0)


def main():
    c=load(); all_dec=[]; rows=[]
    for portfolio,flag in [('PRIMARY_2ZONE','primary_eligible'),('EXPANDED_5ZONE','expanded_eligible')]:
        for part in PARTS:
            g=c[(c.partition==part)&c[flag]].copy()
            d=lock(g,portfolio); all_dec.append(d)
            a=d[d.accepted]
            m=metrics(a)
            rows.append({'portfolio':portfolio,'partition':part,'candidates':len(d),'accepted':len(a),'skipped_open':int((~d.accepted).sum()),**m})
            for z in sorted(d.zone.unique()):
                dz=d[d.zone==z]; az=dz[dz.accepted]
                mz=metrics(az)
                rows.append({'portfolio':portfolio,'partition':part,'zone':z,'candidates':len(dz),'accepted':len(az),'skipped_open':int((~dz.accepted).sum()),**mz})
        dmaj=pd.concat([x for x in all_dec if x.portfolio.iloc[0]==portfolio and x.partition.iloc[0] in MAJOR],ignore_index=True)
        amaj=dmaj[dmaj.accepted]; m=metrics(amaj)
        rows.append({'portfolio':portfolio,'partition':'POOLED_MAJOR','candidates':len(dmaj),'accepted':len(amaj),'skipped_open':int((~dmaj.accepted).sum()),**m})
        for z in sorted(dmaj.zone.unique()):
            dz=dmaj[dmaj.zone==z]; az=dz[dz.accepted]; mz=metrics(az)
            rows.append({'portfolio':portfolio,'partition':'POOLED_MAJOR','zone':z,'candidates':len(dz),'accepted':len(az),'skipped_open':int((~dz.accepted).sum()),**mz})
    dec=pd.concat(all_dec,ignore_index=True); dec.to_csv(OUT_TRADES,index=False)
    s=pd.DataFrame(rows); s.to_csv(OUT_SUM,index=False)
    lines=['# B27DG — F85 LONG Single-Position Portfolio — Result','',
           'Operational rule: while one BTC trade is open, later eligible entries are skipped. Earliest causal entry wins; a new entry is allowed only at/after the prior `exit_ts`.','']
    for portfolio in ('PRIMARY_2ZONE','EXPANDED_5ZONE'):
        lines += [f'## {portfolio}','','| Partition | Candidates | Accepted | Skipped open | WR | PF | Exp | Net |','|---|---:|---:|---:|---:|---:|---:|---:|']
        for part in (*PARTS,'POOLED_MAJOR'):
            r=s[(s.portfolio==portfolio)&(s.partition==part)&s.zone.isna()].iloc[0]
            lines.append(f'| {part} | {int(r.candidates)} | {int(r.accepted)} | {int(r.skipped_open)} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.total_net)} |')
        lines += ['','### Pooled-major contribution by zone','','| Zone | Candidates | Accepted | Blocked | Retention | WR | PF | Exp | Net |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        z=s[(s.portfolio==portfolio)&(s.partition=='POOLED_MAJOR')&s.zone.notna()].copy()
        for r in z.itertuples(index=False):
            ret=r.accepted/r.candidates if r.candidates else np.nan
            lines.append(f'| {r.zone} | {int(r.candidates)} | {int(r.accepted)} | {int(r.skipped_open)} | {pct(ret)} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.total_net)} |')
        ties=dec[(dec.portfolio==portfolio)].groupby(['partition','entry_bar_start']).size(); tie_n=int((ties>1).sum())
        lines += ['',f'Exact same-timestamp candidate ties: **{tie_n}**.','']
    lines += ['## Status','','**B27DG_SINGLE_POSITION_RESCORED**','','Primary 2-zone portfolio is the decision-relevant result. Expanded 5-zone portfolio is exploratory only because the added raw zones were not independently promoted. Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); OUT_STATUS.write_text('B27DG_SINGLE_POSITION_RESCORED\n')
    print(OUT_MD.read_text())
if __name__=='__main__':main()
