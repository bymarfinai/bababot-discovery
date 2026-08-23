#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv'
OUT_MD = ROOT / 'BTC_24H_F05_RECLAIM_CONTROLLED_LOSS_ECON_B27CH_Result.md'
OUT_TRADES = ROOT / 'BTC_24H_F05_RECLAIM_CONTROLLED_LOSS_ECON_B27CH_Trades.csv'
OUT_SUM = ROOT / 'BTC_24H_F05_RECLAIM_CONTROLLED_LOSS_ECON_B27CH_Summary.csv'
OUT_SEL = ROOT / 'BTC_24H_F05_RECLAIM_CONTROLLED_LOSS_ECON_B27CH_Selection.csv'
OUT_STATUS = ROOT / 'BTC_24H_F05_RECLAIM_CONTROLLED_LOSS_ECON_B27CH_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
MAJOR = ('external','development','reference_validation')
OOS = ('external','reference_validation')
CLOCKS = ('00-04','04-08','08-12','12-16','16-20','20-00')
ENTRY_F = 0.05
STOP_F = 0.25
NOTIONAL = 500.0
FEE = 0.40

VARIANTS = {
    'A_R1':      {'tp_mult':1.0, 'be':False},
    'A_R1_5':    {'tp_mult':1.5, 'be':False},
    'A_R2':      {'tp_mult':2.0, 'be':False},
    'B_R1_BE':   {'tp_mult':1.0, 'be':True},
    'B_R1_5_BE': {'tp_mult':1.5, 'be':True},
    'B_R2_BE':   {'tp_mult':2.0, 'be':True},
}


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
    expected = {'external':202,'development':333,'reference_validation':194}
    assert len(q) == 729, len(q)
    for p,n in expected.items():
        got = len(q[q.partition == p])
        assert got == n, (p,got,n)
    assert len(q[q.partition.isin(OOS)]) == 396
    assert q.reclaim_complete_ts.notna().all()
    return q.sort_values(['obs_start','partition']).reset_index(drop=True)


def trade_pnl(entry: float, exit_px: float) -> tuple[float,float]:
    gross = (entry - exit_px) / entry
    net = gross * NOTIONAL - FEE
    return gross, net


