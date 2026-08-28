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
import bnb_session_native_london_ny_long_m7_entry_economics_b27es as b27es

TARGET='BNBUSDT'
BAR5=pd.Timedelta(minutes=5)
CAND='E5_MICRO_HL_BULL'
EXT_R=.30
STOP_R=.30
COST=b27es.TOTAL_COST
NOTIONAL=b27es.ILLUSTRATIVE_NOTIONAL
PFX='BNB_SESSION_NATIVE_LONDON_NY_LONG_M10_LOSS_CONVERSION_B27EV'
OUT_DETAIL=ROOT/f'{PFX}_Detail.csv'
OUT_SUM=ROOT/f'{PFX}_Summary.csv'
OUT_MD=ROOT/f'{PFX}_Result.md'
OUT_STATUS=ROOT/f'{PFX}_Status.txt'
ACTIONS=[
    'BASELINE',
    'C1_CLOSE_ABOVE_SIGNAL_HIGH',
    'C2_SECOND_BULL_PROGRESS',
    'C3_CLOSE_ABOVE_PREV_HIGH',
    'M1_H_TOUCH_LOCK_005R',
    'M2_H10_TOUCH_LOCK_H',
    'M3_PARTIAL50_AT_H',
    'M4_PARTIAL50_AT_H10',
    'R1_ONE_FRESH_MICROHL_AFTER_SL_BEFORE_H',
]


def basic_sim(q, entry_px, H, R):
    return b27es.simulate_one(q, entry_px, H, R, EXT_R, STOP_R)


def signal_context(exe, entry_ts):
    sig_ts=entry_ts-BAR5; prev_ts=sig_ts-BAR5
    if sig_ts not in exe.index or prev_ts not in exe.index:
        raise AssertionError('missing original signal context')
    s=exe.loc[sig_ts]; p=exe.loc[prev_ts]
    return sig_ts,pd.Series(p),pd.Series(s)


def confirm_entry(action, exe, original_entry_ts, H, R):
    sig_ts, p0, s0 = signal_context(exe, original_entry_ts)
    start=original_entry_ts
    q=exe[exe.index>=start]
    prev=None
    for ts,row in q.iterrows():
        o,h,l,c=map(float,[row.open,row.high,row.low,row.close])
        ok=False
        if action=='C1_CLOSE_ABOVE_SIGNAL_HIGH':
            ok=c>float(s0.high)
        elif action=='C2_SECOND_BULL_PROGRESS':
            pc=float(prev.close) if prev is not None else float(s0.close)
            ok=(c>o) and (c>float(s0.close)) and (c>pc)
        elif action=='C3_CLOSE_ABOVE_PREV_HIGH':
            ok=c>float(p0.high)
        else:
            raise ValueError(action)
        if ok:
            fill_ts=ts+BAR5
            if fill_ts not in exe.index:
                return None
            entry_px=float(exe.loc[fill_ts].open)
            if entry_px<=0:
                return None
            post=exe[exe.index>=fill_ts]
            if post.empty:
                return None
            z=basic_sim(post,entry_px,H,R)
            z.update({'entry_ts_new':fill_ts,'entry_px_new':entry_px,'trade_legs':1,'executed':True})
            return z
        prev=row
    return None


def stop_fill_px(bar, stop_px):
    o=float(bar.open)
    return o if o<=stop_px else stop_px


def managed_stop_sim(q, entry_px,H,R, mode):
    target=H+EXT_R*R
    orig_stop=entry_px-STOP_R*R
    active_stop=orig_stop
    pending_stop=None
    exit_type='SESSION_CLOSE'; exit_ts=q.index[-1]; exit_px=float(q.iloc[-1].close)
    for ts,bar in q.iterrows():
        if pending_stop is not None:
            active_stop=max(active_stop,pending_stop); pending_stop=None
        hit_sl=float(bar.low)<=active_stop
        hit_tp=float(bar.high)>=target
        if hit_sl:
            exit_type='SL_BOTH' if hit_tp else 'SL'
            exit_ts=ts; exit_px=stop_fill_px(bar,active_stop); break
        if hit_tp:
            exit_type='TP'; exit_ts=ts; exit_px=target; break
        c=float(bar.close)
        if mode=='M1_H_TOUCH_LOCK_005R' and float(bar.high)>=H:
            lock=entry_px+.05*R
            if lock<c:
                pending_stop=lock
        elif mode=='M2_H10_TOUCH_LOCK_H' and float(bar.high)>=H+.10*R:
            lock=H
            if lock<c:
                pending_stop=lock
    gross=exit_px/entry_px-1
    net=gross-COST
    return {'exit_type':exit_type,'exit_ts':exit_ts,'exit_px':exit_px,'gross_return':gross,'net_return':net,
            'pnl_usd_500':net*NOTIONAL,'net_win':net>0,'trade_legs':1,'executed':True,
            'entry_ts_new':q.index[0],'entry_px_new':entry_px}


