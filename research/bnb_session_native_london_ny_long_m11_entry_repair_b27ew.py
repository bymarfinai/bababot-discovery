from __future__ import annotations

from pathlib import Path
import sys
import math
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
RESEARCH=ROOT/'research'
for p in (str(ROOT),str(RESEARCH)):
    if p not in sys.path:
        sys.path.insert(0,p)

import bnb_session_native_london_ny_long_m1_structure_b27em as b27em
import bnb_session_native_london_ny_long_m7_entry_economics_b27es as b27es

TARGET='BNBUSDT'
BAR5=pd.Timedelta(minutes=5)
CAND='E5_MICRO_HL_BULL'
EXT_R=.30
STOP_R=.30
COST=b27es.TOTAL_COST
NOTIONAL=b27es.ILLUSTRATIVE_NOTIONAL
PFX='BNB_SESSION_NATIVE_LONDON_NY_LONG_M11_ENTRY_REPAIR_B27EW'
OUT_DETAIL=ROOT/f'{PFX}_Detail.csv'
OUT_SUM=ROOT/f'{PFX}_Summary.csv'
OUT_MD=ROOT/f'{PFX}_Result.md'
OUT_STATUS=ROOT/f'{PFX}_Status.txt'

ACTIONS=[
    'BASELINE',
    'S05_SPLIT_ADD_005R','S10_SPLIT_ADD_010R','S15_SPLIT_ADD_015R','S20_SPLIT_ADD_020R','S25_SPLIT_ADD_025R',
    'D10_RECLAIM_ORIGINAL','D20_RECLAIM_ORIGINAL','D10_FRESH_MICROHL',
]
ADD_R={
    'S05_SPLIT_ADD_005R':.05,'S10_SPLIT_ADD_010R':.10,'S15_SPLIT_ADD_015R':.15,
    'S20_SPLIT_ADD_020R':.20,'S25_SPLIT_ADD_025R':.25,
}


def basic_sim(q,entry_px,H,R):
    z=b27es.simulate_one(q,float(entry_px),float(H),float(R),EXT_R,STOP_R)
    z.update({'executed':True,'trade_legs':1})
    return z


def failed_before_h(q,base,H):
    if bool(base['net_win']):
        return False
    et=pd.Timestamp(base['exit_ts'])
    if str(base['exit_type']) in ('SL','SL_BOTH'):
        pre=q[q.index<et]
    else:
        pre=q[q.index<=et]
    hit=bool((not pre.empty) and float(pre.high.max())>=float(H))
    return not hit


def conservative_limit_leg(q,limit_px,H,R):
    # Resting buy limit. Locate first eligible fill bar.
    hit=q[q.low.astype(float)<=float(limit_px)]
    if hit.empty:
        return None
    fill_ts=hit.index[0]
    bar=hit.iloc[0]
    o=float(bar.open)
    px=o if o<=float(limit_px) else float(limit_px)
    target=float(H)+EXT_R*float(R)
    stop=px-STOP_R*float(R)

    # If filled intrabar (open above limit), target on the fill bar is ignored because
    # OHLC cannot prove it occurred after the fill. Stop on the fill bar is allowed
    # conservatively if the low reaches it. If filled at open, normal SL-first ordering applies.
    intrabar=o>float(limit_px)
    if float(bar.low)<=stop:
        exit_px=stop; exit_ts=fill_ts; exit_type='SL_ENTRY_BAR'
        gross=exit_px/px-1.0; net=gross-COST
        return {'entry_ts':fill_ts,'entry_px':px,'exit_ts':exit_ts,'exit_px':exit_px,'exit_type':exit_type,
                'gross_return':gross,'net_return':net,'net_win':net>0}
    if (not intrabar) and float(bar.high)>=target:
        exit_px=target; exit_ts=fill_ts; exit_type='TP_ENTRY_BAR'
        gross=exit_px/px-1.0; net=gross-COST
        return {'entry_ts':fill_ts,'entry_px':px,'exit_ts':exit_ts,'exit_px':exit_px,'exit_type':exit_type,
                'gross_return':gross,'net_return':net,'net_win':net>0}

    rest=q[q.index>fill_ts]
    if rest.empty:
        exit_px=float(bar.close); exit_ts=fill_ts; exit_type='SESSION_CLOSE_ENTRY_BAR'
    else:
        exit_px=float(rest.iloc[-1].close); exit_ts=rest.index[-1]; exit_type='SESSION_CLOSE'
        for ts,r in rest.iterrows():
            sl=float(r.low)<=stop; tp=float(r.high)>=target
            if sl:
                exit_px=stop; exit_ts=ts; exit_type='SL_BOTH' if tp else 'SL'; break
            if tp:
                exit_px=target; exit_ts=ts; exit_type='TP'; break
    gross=exit_px/px-1.0; net=gross-COST
    return {'entry_ts':fill_ts,'entry_px':px,'exit_ts':exit_ts,'exit_px':exit_px,'exit_type':exit_type,
            'gross_return':gross,'net_return':net,'net_win':net>0}


