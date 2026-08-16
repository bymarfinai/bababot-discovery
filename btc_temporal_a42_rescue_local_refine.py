"""BTC Temporal A4.2 — local refinement of the robust 5-minute rescue state.

Parent state from A4.1:
- original Tuesday 06:00 SELL, TP/SL 0.5/0.5
- after first completed 5m bar, trade is >= +0.15% adverse to short
- favorable excursion (short MFE) stayed < 0.10%
- flip BUY 0.5/0.5 for the remaining original 4h horizon

This pass only refines nearby interpretable boundaries and optional flow/location
confirmation. Configuration is selected on first 60% Tuesdays and independently
reported on last 40% validation.
"""
import json
import btc_temporal_a4_rescue_engine as a4

CP=5
ADVERSE=(0.08,0.10,0.12,0.15,0.18,0.20)
MFE_MAX=(0.05,0.075,0.10,0.125,0.15)
TAKER_MIN=(None,0.0,0.01,0.02)
CLOSEPOS_MIN=(None,0.60,0.70)
ACTIONS=('FLIP','CUT')


def cond(fv,adv,mfe_max,taker_min,cpmin):
    if fv is None:return False
    net,mfe,mae,close_pos,up_frac,last_ret,eff,taker,ttrend=fv[:9]
    if net<adv or mfe>=mfe_max:return False
    if taker_min is not None and taker<=taker_min:return False
    if cpmin is not None and close_pos<=cpmin:return False
    return True


def evaluate(records,adv,mfe_max,taker_min,cpmin,action):
    cooked=[]
    for r in records:
        final=r['base'];act='HOLD';fv=r['fv']
        if cond(fv,adv,mfe_max,taker_min,cpmin):
            if action=='CUT':
                final=a4.exit_short_at(r['rows'],r['i'],CP);act='CUT'
            else:
                q=a4.long_after_flip(r['rows'],r['i'],CP)
                if q is not None:final=q;act='FLIP'
        cooked.append({'ts':r['ts'],'base':r['base'],'final':final,'original_class':r['original_class'],'action':act,'p_loss':None})
    z=a4.summarize_policy(cooked,CP,0,adv,action)
    z.update({'adverse_min_pct':adv,'mfe_max_pct':mfe_max,'taker_min':taker_min,'close_pos_min':cpmin,'action_type':action})
    return z


def main():
    rows=a4.load();im={x[0]:i for i,x in enumerate(rows)}
    expected=(a4.EVAL_END-a4.EVAL_START)//a4.TF
    exact=sum(a4.EVAL_START<=x[0]<a4.EVAL_END for x in rows)
    idx=[]
    for x in rows:
        if a4.EVAL_START<=x[0]<a4.EVAL_END:
            dt=a4.ldt(x[0])
            if dt.weekday()==1 and dt.hour==6 and dt.minute==0:idx.append(im[x[0]])
    recs=[]
    for i in idx:
        b=a4.base_trade(rows,i,a4.TP,a4.SL,a4.HOLD);ft=a4.first_touch_state(rows,i)
        recs.append({'i':i,'ts':rows[i][0],'base':b['net_usd'],'original_class':ft[0] if ft else 'NA','rows':rows,'fv':a4.feature_vector(rows,i,CP)})
    split=int(len(recs)*.60);disc=recs[:split];val=recs[split:]
    grid=[]
    for adv in ADVERSE:
      for mf in MFE_MAX:
       for tk in TAKER_MIN:
        for cpmin in CLOSEPOS_MIN:
         for act in ACTIONS:
          d=evaluate(disc,adv,mf,tk,cpmin,act)
          v=evaluate(val,adv,mf,tk,cpmin,act)
          f=evaluate(recs,adv,mf,tk,cpmin,act)
          score=d['delta_vs_base_usd']+2*d['sl_to_positive']-4*d['tp_damaged']
          grid.append({'score':a4.rnd(score,3),'discovery':d,'validation':v,'full':f})
    ranked=sorted(grid,key=lambda x:(x['score'],x['discovery']['delta_vs_base_usd']),reverse=True)
    cross=[x for x in grid if x['discovery']['delta_vs_base_usd']>0 and x['validation']['delta_vs_base_usd']>0 and x['validation']['tp_damaged']<=x['validation']['sl_to_positive']]
    cross=sorted(cross,key=lambda x:(x['full']['net_pnl_usd'],x['validation']['delta_vs_base_usd'],x['full']['sl_to_positive']-x['full']['tp_damaged']),reverse=True)
    clean=[x for x in cross if x['validation']['tp_damaged']==0]
    out={'status':'A42_RESCUE_LOCAL_REFINE','data':{'coverage':a4.rnd(100*exact/expected,2),'rows_5m':exact,'tuesdays':len(recs),'discovery':len(disc),'validation':len(val),'configs':len(grid),'checkpoint_min':CP},
         'best_discovery_selected':ranked[:20],'best_cross_period':cross[:25],'best_cross_period_zero_validation_damage':clean[:25]}
    print('COVERAGE',exact,expected,a4.rnd(100*exact/expected,2),'TUESDAYS',len(recs),flush=True)
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)

if __name__=='__main__':main()