def partial_sim(q,entry_px,H,R,level):
    target=H+EXT_R*R; stop=entry_px-STOP_R*R
    frac_open=1.0; gross_sum=0.0; cost_sum=0.0; partial_done=False
    exit_type='SESSION_CLOSE'; exit_ts=q.index[-1]
    for ts,bar in q.iterrows():
        hit_sl=float(bar.low)<=stop
        hit_tp=float(bar.high)>=target
        hit_partial=(not partial_done) and float(bar.high)>=level
        if hit_sl:
            # Conservative: if SL shares the first-partial bar, SL owns that bar.
            gross_sum += frac_open*(stop/entry_px-1)
            cost_sum += frac_open*COST
            frac_open=0.0; exit_type='SL_BOTH' if hit_tp else 'SL'; exit_ts=ts; break
        if hit_partial:
            gross_sum += .5*(level/entry_px-1)
            cost_sum += .5*COST
            frac_open -= .5; partial_done=True
        if hit_tp and frac_open>0:
            gross_sum += frac_open*(target/entry_px-1)
            cost_sum += frac_open*COST
            frac_open=0.0; exit_type='TP_AFTER_PARTIAL' if partial_done else 'TP'; exit_ts=ts; break
    if frac_open>0:
        close=float(q.iloc[-1].close)
        gross_sum += frac_open*(close/entry_px-1)
        cost_sum += frac_open*COST
        exit_type='SESSION_CLOSE_AFTER_PARTIAL' if partial_done else 'SESSION_CLOSE'
        exit_ts=q.index[-1]
    net=gross_sum-cost_sum
    return {'exit_type':exit_type,'exit_ts':exit_ts,'exit_px':np.nan,'gross_return':gross_sum,'net_return':net,
            'pnl_usd_500':net*NOTIONAL,'net_win':net>0,'trade_legs':1,'executed':True,
            'entry_ts_new':q.index[0],'entry_px_new':entry_px,'partial_done':partial_done}


def h_before_sl(q, sim, H):
    if sim['exit_type'] not in ('SL','SL_BOTH'):
        return False
    pre=q[q.index < pd.Timestamp(sim['exit_ts'])]
    return bool((not pre.empty) and float(pre.high.max())>=H)


def retry_after_sl(exe,q,entry_px,H,R,baseline):
    # First leg always retained.
    total_net=float(baseline['net_return']); total_pnl=float(baseline['pnl_usd_500']); legs=1
    if baseline['exit_type'] not in ('SL','SL_BOTH') or h_before_sl(q,baseline,H):
        z=dict(baseline); z.update({'net_return':total_net,'pnl_usd_500':total_pnl,'net_win':total_net>0,
                                    'trade_legs':legs,'executed':True,'entry_ts_new':q.index[0],'entry_px_new':entry_px,
                                    'retry_executed':False})
        return z
    start=pd.Timestamp(baseline['exit_ts'])+BAR5
    scan=exe[exe.index>=start]
    prev=None
    for ts,row in scan.iterrows():
        if prev is not None:
            o,h,l,c=map(float,[row.open,row.high,row.low,row.close])
            is_micro=(l>float(prev.low)) and (c>float(prev.close)) and (c>o)
            if is_micro:
                fill_ts=ts+BAR5
                if fill_ts not in exe.index:
                    break
                px=float(exe.loc[fill_ts].open)
                post=exe[exe.index>=fill_ts]
                if post.empty: break
                r=basic_sim(post,px,H,R)
                total_net += float(r['net_return']); total_pnl += float(r['pnl_usd_500']); legs+=1
                return {'exit_type':f"RETRY_{r['exit_type']}",'exit_ts':r['exit_ts'],'exit_px':r['exit_px'],
                        'gross_return':np.nan,'net_return':total_net,'pnl_usd_500':total_pnl,'net_win':total_net>0,
                        'trade_legs':legs,'executed':True,'entry_ts_new':q.index[0],'entry_px_new':entry_px,
                        'retry_executed':True,'retry_entry_ts':fill_ts,'retry_entry_px':px}
        prev=row
    z=dict(baseline); z.update({'net_return':total_net,'pnl_usd_500':total_pnl,'net_win':total_net>0,
                                'trade_legs':legs,'executed':True,'entry_ts_new':q.index[0],'entry_px_new':entry_px,
                                'retry_executed':False})
    return z