def split_sim(q,entry_px,H,R,add_r,baseline):
    # First 50% is the original leg. Second 50% is a resting limit, but may only fill
    # strictly before a barrier exit of leg 1; this avoids same-bar path invention.
    first=dict(baseline)
    et=pd.Timestamp(first['exit_ts'])
    if str(first['exit_type'])=='SESSION_CLOSE':
        scan=q[q.index<=et]
    else:
        scan=q[q.index<et]
    limit=float(entry_px)-float(add_r)*float(R)
    second=conservative_limit_leg(scan,limit,H,R) if not scan.empty else None
    net=.5*float(first['net_return'])
    legs=1
    add_filled=False
    if second is not None:
        # Once the second leg fills before leg-1 exit, simulate it through the full remaining session.
        fill_ts=pd.Timestamp(second['entry_ts'])
        full_post=q[q.index>=fill_ts]
        second=conservative_limit_leg(full_post,limit,H,R)
        net += .5*float(second['net_return'])
        legs=2; add_filled=True
    return {'executed':True,'trade_legs':legs,'net_return':net,'pnl_usd_500':net*NOTIONAL,
            'net_win':net>0,'exit_type':'SPLIT','exit_ts':max(pd.Timestamp(first['exit_ts']),pd.Timestamp(second['exit_ts'])) if second is not None else pd.Timestamp(first['exit_ts']),
            'entry_ts_new':q.index[0],'entry_px_new':float(entry_px),'add_filled':add_filled,
            'add_entry_ts':pd.Timestamp(second['entry_ts']) if second is not None else pd.NaT,
            'add_entry_px':float(second['entry_px']) if second is not None else np.nan}


def delayed_repair(action,exe,original_entry_ts,original_entry_px,H,R):
    q=exe[exe.index>=pd.Timestamp(original_entry_ts)].copy()
    if q.empty:
        return None
    dip_r=.10 if action in ('D10_RECLAIM_ORIGINAL','D10_FRESH_MICROHL') else .20
    dip_level=float(original_entry_px)-dip_r*float(R)
    dipped=False
    prev=None
    for ts,row in q.iterrows():
        if float(row.low)<=dip_level:
            dipped=True
        ok=False
        if dipped and action in ('D10_RECLAIM_ORIGINAL','D20_RECLAIM_ORIGINAL'):
            ok=float(row.close)>=float(original_entry_px)
        elif dipped and action=='D10_FRESH_MICROHL' and prev is not None:
            ok=(float(row.low)>float(prev.low) and float(row.close)>float(prev.close) and float(row.close)>float(row.open))
        if ok:
            fill_ts=ts+BAR5
            if fill_ts not in exe.index:
                return None
            px=float(exe.loc[fill_ts].open)
            post=exe[exe.index>=fill_ts]
            if post.empty:
                return None
            z=basic_sim(post,px,H,R)
            z.update({'entry_ts_new':fill_ts,'entry_px_new':px,'trigger_ts':ts,'dip_R':dip_r})
            return z
        prev=row
    return None


