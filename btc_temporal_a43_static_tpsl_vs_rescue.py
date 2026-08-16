"""BTC Temporal A4.3 — dense static TP/SL sweep vs frozen A4 rescue.

Question: can a better static TP/SL on the exact same Tuesday 06:00 SELL entries
match or beat the apparent improvement from A4 post-entry rescue?

Frozen common setup:
- BTCUSDT, 971-day evaluation window from shared loader
- SELL every Tuesday exact 06:00 WIB 5m open
- max hold 240m
- conservative same-5m ambiguity = SL first
- fee 0.15% round-trip per position
- $500 notional ($10 x 50)

Static sweep:
- TP and SL 0.20%..1.20% in 0.05% steps (441 configs)
- includes 0.50/0.50 exactly
- no entry filtering

Robustness:
- first 60% Tuesdays = discovery
- last 40% = validation
- select static geometry on discovery only, then report validation
- full-sample rankings are descriptive only

Frozen rescue benchmark is recomputed from the A4.2 rule:
At 06:05, if original 0.5/0.5 SELL is still open, adverse move >= +0.12%,
short MFE < 0.15%, and taker-buy ratio >50%, close SELL and flip BUY 0.5/0.5
for the remaining original 4h horizon.
"""
import json
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END
from btc_temporal_a37_money_optimizer import trade, summarize, NOTIONAL, FEE_PCT
import btc_temporal_a4_rescue_engine as a4

HOLD=240
GRID=tuple(round(0.20+0.05*i,2) for i in range(21))


def idxs(rows):
    im={x[0]:i for i,x in enumerate(rows)}
    out=[]
    for x in rows:
        if not(EVAL_START<=x[0]<EVAL_END):
            continue
        dt=ldt(x[0])
        if dt.weekday()==1 and dt.hour==6 and dt.minute==0:
            out.append(im[x[0]])
    return out


def simulate_static(rows, indices, tp, sl):
    ts=[]
    for i in indices:
        t=trade(rows,i,tp,sl,HOLD)
        if t is None:
            return None
        ts.append(t)
    return summarize(ts,tp,sl,HOLD)


def rescue_cond(fv):
    if fv is None:
        return False
    net,mfe,mae,close_pos,up_frac,last_ret,eff,taker,ttrend=fv[:9]
    return net>=0.12 and mfe<0.15 and taker>0.0


def simulate_rescue(rows, indices):
    rec=[]
    for i in indices:
        b=trade(rows,i,0.5,0.5,HOLD)
        if b is None:
            continue
        ft=a4.first_touch_state(rows,i)
        orig=ft[0] if ft else 'NA'
        final=b['net_usd']; action='HOLD'
        fv=a4.feature_vector(rows,i,5)
        if rescue_cond(fv):
            q=a4.long_after_flip(rows,i,5)
            if q is not None:
                final=q; action='FLIP'
        rec.append({'ts':rows[i][0],'base':b['net_usd'],'final':final,'original_class':orig,'action':action,'p_loss':None})
    z=a4.summarize_policy(rec,5,0,0.12,'FLIP')
    z.update({'rule':'A4.2 frozen: 5m adverse>=0.12, short MFE<0.15, taker-buy>50%, flip BUY 0.5/0.5'})
    return z


def compact(x):
    if x is None:return None
    keys=('tp_pct','sl_pct','rr','trades','tp_hits','sl_hits','timeouts','net_win_trades','net_loss_trades','net_wr','net_pnl_usd','expectancy_usd','profit_factor','max_dd_usd','max_loss_streak','positive_blocks','block_net_usd','avg_hold_min')
    return {k:x.get(k) for k in keys}