def build(x5):
    entries,exec_map=b27es.build_entries(x5)
    e=entries[entries.candidate==CAND].copy().sort_values('entry_ts')
    if len(e)!=50: raise AssertionError(f'expected 50 entries got {len(e)}')
    sessions=b27em.session_rows(x5)
    dev=sessions[(sessions.partition=='development') & sessions.leave.fillna(False).astype(bool)]
    smap={str(r.local_date):r for _,r in dev.iterrows()}
    rows=[]
    for _,r in e.iterrows():
        date=str(r.local_date); s=smap[date]
        exe=b27em.fs(x5,pd.Timestamp(s.ny_open_utc),pd.Timestamp(s.ny_close_utc))
        q=exec_map[(date,CAND)]
        entry_px=float(r.entry_px); H=float(r.H); R=float(r.R)
        base=basic_sim(q,entry_px,H,R)
        base_win=bool(base['net_win'])
        for action in ACTIONS:
            if action=='BASELINE':
                z=dict(base); z.update({'trade_legs':1,'executed':True,'entry_ts_new':pd.Timestamp(r.entry_ts),'entry_px_new':entry_px})
            elif action.startswith('C'):
                z=confirm_entry(action,exe,pd.Timestamp(r.entry_ts),H,R)
                if z is None:
                    z={'exit_type':'NO_TRADE','exit_ts':pd.NaT,'exit_px':np.nan,'gross_return':0.0,'net_return':0.0,
                       'pnl_usd_500':0.0,'net_win':False,'trade_legs':0,'executed':False,
                       'entry_ts_new':pd.NaT,'entry_px_new':np.nan}
            elif action in ('M1_H_TOUCH_LOCK_005R','M2_H10_TOUCH_LOCK_H'):
                z=managed_stop_sim(q,entry_px,H,R,action)
            elif action=='M3_PARTIAL50_AT_H':
                z=partial_sim(q,entry_px,H,R,H)
            elif action=='M4_PARTIAL50_AT_H10':
                z=partial_sim(q,entry_px,H,R,H+.10*R)
            elif action=='R1_ONE_FRESH_MICROHL_AFTER_SL_BEFORE_H':
                z=retry_after_sl(exe,q,entry_px,H,R,base)
            else: raise ValueError(action)
            new_win=bool(z['net_win'])
            if base_win and new_win: trans='W_TO_W'
            elif base_win and not bool(z['executed']): trans='W_TO_NT'
            elif base_win: trans='W_TO_L'
            elif new_win: trans='L_TO_W'
            elif not bool(z['executed']): trans='L_TO_NT'
            else: trans='L_TO_L'
            rec={'local_date':date,'action':action,'baseline_win':base_win,'baseline_net_return':float(base['net_return']),
                 'baseline_exit_type':base['exit_type'],'transition':trans}
            rec.update(z); rows.append(rec)
    d=pd.DataFrame(rows).sort_values(['action','local_date']).reset_index(drop=True)
    b=d[d.action=='BASELINE']
    if len(b)!=50 or int(b.net_win.sum())!=25 or int((~b.net_win).sum())!=25:
        raise AssertionError('baseline 25/25 integrity failed')
    return d


def pf(vals):
    x=pd.to_numeric(vals,errors='coerce').fillna(0.0)
    pos=float(x[x>0].sum()); neg=float(-x[x<0].sum())
    return pos/neg if neg>0 else (math.inf if pos>0 else np.nan)