def build(x5):
    entries,exec_map=b27es.build_entries(x5)
    e=entries[entries.candidate==CAND].copy().sort_values('entry_ts')
    if len(e)!=50:
        raise AssertionError(f'expected 50 E5 entries got {len(e)}')
    sessions=b27em.session_rows(x5)
    dev=sessions[(sessions.partition=='development') & sessions.leave.fillna(False).astype(bool)].copy()
    smap={str(r.local_date):r for _,r in dev.iterrows()}
    rows=[]
    failed_count=0
    for _,r in e.iterrows():
        date=str(r.local_date); s=smap[date]
        exe=b27em.fs(x5,pd.Timestamp(s.ny_open_utc),pd.Timestamp(s.ny_close_utc))
        q=exec_map[(date,CAND)]
        entry_px=float(r.entry_px); H=float(r.H); R=float(r.R)
        base=basic_sim(q,entry_px,H,R)
        base_win=bool(base['net_win'])
        fb=failed_before_h(q,base,H)
        failed_count += int(fb)
        for action in ACTIONS:
            if action=='BASELINE':
                z=dict(base); z.update({'executed':True,'trade_legs':1,'pnl_usd_500':float(base['net_return'])*NOTIONAL,
                                        'entry_ts_new':pd.Timestamp(r.entry_ts),'entry_px_new':entry_px})
            elif action in ADD_R:
                z=split_sim(q,entry_px,H,R,ADD_R[action],base)
            else:
                z=delayed_repair(action,exe,pd.Timestamp(r.entry_ts),entry_px,H,R)
                if z is None:
                    z={'executed':False,'trade_legs':0,'net_return':0.0,'pnl_usd_500':0.0,'net_win':False,
                       'exit_type':'NO_TRADE','exit_ts':pd.NaT,'entry_ts_new':pd.NaT,'entry_px_new':np.nan}
                else:
                    z['pnl_usd_500']=float(z['net_return'])*NOTIONAL
            new_win=bool(z['net_win'])
            if base_win and new_win: trans='W_TO_W'
            elif base_win and not bool(z['executed']): trans='W_TO_NT'
            elif base_win: trans='W_TO_L'
            elif new_win: trans='L_TO_W'
            elif not bool(z['executed']): trans='L_TO_NT'
            else: trans='L_TO_L'
            rec={'local_date':date,'action':action,'baseline_win':base_win,'baseline_failed_before_H':fb,
                 'baseline_net_return':float(base['net_return']),'baseline_exit_type':str(base['exit_type']),
                 'transition':trans,'H':H,'R':R,'original_entry_px':entry_px}
            rec.update(z); rows.append(rec)
    if failed_count!=19:
        raise AssertionError(f'expected 19 baseline failed-before-H losses, got {failed_count}')
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
        q=d[d.action==action].copy(); ex=q[q.executed.astype(bool)]
        fb=q[q.baseline_failed_before_H.astype(bool)]
        out.append({
            'action':action,
            'L_to_W':int((q.transition=='L_TO_W').sum()),'L_to_L':int((q.transition=='L_TO_L').sum()),'L_to_NT':int((q.transition=='L_TO_NT').sum()),
            'failed_before_H_L_to_W':int((fb.transition=='L_TO_W').sum()),
            'W_to_W':int((q.transition=='W_TO_W').sum()),'W_to_L':int((q.transition=='W_TO_L').sum()),'W_to_NT':int((q.transition=='W_TO_NT').sum()),
            'net_win_opportunities':int(q.net_win.sum()),'executed_opportunities':len(ex),
            'trade_legs':int(pd.to_numeric(q.trade_legs,errors='coerce').fillna(0).sum()),
            'net_wr_executed':float(ex.net_win.mean()) if len(ex) else np.nan,
            'avg_net_return_per_opportunity':float(pd.to_numeric(q.net_return,errors='coerce').fillna(0).mean()),
            'total_pnl_usd_500':float(pd.to_numeric(q.pnl_usd_500,errors='coerce').fillna(0).sum()),
            'profit_factor_opportunity':pf(q.pnl_usd_500),
        })
    s=pd.DataFrame(out)
    rank=s[s.action!='BASELINE'].sort_values(
        ['L_to_W','failed_before_H_L_to_W','W_to_W','net_win_opportunities','avg_net_return_per_opportunity'],
        ascending=[False,False,False,False,False]).reset_index(drop=True)
    rank['rank']=np.arange(1,len(rank)+1)
    base=s[s.action=='BASELINE'].copy(); base['rank']=0
    return pd.concat([base,rank],ignore_index=True)


