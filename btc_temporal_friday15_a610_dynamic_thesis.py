"""BTC Friday15 A6.10 — dynamic thesis-state on ALL 138 Friday occurrences.

Parent stays every Friday 15:00 WIB BUY, TP2.0 / SL0.7 / max6h / fee0.15% / $500.
No pre-entry skip. Candidate early-failure states are evaluated at 15/30/60m using only
completed 5m candles before the decision open. Candidate selection uses discovery only.
Then the frozen selected detector is evaluated on validation and with HOLD/CUT/FLIP actions.
"""
import json
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_friday15_a69b_full_loss_forensics as a69
import btc_temporal_saturday18_a74_loss_forensics as a74
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END

TP=2.0; SL=.7; HOLD=360; NOTIONAL=500.0; FEE_USD=.75
CHECKS=(15,30,60)
SHORT_GEOMS=((.7,.7),(1.0,.7),(1.0,1.0))


def econ_pnls(p):
    n=len(p); pos=sum(x for x in p if x>0); neg=-sum(x for x in p if x<0)
    return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2) if n else None,
            'pnl':rnd(sum(p),3),'exp':rnd(sum(p)/n,4) if n else None,
            'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(a60.max_dd(p),3) if p else 0,
            'ls':a60.loss_streak(p) if p else 0}

def detector_defs(h):
    return (
      (f'{h}_NO03_NEG', lambda c: c['mfe']<.3 and c['progress']<0),
      (f'{h}_NO03_NEG_FLOW', lambda c: c['mfe']<.3 and c['progress']<0 and c['taker']<0),
      (f'{h}_NO03_NEG_D20', lambda c: c['mfe']<.3 and c['progress']<0 and c['d20']<0),
      (f'{h}_NO03_NEG_FLOW_D20', lambda c: c['mfe']<.3 and c['progress']<0 and c['taker']<0 and c['d20']<0),
      (f'{h}_NO03_NEG_FLOW_D20_SLOPE', lambda c: c['mfe']<.3 and c['progress']<0 and c['taker']<0 and c['d20']<0 and c['s20_15']<0),
    )

def det_stats(q,name,fn,h):
    sig=[r for r in q if fn(r['checks'][str(h)])]
    n=len(sig); losses=sum(r['trade']['net_usd']<=0 for r in sig); a=sum(r['label']=='A_WRONG_WAY_LT_03' for r in sig); wins=sum(r['trade']['net_usd']>0 for r in sig)
    return {'rule':name,'h':h,'signals':n,'eventual_loss':losses,'A_wrongway':a,'false_winner':wins,
            'loss_precision':rnd(100*losses/n,2) if n else None,'A_precision':rnd(100*a/n,2) if n else None,
            'A_recall':rnd(100*a/max(1,sum(r['label']=='A_WRONG_WAY_LT_03' for r in q)),2) if n else 0}

def cut_net(r,h):
    j=r['i']+h//5; px=r['rows'][j][1] if 'rows' in r else None
    raise RuntimeError('unused')

def short_leg(rows,j,end_idx,tp,sl):
    e=rows[j][1]; tp_px=e*(1-tp/100); sl_px=e*(1+sl/100)
    for k in range(j,end_idx):
        x=rows[k]; hit_tp=x[3]<=tp_px; hit_sl=x[2]>=sl_px
        if hit_tp and hit_sl: return -sl/100*NOTIONAL-FEE_USD
        if hit_sl: return -sl/100*NOTIONAL-FEE_USD
        if hit_tp: return tp/100*NOTIONAL-FEE_USD
    exit_px=rows[end_idx][1]
    return (e-exit_px)/e*NOTIONAL-FEE_USD

def action_pnl(rows,r,h,mode,geom=None):
    if not r['signal']: return r['trade']['net_usd']
    j=r['i']+h//5; e=r['entry']; px=rows[j][1]
    long_net=(px-e)/e*NOTIONAL-FEE_USD
    if mode=='CUT': return long_net
    if mode=='FLIP':
        end_idx=r['i']+HOLD//5
        return long_net+short_leg(rows,j,end_idx,geom[0],geom[1])
    return r['trade']['net_usd']

def main():
    rows=load(); im={x[0]:i for i,x in enumerate(rows)}; e7=a74.ema_series(rows,7); e20=a74.ema_series(rows,20); rec=[]
    for x in rows:
        if not(EVAL_START<=x[0]<EVAL_END): continue
        d=ldt(x[0])
        if not(d.weekday()==4 and d.hour==15 and d.minute==0): continue
        i=im[x[0]]; t=a60.trade(rows,i,TP,SL,HOLD); p=a69.path_stats(rows,i,x[1])
        if t is None or p is None: continue
        r={'i':i,'ts':x[0],'entry':x[1],'trade':t,'path':p}; r['label']=a69.label(r)
        r['checks']={str(h):a69.checkpoint(rows,r,e7,e20,h) for h in CHECKS}
        if all(r['checks'].values()): rec.append(r)
    disc=rec[:82]; val=rec[82:]
    candidates=[]
    for h in CHECKS:
        for name,fn in detector_defs(h):
            ds=det_stats(disc,name,fn,h); vs=det_stats(val,name,fn,h); fs=det_stats(rec,name,fn,h)
            # selection score uses DISCOVERY ONLY: prioritize loss precision, then A capture, require >=8 signals
            score=(-1e9 if ds['signals']<8 else ds['loss_precision']*100+ds['A_wrongway']-ds['false_winner'])
            candidates.append({'name':name,'h':h,'score_disc':score,'discovery':ds,'validation':vs,'full':fs})
    chosen=max(candidates,key=lambda z:z['score_disc'])
    h=chosen['h']; fn=dict(detector_defs(h))[chosen['name']]
    for r in rec: r['signal']=bool(fn(r['checks'][str(h)]))
    # Action choice also discovery-only among CUT and three fixed SHORT geometries.
    action_rows=[]
    base_disc=[r['trade']['net_usd'] for r in disc]; base_val=[r['trade']['net_usd'] for r in val]; base_full=[r['trade']['net_usd'] for r in rec]
    for mode,geom in [('CUT',None)]+[('FLIP',g) for g in SHORT_GEOMS]:
        pd=[action_pnl(rows,r,h,mode,geom) for r in disc]; pv=[action_pnl(rows,r,h,mode,geom) for r in val]; pf=[action_pnl(rows,r,h,mode,geom) for r in rec]
        action_rows.append({'mode':mode,'geom':geom,'discovery':econ_pnls(pd),'validation':econ_pnls(pv),'full':econ_pnls(pf),
          'delta_disc':rnd(sum(pd)-sum(base_disc),3),'delta_val':rnd(sum(pv)-sum(base_val),3),'delta_full':rnd(sum(pf)-sum(base_full),3)})
    selected_action=max(action_rows,key=lambda z:z['discovery']['pnl'])
    sig=[r for r in rec if r['signal']]
    out={'status':'FRIDAY15_A610_DYNAMIC_THESIS','parent':{'full':econ_pnls(base_full),'discovery':econ_pnls(base_disc),'validation':econ_pnls(base_val)},
      'candidate_selection':'discovery only; >=8 discovery signals; rank loss precision then A capture/false winners',
      'candidates':candidates,'chosen_detector':chosen,
      'signal_labels_full':{lab:sum(r['label']==lab for r in sig) for lab in ('WIN','A_WRONG_WAY_LT_03','B_WEAK_POP_03_05','C_GIVEBACK_05_10','D_DEEP_GIVEBACK_GE_10')},
      'actions':action_rows,'selected_action_discovery_only':selected_action}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__': main()