def summarize(d):
    out=[]
    for action in ACTIONS:
        q=d[d.action==action].copy()
        execq=q[q.executed.astype(bool)]
        out.append({'action':action,'L_to_W':int((q.transition=='L_TO_W').sum()),'L_to_NT':int((q.transition=='L_TO_NT').sum()),
                    'W_to_W':int((q.transition=='W_TO_W').sum()),'W_to_L':int((q.transition=='W_TO_L').sum()),
                    'W_to_NT':int((q.transition=='W_TO_NT').sum()),'net_win_opportunities':int(q.net_win.sum()),
                    'executed_opportunities':len(execq),'trade_legs':int(pd.to_numeric(q.trade_legs,errors='coerce').fillna(0).sum()),
                    'net_wr_executed':float(execq.net_win.mean()) if len(execq) else np.nan,
                    'avg_net_return_per_opportunity':float(pd.to_numeric(q.net_return,errors='coerce').fillna(0).mean()),
                    'total_pnl_usd_500':float(pd.to_numeric(q.pnl_usd_500,errors='coerce').fillna(0).sum()),
                    'profit_factor_opportunity':pf(q.pnl_usd_500)})
    s=pd.DataFrame(out)
    rank=s[s.action!='BASELINE'].sort_values(['L_to_W','W_to_W','net_win_opportunities','avg_net_return_per_opportunity'],
                                             ascending=[False,False,False,False]).reset_index(drop=True)
    rank['rank']=np.arange(1,len(rank)+1)
    base=s[s.action=='BASELINE'].copy(); base['rank']=0
    return pd.concat([base,rank],ignore_index=True)


def main():
    prereg=ROOT/f'{PFX}_Preregistration.md'
    if not prereg.exists(): raise AssertionError('B27EV preregistration missing')
    x5,cov=b27em.data_base.load5(TARGET)
    if cov<.995: raise AssertionError(f'coverage gate failed {cov}')
    d=build(x5); d.to_csv(OUT_DETAIL,index=False)
    s=summarize(d); s.to_csv(OUT_SUM,index=False)
    ranked=s[s.action!='BASELINE'].sort_values('rank')
    base=s[s.action=='BASELINE'].iloc[0]
    leader=ranked.iloc[0]
    lines=[
        '# BNB Session-Native LONG M10 Loss Conversion Discovery — B27EV Result','',
        f'Raw BNB 5m coverage: **{cov:.4%}**.','',
        'Development only. Frozen baseline: **E5_MICRO_HL_BULL**, TP **H+0.30R**, SL **0.30R**, total cost **0.15%**.','',
        f'Baseline integrity: **50 opportunities = 25 net wins + 25 net losses**, net WR **{100*base.net_wr_executed:.1f}%**.','',
        'Primary objective is **actual original loss → actual net win**. No-trades are reported separately and never counted as conversions.','',
        '| Rank | Intervention | L→W | L→NT | W→W | W→L | W→NT | Net wins /50 | Executed opps | Trade legs | Net WR executed | Avg net/opp | PnL @ $500 | PF |',
        '|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    lines.append(f"| 0 | BASELINE | 0 | 0 | 25 | 0 | 0 | {int(base.net_win_opportunities)}/50 | {int(base.executed_opportunities)} | {int(base.trade_legs)} | {100*base.net_wr_executed:.1f}% | {100*base.avg_net_return_per_opportunity:.3f}% | ${base.total_pnl_usd_500:.2f} | {base.profit_factor_opportunity:.2f} |")
    for _,r in ranked.iterrows():
        wr='-' if pd.isna(r.net_wr_executed) else f'{100*r.net_wr_executed:.1f}%'
        pfs='inf' if math.isinf(r.profit_factor_opportunity) else f'{r.profit_factor_opportunity:.2f}'
        lines.append(f"| {int(r['rank'])} | {r.action} | {int(r.L_to_W)} | {int(r.L_to_NT)} | {int(r.W_to_W)} | {int(r.W_to_L)} | {int(r.W_to_NT)} | {int(r.net_win_opportunities)}/50 | {int(r.executed_opportunities)} | {int(r.trade_legs)} | {wr} | {100*r.avg_net_return_per_opportunity:.3f}% | ${r.total_pnl_usd_500:.2f} | {pfs} |")
    lines += ['', '## Development-only conversion leader','',
              f"By the preregistered ranking, **{leader.action}** ranks first: it converts **{int(leader.L_to_W)}/25** original losses into actual net wins while retaining **{int(leader.W_to_W)}/25** original winners.", '',
              f"Resulting net-positive opportunities: **{int(leader.net_win_opportunities)}/50 ({100*leader.net_win_opportunities/50:.1f}%)**. This is discovery, **not validation**.", '',
              'No interventions are combined in B27EV. A combination, threshold, or holdout test requires a new preregistered milestone.','',
              '**Status: B27EV_BNB_MICROHL_LOSS_CONVERSION_DEV_COMPLETE**','',
              'STOP: no holdout reveal, no intervention combination, no threshold retuning, no August, no SHORT/live integration.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    OUT_STATUS.write_text('B27EV_BNB_MICROHL_LOSS_CONVERSION_DEV_COMPLETE\n')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