def eval_one(x5: pd.DataFrame, r, variant: str, tp_mult: float, use_be: bool) -> dict:
    start = pd.Timestamp(r.reclaim_complete_ts)
    end = pd.Timestamp(r.obs_end)
    L = float(r.L); H = float(r.H); R4 = H-L
    assert R4 > 0 and start < end
    limit_px = L + ENTRY_F*R4
    hard_stop = L + STOP_F*R4
    assert hard_stop > limit_px > L
    q = fast_slice(x5,start,end)
    assert len(q) >= 1 and q.index[0] == start

    base = {
        'variant':variant,'tp_multiple':tp_mult,'use_be':use_be,
        'partition':str(r.partition),'regime':str(r.regime),'clock_block':str(r.clock_block),
        'obs_start':pd.Timestamp(r.obs_start),'obs_end':end,'reclaim_complete_ts':start,
        'H':H,'L':L,'R4':R4,'limit_px':limit_px,'hard_stop_px':hard_stop,
    }

    fill_idx = None; fill_ts = pd.NaT; entry = np.nan
    cancel_reason = 'NO_FILL_BEFORE_BLOCK_END'

    for i,b in enumerate(q.itertuples()):
        o=float(b.open); h=float(b.high); c=float(b.close)
        # Invalidation known at bar open occurs before any possible new fill.
        if o >= hard_stop:
            cancel_reason='INVALIDATED_BEFORE_FILL'; break
        if h >= limit_px:
            fill_idx=i; fill_ts=q.index[i]
            entry = o if o >= limit_px else limit_px
            assert hard_stop > entry, (entry, hard_stop)
            break
        # No fill occurred in this completed bar, so its close can cancel the pending order.
        if c < L:
            cancel_reason='REBREAK_BEFORE_FILL'; break
        if c > H:
            cancel_reason='HIGH_BREAK_BEFORE_FILL'; break

    if fill_idx is None:
        return {**base,'filled':False,'cancel_reason':cancel_reason,'fill_ts':pd.NaT,'entry_px':np.nan,
                'initial_risk_px':np.nan,'initial_risk_pct':np.nan,'target_px':np.nan,
                'exit_ts':pd.NaT,'exit_px':np.nan,'exit_reason':'NO_TRADE','gross_return':np.nan,
                'net_pnl_usd':np.nan,'hold_minutes':np.nan,'rebreak_confirmed':False}

    risk = hard_stop-entry
    assert risk > 0
    target = entry - tp_mult*risk
    assert hard_stop > entry > target

    # Fill-bar treatment: stop is conservative; same-fill-bar TP is not credited.
    fb = q.iloc[fill_idx]
    if float(fb.high) >= hard_stop:
        exit_px=hard_stop; exit_ts=q.index[fill_idx]+BAR5; reason='HARD_STOP'
        gross,net=trade_pnl(entry,exit_px)
        return {**base,'filled':True,'cancel_reason':'','fill_ts':fill_ts,'entry_px':entry,
                'initial_risk_px':risk,'initial_risk_pct':risk/entry,'target_px':target,
                'exit_ts':exit_ts,'exit_px':exit_px,'exit_reason':reason,'gross_return':gross,
                'net_pnl_usd':net,'hold_minutes':float((exit_ts-fill_ts)/pd.Timedelta(minutes=1)),
                'rebreak_confirmed':False}

    fb_close=float(fb.close)
    rebreak = bool(fb_close < L)
    above_count = 1 if (not rebreak and fb_close > L) else 0
    be_active = False  # may activate only from the next bar after confirmation

    for i in range(fill_idx+1, len(q)):
        b=q.iloc[i]; ts=q.index[i]
        o=float(b.open); h=float(b.high); lo=float(b.low); c=float(b.close)

        if use_be and rebreak:
            be_active=True
        active_stop = entry if be_active else hard_stop

        # Gap/open handling first.
        if o >= active_stop:
            exit_px=o; exit_ts=ts; reason='BE_STOP' if be_active else 'HARD_STOP'
            break
        if o <= target:
            exit_px=o; exit_ts=ts; reason='TP'
            break

        hit_stop = h >= active_stop
        hit_target = lo <= target
        if hit_stop and hit_target:
            exit_px=active_stop; exit_ts=ts+BAR5; reason='BE_STOP' if be_active else 'HARD_STOP'
            break
        if hit_stop:
            exit_px=active_stop; exit_ts=ts+BAR5; reason='BE_STOP' if be_active else 'HARD_STOP'
            break
        if hit_target:
            exit_px=target; exit_ts=ts+BAR5; reason='TP'
            break

        # Completed-close logic only after no intrabar order executed.
        if not rebreak:
            if c < L:
                rebreak=True
                above_count=0
                # BE intentionally does not activate until the next bar.
            else:
                above_count = above_count + 1 if c > L else 0
                if above_count >= 2:
                    exit_px=c; exit_ts=ts+BAR5; reason='EARLY_HOLD_EXIT'
                    break
    else:
        last=q.iloc[-1]
        exit_px=float(last.close); exit_ts=end; reason='TIME'

    gross,net=trade_pnl(entry,exit_px)
    hold=float((exit_ts-fill_ts)/pd.Timedelta(minutes=1))
    return {**base,'filled':True,'cancel_reason':'','fill_ts':fill_ts,'entry_px':entry,
            'initial_risk_px':risk,'initial_risk_pct':risk/entry,'target_px':target,
            'exit_ts':exit_ts,'exit_px':exit_px,'exit_reason':reason,'gross_return':gross,
            'net_pnl_usd':net,'hold_minutes':hold,'rebreak_confirmed':rebreak}


