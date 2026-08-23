#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd
import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv'
OUT_MD = ROOT / 'BTC_24H_F05_T10_F25_ECON_B27CK_Result.md'
OUT_TRADES = ROOT / 'BTC_24H_F05_T10_F25_ECON_B27CK_Trades.csv'
OUT_SUM = ROOT / 'BTC_24H_F05_T10_F25_ECON_B27CK_Summary.csv'
OUT_STATUS = ROOT / 'BTC_24H_F05_T10_F25_ECON_B27CK_Status.txt'
OUT_LOGIC = ROOT / 'BTC_24H_F05_T10_F25_ECON_B27CK_Audit.txt'

BAR5 = pd.Timedelta(minutes=5)
MAJOR = ('external','development','reference_validation')
OOS = ('external','reference_validation')
CLOCKS = ('00-04','04-08','08-12','12-16','16-20','20-00')
WIB = {'00-04':'07-11','04-08':'11-15','08-12':'15-19','12-16':'19-23','16-20':'23-03','20-00':'03-07'}
NOTIONAL = 500.0
FEE = 0.40
ENTRY_F = 0.05
TP_F = -0.10
STOP_F = 0.25


def as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.copy()
    return s.astype(str).str.lower().eq('true')


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def load_source() -> pd.DataFrame:
    d = pd.read_csv(SRC)
    for c in ('obs_start','obs_end','reclaim_complete_ts'):
        d[c] = pd.to_datetime(d[c], utc=True, errors='coerce')
    d['eligible'] = as_bool(d['eligible'])
    q = d[d.partition.isin(MAJOR) & d.eligible].copy()
    exp = {'external':202,'development':333,'reference_validation':194}
    assert len(q) == 729
    for p,n in exp.items():
        assert len(q[q.partition == p]) == n
    assert len(q[q.partition.isin(OOS)]) == 396
    assert q.reclaim_complete_ts.notna().all()
    return q.sort_values(['obs_start','partition']).reset_index(drop=True)


def pnl(entry: float, exit_px: float) -> tuple[float,float]:
    gross = (entry - exit_px) / entry
    return gross, gross*NOTIONAL - FEE


def eval_one(x5: pd.DataFrame, r) -> dict:
    start = pd.Timestamp(r.reclaim_complete_ts)
    end = pd.Timestamp(r.obs_end)
    H = float(r.H); L = float(r.L); R4 = float(r.R4)
    assert R4 > 0 and abs(R4-(H-L)) < 1e-7*max(1.0,R4)
    f05 = L + ENTRY_F*R4
    t10 = L - 0.10*R4
    f25 = L + STOP_F*R4
    assert t10 < L < f05 < f25 < H
    q = fast_slice(x5,start,end)
    assert len(q) >= 1 and q.index[0] == start

    base = {
        'partition':str(r.partition),'regime':str(r.regime),'clock_block':str(r.clock_block),
        'obs_start':pd.Timestamp(r.obs_start),'obs_end':end,'reclaim_complete_ts':start,
        'H':H,'L':L,'R4':R4,'F05':f05,'T10':t10,'F25':f25,
    }

    fill_idx = None; fill_ts = pd.NaT; entry = np.nan
    cancel = 'NO_FILL_BEFORE_BLOCK_END'
    for i,b in enumerate(q.itertuples()):
        o=float(b.open); h=float(b.high); c=float(b.close)
        if o >= f25:
            cancel='INVALIDATED_BEFORE_FILL'; break
        if h >= f05:
            fill_idx=i; fill_ts=q.index[i]
            entry=o if o >= f05 else f05
            assert f25 > entry >= f05
            break
        if c < L:
            cancel='REBREAK_BEFORE_FILL'; break
        if c > H:
            cancel='HIGH_BREAK_BEFORE_FILL'; break

    if fill_idx is None:
        return {**base,'filled':False,'cancel_reason':cancel,'fill_ts':pd.NaT,'entry_px':np.nan,
                'actual_reward_px':np.nan,'actual_risk_px':np.nan,'actual_rr':np.nan,
                'exit_ts':pd.NaT,'exit_px':np.nan,'exit_reason':'NO_TRADE',
                'gross_return':np.nan,'net_pnl_usd':np.nan,'hold_minutes':np.nan}

    reward=entry-t10; risk=f25-entry
    assert reward>0 and risk>0
    rr=reward/risk

    fb=q.iloc[fill_idx]
    if float(fb.high) >= f25:
        exit_px=f25; exit_ts=q.index[fill_idx]+BAR5; reason='SL_F25'
        gross,net=pnl(entry,exit_px)
        return {**base,'filled':True,'cancel_reason':'','fill_ts':fill_ts,'entry_px':entry,
                'actual_reward_px':reward,'actual_risk_px':risk,'actual_rr':rr,
                'exit_ts':exit_ts,'exit_px':exit_px,'exit_reason':reason,
                'gross_return':gross,'net_pnl_usd':net,
                'hold_minutes':float((exit_ts-fill_ts)/pd.Timedelta(minutes=1))}

    exit_px=np.nan; exit_ts=pd.NaT; reason=None
    for i in range(fill_idx+1,len(q)):
        b=q.iloc[i]; ts=q.index[i]
        o=float(b.open); h=float(b.high); lo=float(b.low)
        if o >= f25:
            exit_px=o; exit_ts=ts; reason='SL_GAP_OPEN'; break
        if o <= t10:
            exit_px=o; exit_ts=ts; reason='TP_GAP_OPEN'; break
        hs=h>=f25; ht=lo<=t10
        if hs and ht:
            exit_px=f25; exit_ts=ts+BAR5; reason='SL_F25'; break
        if hs:
            exit_px=f25; exit_ts=ts+BAR5; reason='SL_F25'; break
        if ht:
            exit_px=t10; exit_ts=ts+BAR5; reason='TP_T10'; break

    if reason is None:
        last=q.iloc[-1]
        exit_px=float(last.close); exit_ts=end; reason='TIME'

    gross,net=pnl(entry,float(exit_px))
    return {**base,'filled':True,'cancel_reason':'','fill_ts':fill_ts,'entry_px':entry,
            'actual_reward_px':reward,'actual_risk_px':risk,'actual_rr':rr,
            'exit_ts':exit_ts,'exit_px':float(exit_px),'exit_reason':reason,
            'gross_return':gross,'net_pnl_usd':net,
            'hold_minutes':float((pd.Timestamp(exit_ts)-fill_ts)/pd.Timedelta(minutes=1))}