def main():
    prereg=ROOT/f'{PFX}_Preregistration.md'
    if not prereg.exists():
        raise AssertionError('B27EW preregistration missing')
    x5,cov=b27em.data_base.load5(TARGET)
    if cov<.995:
        raise AssertionError(f'coverage gate failed {cov}')
    d=build(x5); d.to_csv(OUT_DETAIL,index=False)
    s=summarize(d); s.to_csv(OUT_SUM,index=False)
    base=s[s.action=='BASELINE'].iloc[0]
    ranked=s[s.action!='BASELINE'].sort_values('rank')
    lead=ranked.iloc[0]
    lines=[
        '# BNB Session-Native LONG M11 Failed-Before-H Entry Repair Discovery — B27EW Result','',
        f'Raw BNB 5m coverage: **{cov:.4%}**.','',
        'Development only. Frozen baseline: **E5_MICRO_HL_BULL**, TP **H+0.30R**, SL **0.30R**, total cost **0.15%**.','',
        'Baseline integrity: **50 opportunities = 25 net wins + 25 net losses**; **19/25 losses failed before H**.','',
        'Primary objective: **original loss -> actual net win**. No-trades do not count as conversions.','',
        '| Rank | Entry repair | L→W | FBH L→W | L→NT | W→W | W→L | W→NT | Net wins/50 | Executed | Legs | WR executed | Avg net/opp | PnL @ $500 | PF |',
        '|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _,r in s.sort_values('rank').iterrows():
        lines.append(f"| {int(r['rank'])} | {r.action} | {int(r.L_to_W)} | {int(r.failed_before_H_L_to_W)} | {int(r.L_to_NT)} | {int(r.W_to_W)} | {int(r.W_to_L)} | {int(r.W_to_NT)} | {int(r.net_win_opportunities)}/50 | {int(r.executed_opportunities)} | {int(r.trade_legs)} | {100*r.net_wr_executed:.1f}% | {100*r.avg_net_return_per_opportunity:.3f}% | ${r.total_pnl_usd_500:.2f} | {r.profit_factor_opportunity:.2f} |")
    lines += ['', '## Development discovery leader','',
              f"By preregistered loss-conversion ranking: **{lead.action}** converts **{int(lead.L_to_W)}/25** original losses, including **{int(lead.failed_before_H_L_to_W)}/19** failed-before-H losses, while retaining **{int(lead.W_to_W)}/25** original winners.",
              f"Resulting net-positive opportunities: **{int(lead.net_win_opportunities)}/50 ({100*lead.net_win_opportunities/50:.1f}%)**.",'',
              'This is development discovery only. No entry repair is validated or promoted here.','',
              '**Status: B27EW_BNB_FAILED_BEFORE_H_ENTRY_REPAIR_DEV_COMPLETE**','',
              'STOP: no intervention combination, no partial-management combination, no external/reference-validation/August reveal, no threshold retuning, no SHORT/live integration.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    OUT_STATUS.write_text('B27EW_BNB_FAILED_BEFORE_H_ENTRY_REPAIR_DEV_COMPLETE\n')
    print(OUT_MD.read_text())

if __name__=='__main__':
    main()