def max_drawdown(net: pd.Series) -> float:
    x=pd.to_numeric(net,errors='coerce').dropna().to_numpy(float)
    if len(x)==0: return np.nan
    cum=np.concatenate([[0.0],np.cumsum(x)])
    peak=np.maximum.accumulate(cum)
    return float(np.max(peak-cum))


def max_loss_streak(net: pd.Series) -> int:
    vals=pd.to_numeric(net,errors='coerce').dropna().to_numpy(float)
    best=cur=0
    for v in vals:
        if v < 0:
            cur += 1; best=max(best,cur)
        else:
            cur=0
    return int(best)


def metrics(g: pd.DataFrame) -> dict:
    source_n=int(len(g))
    t=g[g.filled].copy().sort_values(['fill_ts','obs_start'])
    n=int(len(t))
    if n==0:
        return {'source_n':source_n,'trades_n':0,'fill_rate':0.0,'wr':np.nan,'pf':np.nan,'expectancy':np.nan,
                'total_net':0.0,'avg_win':np.nan,'avg_loss':np.nan,'max_dd':np.nan,'max_loss_streak':0,
                'tp_n':0,'hard_stop_n':0,'early_n':0,'be_n':0,'time_n':0,
                'median_risk_pct':np.nan,'median_hold_min':np.nan}
    net=pd.to_numeric(t.net_pnl_usd,errors='coerce')
    pos=net[net>0]; neg=net[net<0]
    gp=float(pos.sum()) if len(pos) else 0.0
    gl=float(-neg.sum()) if len(neg) else 0.0
    pf=(gp/gl) if gl>0 else (math.inf if gp>0 else np.nan)
    return {
        'source_n':source_n,'trades_n':n,'fill_rate':n/source_n if source_n else np.nan,
        'wr':float((net>0).mean()),'pf':pf,'expectancy':float(net.mean()),'total_net':float(net.sum()),
        'avg_win':float(pos.mean()) if len(pos) else np.nan,'avg_loss':float(neg.mean()) if len(neg) else np.nan,
        'max_dd':max_drawdown(net),'max_loss_streak':max_loss_streak(net),
        'tp_n':int((t.exit_reason=='TP').sum()),'hard_stop_n':int((t.exit_reason=='HARD_STOP').sum()),
        'early_n':int((t.exit_reason=='EARLY_HOLD_EXIT').sum()),'be_n':int((t.exit_reason=='BE_STOP').sum()),
        'time_n':int((t.exit_reason=='TIME').sum()),
        'median_risk_pct':float(t.initial_risk_pct.median()),'median_hold_min':float(t.hold_minutes.median()),
    }