def max_drawdown(net: pd.Series) -> float:
    x=pd.to_numeric(net,errors='coerce').dropna().to_numpy(float)
    if len(x)==0: return np.nan
    cum=np.concatenate([[0.0],np.cumsum(x)])
    peak=np.maximum.accumulate(cum)
    return float(np.max(peak-cum))


def max_loss_streak(net: pd.Series) -> int:
    x=pd.to_numeric(net,errors='coerce').dropna().to_numpy(float)
    cur=best=0
    for v in x:
        if v<0: cur+=1; best=max(best,cur)
        else: cur=0
    return int(best)


def metrics(g: pd.DataFrame) -> dict:
    source_n=len(g)
    t=g[g.filled].copy().sort_values(['fill_ts','obs_start'])
    n=len(t)
    if n==0:
        return {'source_n':source_n,'trades_n':0,'fill_rate':0.0,'wr':np.nan,'pf':np.nan,
                'expectancy':np.nan,'total_net':0.0,'avg_win':np.nan,'avg_loss':np.nan,
                'max_dd':np.nan,'max_loss_streak':0,'tp_n':0,'sl_n':0,'time_n':0,
                'median_hold_min':np.nan,'median_actual_rr':np.nan}
    net=pd.to_numeric(t.net_pnl_usd,errors='coerce')
    pos=net[net>0]; neg=net[net<0]
    gp=float(pos.sum()); gl=float(-neg.sum())
    pf=gp/gl if gl>0 else (math.inf if gp>0 else np.nan)
    return {
        'source_n':int(source_n),'trades_n':int(n),'fill_rate':n/source_n,
        'wr':float((net>0).mean()),'pf':pf,'expectancy':float(net.mean()),'total_net':float(net.sum()),
        'avg_win':float(pos.mean()) if len(pos) else np.nan,'avg_loss':float(neg.mean()) if len(neg) else np.nan,
        'max_dd':max_drawdown(net),'max_loss_streak':max_loss_streak(net),
        'tp_n':int(t.exit_reason.str.startswith('TP').sum()),
        'sl_n':int(t.exit_reason.str.startswith('SL').sum()),
        'time_n':int((t.exit_reason=='TIME').sum()),
        'median_hold_min':float(t.hold_minutes.median()),
        'median_actual_rr':float(t.actual_rr.median()),
    }