def main():
    rows=load(); all_idx=idxs(rows)
    split=int(len(all_idx)*0.60); disc_idx=all_idx[:split]; val_idx=all_idx[split:]
    expected=(EVAL_END-EVAL_START)//TF
    exact=sum(EVAL_START<=x[0]<EVAL_END for x in rows)

    configs=[]
    for tp in GRID:
        for sl in GRID:
            d=simulate_static(rows,disc_idx,tp,sl)
            v=simulate_static(rows,val_idx,tp,sl)
            f=simulate_static(rows,all_idx,tp,sl)
            configs.append({'tp':tp,'sl':sl,'disc':d,'val':v,'full':f})

    # Descriptive full-sample bests.
    by_full_net=sorted(configs,key=lambda x:(x['full']['net_pnl_usd'],x['full']['profit_factor'] or 0,-x['full']['max_dd_usd']),reverse=True)
    by_full_wr=sorted(configs,key=lambda x:(x['full']['net_wr'],x['full']['net_pnl_usd']),reverse=True)
    symmetric=[x for x in configs if abs(x['tp']-x['sl'])<1e-9]
    by_sym_full=sorted(symmetric,key=lambda x:(x['full']['net_pnl_usd'],x['full']['net_wr']),reverse=True)
    near=[x for x in configs if 0.35<=x['tp']<=0.65 and 0.35<=x['sl']<=0.65]
    by_near=sorted(near,key=lambda x:(x['full']['net_pnl_usd'],x['full']['net_wr']),reverse=True)

    # Proper chronological selection: choose by discovery economics, observe validation.
    sel_disc=sorted(configs,key=lambda x:(x['disc']['net_pnl_usd'],x['disc']['profit_factor'] or 0,-x['disc']['max_dd_usd']),reverse=True)
    cross=[x for x in configs if x['disc']['net_pnl_usd']>0 and x['val']['net_pnl_usd']>0]
    cross=sorted(cross,key=lambda x:(x['full']['net_pnl_usd'],x['val']['net_pnl_usd'],x['full']['positive_blocks']),reverse=True)

    base05={'disc':simulate_static(rows,disc_idx,0.5,0.5),'val':simulate_static(rows,val_idx,0.5,0.5),'full':simulate_static(rows,all_idx,0.5,0.5)}
    rescue={'disc':simulate_rescue(rows,disc_idx),'val':simulate_rescue(rows,val_idx),'full':simulate_rescue(rows,all_idx)}

    def pack(c):
        return {'tp':c['tp'],'sl':c['sl'],'discovery':compact(c['disc']),'validation':compact(c['val']),'full':compact(c['full'])}

    out={
      'status':'A43_STATIC_TPSL_VS_RESCUE',
      'data':{
        'coverage':rnd(100*exact/expected,2),'rows_5m':exact,'expected_5m':expected,
        'tuesdays':len(all_idx),'discovery':len(disc_idx),'validation':len(val_idx),
        'entry':'Tuesday 06:00 WIB SELL exact open','hold_min':HOLD,
        'grid_min_pct':GRID[0],'grid_max_pct':GRID[-1],'grid_step_pct':0.05,
        'static_configs':len(configs),'notional_usd':NOTIONAL,'fee_roundtrip_pct':FEE_PCT
      },
      'baseline_050_050':{'discovery':compact(base05['disc']),'validation':compact(base05['val']),'full':compact(base05['full'])},
      'frozen_rescue_050_050':rescue,
      'discovery_selected_static_top15':[pack(x) for x in sel_disc[:15]],
      'cross_period_positive_top15':[pack(x) for x in cross[:15]],
      'fullsample_best_net_top15':[pack(x) for x in by_full_net[:15]],
      'fullsample_best_wr_top15':[pack(x) for x in by_full_wr[:15]],
      'symmetric_best_top15':[pack(x) for x in by_sym_full[:15]],
      'near_050_best_top15':[pack(x) for x in by_near[:15]],
    }
    print('COVERAGE',exact,expected,rnd(100*exact/expected,2),'TUESDAYS',len(all_idx),flush=True)
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)

if __name__=='__main__':main()