def summarize(d: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for v in VARIANTS:
        z=d[d.variant==v]
        for p in MAJOR:
            rows.append({'variant':v,'scope':'PARTITION','name':p,**metrics(z[z.partition==p])})
        rows.append({'variant':v,'scope':'POOL','name':'POOLED_OOS',**metrics(z[z.partition.isin(OOS)])})
        rows.append({'variant':v,'scope':'POOL','name':'POOLED_MAJOR',**metrics(z)})
        for cb in CLOCKS:
            rows.append({'variant':v,'scope':'CLOCK_OOS','name':cb,**metrics(z[z.partition.isin(OOS)&z.clock_block.eq(cb)])})
            rows.append({'variant':v,'scope':'CLOCK_MAJOR','name':cb,**metrics(z[z.clock_block.eq(cb)])})
    return pd.DataFrame(rows)


def getrow(s: pd.DataFrame, v: str, scope: str, name: str):
    q=s[(s.variant==v)&(s.scope==scope)&(s.name==name)]
    assert len(q)==1,(v,scope,name,len(q))
    return q.iloc[0]


def select_dev(s: pd.DataFrame) -> tuple[pd.DataFrame,str|None]:
    rows=[]
    for v,cfg in VARIANTS.items():
        r=getrow(s,v,'PARTITION','development')
        eligible=bool(int(r.trades_n)>=150 and float(r.expectancy)>0 and float(r.pf)>=1.10 and float(r.total_net)>0)
        ratio=float(r.total_net/r.max_dd) if eligible and pd.notna(r.max_dd) and float(r.max_dd)>0 else (math.inf if eligible else np.nan)
        rows.append({'variant':v,'tp_multiple':cfg['tp_mult'],'use_be':cfg['be'],'dev_trades':int(r.trades_n),
                     'dev_wr':float(r.wr),'dev_pf':float(r.pf),'dev_expectancy':float(r.expectancy),
                     'dev_total_net':float(r.total_net),'dev_max_dd':float(r.max_dd),'dev_max_loss_streak':int(r.max_loss_streak),
                     'eligible':eligible,'profit_dd_ratio':ratio})
    sel=pd.DataFrame(rows)
    elig=sel[sel.eligible].copy()
    selected=None
    if len(elig):
        maxnet=float(elig.dev_total_net.max())
        elig['profit_floor_pass']=elig.dev_total_net >= 0.80*maxnet
        cand=elig[elig.profit_floor_pass].copy()
        cand=cand.sort_values(['profit_dd_ratio','dev_pf','dev_max_loss_streak','tp_multiple'],ascending=[False,False,True,False])
        selected=str(cand.iloc[0].variant)
        sel['profit_floor_pass']=sel.variant.isin(set(cand.variant))
    else:
        sel['profit_floor_pass']=False
    sel['selected']=sel.variant.eq(selected) if selected is not None else False
    return sel,selected


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'

def money(v):
    return '-' if pd.isna(v) else f'${float(v):+.2f}'

def pfmt(v):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.2f}'