def summarize(d: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for p in MAJOR:
        rows.append({'scope':'PARTITION','name':p,**metrics(d[d.partition==p])})
    rows.append({'scope':'POOL','name':'POOLED_OOS',**metrics(d[d.partition.isin(OOS)])})
    rows.append({'scope':'POOL','name':'POOLED_MAJOR',**metrics(d)})
    for cb in CLOCKS:
        rows.append({'scope':'CLOCK_OOS','name':cb,**metrics(d[d.partition.isin(OOS)&d.clock_block.eq(cb)])})
        rows.append({'scope':'CLOCK_MAJOR','name':cb,**metrics(d[d.clock_block.eq(cb)])})
    return pd.DataFrame(rows)


def getrow(s,scope,name):
    z=s[(s.scope==scope)&(s.name==name)]
    assert len(z)==1
    return z.iloc[0]

def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def money(x): return '-' if pd.isna(x) else f'${float(x):+.2f}'
def pfmt(x):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.2f}'
def num(x): return '-' if pd.isna(x) else f'{float(x):.2f}'


def main():
    src=load_source()
    x5,cov=b21.load5()
    assert len(x5)==698112 and abs(float(cov)-1.0)<1e-12
    d=pd.DataFrame([eval_one(x5,r) for r in src.itertuples(index=False)])
    assert len(d)==729
    # Executable entry identity must reproduce B27CH exact F05 fill semantics.
    expected_fills={'external':178,'development':280,'reference_validation':163}
    for p,n in expected_fills.items():
        assert int(d[d.partition.eq(p)].filled.sum())==n,(p,int(d[d.partition.eq(p)].filled.sum()),n)
    assert int(d[d.partition.isin(OOS)].filled.sum())==341
    assert int(d.filled.sum())==621
    d.to_csv(OUT_TRADES,index=False)
    s=summarize(d); s.to_csv(OUT_SUM,index=False)

    ext=getrow(s,'PARTITION','external'); dev=getrow(s,'PARTITION','development'); val=getrow(s,'PARTITION','reference_validation'); oos=getrow(s,'POOL','POOLED_OOS')
    positive=all(float(r.expectancy)>0 and float(r.pf)>1.0 for r in (ext,dev,val)) and float(oos.expectancy)>0 and float(oos.pf)>1.0
    verdict='B27CK_DIAGNOSTIC_POSITIVE_ALL_MAJOR' if positive else 'B27CK_DIAGNOSTIC_MIXED_OR_NEGATIVE'
    OUT_STATUS.write_text(verdict+'\n')
    OUT_LOGIC.write_text('audit=PASS\nsource=729\nfills_external=178\nfills_development=280\nfills_validation=163\nfills_oos=341\nfills_major=621\n')

    lines=['# B27CK — BTC 24H F05 Entry / T10 TP / F25 SL Economics — Result','',
           f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
           '**Audit status: PASS.** Exact B27CE source reproduced (202/333/194) and B27CH executable F05 fill identity reproduced (178/280/163; OOS 341; major 621).','',
           'Configuration: SHORT F05 = L+5%R4; fixed TP T10 = L-10%R4; fixed SL F25 = L+25%R4; no early exit, no BE, no runner. $500 notional, $0.40 RT fee, no extra slippage.','',
           '**Important:** exact-F05 nominal RR is 0.75:1 (15%R4 reward / 20%R4 risk), below the previously required >=1:1. This is diagnostic, not promotable as-is.','',
           '## Six-clock OOS economics — first','',
           '| UTC / WIB | N | WR | PF | Exp/trade | Net | Max DD | Loss streak | TP | SL | TIME | Median actual RR |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for cb in CLOCKS:
        r=getrow(s,'CLOCK_OOS',cb)
        lines.append(f'| {cb} / {WIB[cb]} | {int(r.trades_n)} | {pct(r.wr)} | {pfmt(r.pf)} | {money(r.expectancy)} | {money(r.total_net)} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {int(r.tp_n)} | {int(r.sl_n)} | {int(r.time_n)} | {num(r.median_actual_rr)} |')

    lines += ['', '## Major partitions and pools','',
              '| Scope | Source | Trades | Fill | WR | PF | Exp/trade | Net | Avg win | Avg loss | Max DD | Loss streak | TP | SL | TIME | Median RR | Median hold |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for scope,name in [('PARTITION','external'),('PARTITION','development'),('PARTITION','reference_validation'),('POOL','POOLED_OOS'),('POOL','POOLED_MAJOR')]:
        r=getrow(s,scope,name)
        lines.append(f'| {name} | {int(r.source_n)} | {int(r.trades_n)} | {pct(r.fill_rate)} | {pct(r.wr)} | {pfmt(r.pf)} | {money(r.expectancy)} | {money(r.total_net)} | {money(r.avg_win)} | {money(r.avg_loss)} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {int(r.tp_n)} | {int(r.sl_n)} | {int(r.time_n)} | {num(r.median_actual_rr)} | {num(r.median_hold_min)}m |')

    lines += ['', f'**Frozen diagnostic verdict: `{verdict}`.**','',
              'A positive diagnostic would still not override the RR<1 constraint. Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