def main() -> None:
    src=load_source()
    x5,cov=b21.load5()
    assert len(x5)==698112 and abs(float(cov)-1.0)<1e-12

    rows=[]
    for r in src.itertuples(index=False):
        for v,cfg in VARIANTS.items():
            rows.append(eval_one(x5,r,v,float(cfg['tp_mult']),bool(cfg['be'])))
    d=pd.DataFrame(rows)
    assert len(d)==729*len(VARIANTS)
    # Entry identity must be identical across variants.
    pivot=d.pivot_table(index=['partition','obs_start'],columns='variant',values='filled',aggfunc='first')
    assert pivot.nunique(axis=1).max()==1
    d.to_csv(OUT_TRADES,index=False)

    s=summarize(d); s.to_csv(OUT_SUM,index=False)
    sel,selected=select_dev(s)

    robust=False; high70=False
    if selected is not None:
        robust=True; high70=True
        mins={'external':80,'development':150,'reference_validation':80}
        for p in MAJOR:
            r=getrow(s,selected,'PARTITION',p)
            robust = robust and int(r.trades_n)>=mins[p] and float(r.expectancy)>0 and float(r.pf)>=1.20
            high70 = high70 and float(r.wr)>=.70
        po=getrow(s,selected,'POOL','POOLED_OOS')
        robust = robust and float(po.expectancy)>0 and float(po.pf)>=1.20
    sel['robust_pass']=sel.variant.eq(selected)&robust if selected is not None else False
    sel['high_quality_70']=sel.variant.eq(selected)&high70 if selected is not None else False
    sel.to_csv(OUT_SEL,index=False)

    if selected is None:
        verdict='B27CH_NO_DEVELOPMENT_CANDIDATE'
    elif robust:
        verdict='B27CH_CONTROLLED_LOSS_ECON_SUPPORTED'
    else:
        verdict='B27CH_CONTROLLED_LOSS_ECON_NOT_SUPPORTED'
    OUT_STATUS.write_text(verdict+'\n')

    lines=[
        '# B27CH — BTC 24H F05 Reclaim SHORT Controlled-Loss Economics — Result','',
        f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
        '**Audit status: PASS.** Exact B27CE eligible reclaim source identity reproduced: external 202 / development 333 / validation 194 / pooled OOS 396 / pooled major 729. Six frozen variants only; no clock/regime exclusion.','',
        f'Illustrative economics: **${NOTIONAL:.0f} notional/trade, ${FEE:.2f} round-trip fee, no extra slippage**. F05 marketable sell-limit, F25 hard invalidation, 10-minute post-entry hold-above-L defense, RR >=1:1.','',
        '## Development optimization','',
        '| Variant | Trades | WR | PF | Exp/trade | Net | Max DD | Loss streak | Net/DD | Eligible | Profit floor | Selected |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|']
    for rr in sel.itertuples(index=False):
        ratio='-' if pd.isna(rr.profit_dd_ratio) else ('inf' if math.isinf(float(rr.profit_dd_ratio)) else f'{float(rr.profit_dd_ratio):.2f}')
        lines.append(f'| {rr.variant} | {int(rr.dev_trades)} | {pct(rr.dev_wr)} | {pfmt(rr.dev_pf)} | {money(rr.dev_expectancy)} | {money(rr.dev_total_net)} | {money(rr.dev_max_dd)} | {int(rr.dev_max_loss_streak)} | {ratio} | {"YES" if rr.eligible else "NO"} | {"YES" if rr.profit_floor_pass else "NO"} | {"YES" if rr.selected else "NO"} |')

    lines += ['', '## Major partitions — all variants','',
              '| Variant | Partition | N | WR | PF | Exp/trade | Net | Max DD | Max loss streak | TP | STOP | EARLY | BE | TIME |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for v in VARIANTS:
        for p in MAJOR:
            r=getrow(s,v,'PARTITION',p)
            lines.append(f'| {v} | {p} | {int(r.trades_n)} | {pct(r.wr)} | {pfmt(r.pf)} | {money(r.expectancy)} | {money(r.total_net)} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {int(r.tp_n)} | {int(r.hard_stop_n)} | {int(r.early_n)} | {int(r.be_n)} | {int(r.time_n)} |')

    lines += ['', '## Pooled OOS — all variants','',
              '| Variant | N | WR | PF | Exp/trade | Net | Max DD | Loss streak | Median risk | Median hold |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for v in VARIANTS:
        r=getrow(s,v,'POOL','POOLED_OOS')
        lines.append(f'| {v} | {int(r.trades_n)} | {pct(r.wr)} | {pfmt(r.pf)} | {money(r.expectancy)} | {money(r.total_net)} | {money(r.max_dd)} | {int(r.max_loss_streak)} | {pct(r.median_risk_pct)} | {float(r.median_hold_min):.1f}m |')

    lines += ['', '## Six-clock OOS diagnostics — all variants','',
              '| Variant | UTC block | N | WR | PF | Exp/trade | Net | Max DD |',
              '|---|---|---:|---:|---:|---:|---:|---:|']
    for v in VARIANTS:
        for cb in CLOCKS:
            r=getrow(s,v,'CLOCK_OOS',cb)
            lines.append(f'| {v} | {cb} | {int(r.trades_n)} | {pct(r.wr)} | {pfmt(r.pf)} | {money(r.expectancy)} | {money(r.total_net)} | {money(r.max_dd)} |')

    if selected is None:
        lines += ['', '**No development variant met the frozen eligibility gate.**']
    else:
        lines += ['', f'Frozen development-selected candidate: **{selected}**.',
                  f'Robustness gate: **{"PASS" if robust else "FAIL"}**. HIGH_QUALITY_70: **{"PASS" if high70 else "FAIL"}**.']
    lines += ['',f'**Frozen verdict: `{verdict}`.**','',
              'Research only. No live BBC change. No failed clock may be removed post hoc inside B27CH.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
