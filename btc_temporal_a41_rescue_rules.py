"""BTC Temporal A4.1 — interpretable winner/loser path atlas and rescue rules.

A4 established a large oracle rescue capacity but generic KNN failed to identify
losers. This pass learns simple causal post-entry states that can be frozen on a
60% discovery segment and evaluated on the last 40% validation segment.
"""
import json, statistics
import btc_temporal_a4_rescue_engine as a4

CPS=(5,10,15,20,30)
ADVERSE=(0.0,0.05,0.10,0.15,0.20,0.25)
MODES=('PRICE','FLOW50','FLOW52','MAE_DOM','NO_MFE10','BULL2')
ACTIONS=('CUT','FLIP')


def cond(fv,a,mode):
    if fv is None:return False
    net,mfe,mae,close_pos,up_frac,last_ret,eff,taker,ttrend=fv[:9]
    if net<a:return False
    if mode=='PRICE':return True
    if mode=='FLOW50':return taker>0
    if mode=='FLOW52':return taker>0.02
    if mode=='MAE_DOM':return mae>max(mfe,0.05)
    if mode=='NO_MFE10':return mfe<0.10
    if mode=='BULL2':return close_pos>0.60 and last_ret>0 and (taker>0 or ttrend>0)
    return False


def summarize(records,cp,a,mode,action):
    cooked=[]
    for r in records:
        act='HOLD';final=r['base']
        fv=r['fv'][cp]
        if cond(fv,a,mode):
            if action=='CUT':
                act='CUT';final=a4.exit_short_at(r['rows'],r['i'],cp)
            else:
                q=a4.long_after_flip(r['rows'],r['i'],cp)
                if q is not None:act='FLIP';final=q
        cooked.append({'ts':r['ts'],'base':r['base'],'final':final,'original_class':r['original_class'],'action':act,'p_loss':None})
    z=a4.summarize_policy(cooked,cp,0,a,action+'_'+mode)
    z['mode']=mode;z['adverse_min_pct']=a;z['action_type']=action
    return z


def atlas(records,cp):
    surv=[r for r in records if r['fv'][cp] is not None and r['original_class'] in ('TP','SL')]
    tp=[r for r in surv if r['original_class']=='TP'];sl=[r for r in surv if r['original_class']=='SL']
    def med(group,idx):
        return a4.rnd(statistics.median([r['fv'][cp][idx] for r in group]),4) if group else None
    bins=[(-99,-.20),(-.20,-.10),(-.10,0),(0,.10),(.10,.20),(.20,.30),(.30,99)]
    br=[]
    for lo,hi in bins:
        q=[r for r in surv if lo<=r['fv'][cp][0]<hi]
        if q:
            br.append({'lo':lo,'hi':hi,'n':len(q),'sl':sum(r['original_class']=='SL' for r in q),
                       'sl_rate':a4.rnd(100*sum(r['original_class']=='SL' for r in q)/len(q),2)})
    return {'cp_min':cp,'survivors':len(surv),'tp':len(tp),'sl':len(sl),
            'median_tp':{'net':med(tp,0),'mfe':med(tp,1),'mae':med(tp,2),'close_pos':med(tp,3),'taker_edge':med(tp,7)},
            'median_sl':{'net':med(sl,0),'mfe':med(sl,1),'mae':med(sl,2),'close_pos':med(sl,3),'taker_edge':med(sl,7)},
            'return_bins':br}


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
        rec={'i':i,'ts':rows[i][0],'base':b['net_usd'],'original_class':ft[0] if ft else 'NA','rows':rows,'fv':{}}
        for cp in CPS:rec['fv'][cp]=a4.feature_vector(rows,i,cp)
        recs.append(rec)
    split=int(len(recs)*.60);disc=recs[:split];val=recs[split:]
    atlas_all=[atlas(recs,cp) for cp in CPS]
    atlas_disc=[atlas(disc,cp) for cp in CPS]
    atlas_val=[atlas(val,cp) for cp in CPS]
    results=[];dr=[]
    for cp in CPS:
        for ad in ADVERSE:
            for mode in MODES:
                for act in ACTIONS:
                    full=summarize(recs,cp,ad,mode,act);results.append(full)
                    d=summarize(disc,cp,ad,mode,act)
                    # Money-first, with strong penalty for destroying old winners.
                    score=d['delta_vs_base_usd']+1.5*d['sl_to_positive']-3.0*d['tp_damaged']
                    dr.append((score,d))
    bynet=sorted(results,key=lambda r:(r['net_pnl_usd'],r['sl_to_positive']-r['tp_damaged'],r['positive_blocks']),reverse=True)
    byconvert=sorted(results,key=lambda r:(r['sl_to_positive']-r['tp_damaged'],r['delta_vs_base_usd']),reverse=True)
    dr.sort(key=lambda z:(z[0],z[1]['delta_vs_base_usd']),reverse=True)
    frozen=[];seen=set()
    for score,d in dr:
        key=(d['cp_min'],d['adverse_min_pct'],d['mode'],d['action_type'])
        if key in seen:continue
        seen.add(key)
        v=summarize(val,*key)
        frozen.append({'discovery_score':a4.rnd(score,3),'discovery':d,'validation':v})
        if len(frozen)>=15:break
    out={'status':'A41_INTERPRETABLE_RESCUE_RULES','data':{'coverage':a4.rnd(100*exact/expected,2),'rows_5m':exact,'tuesdays':len(recs),'discovery':len(disc),'validation':len(val),'configs':len(results)},
         'atlas_full':atlas_all,'atlas_discovery':atlas_disc,'atlas_validation':atlas_val,
         'best_fullsample_net':bynet[:20],'best_fullsample_conversion':byconvert[:20],
         'discovery_selected_validation':frozen}
    print('COVERAGE',exact,expected,a4.rnd(100*exact/expected,2),'TUESDAYS',len(recs),flush=True)
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)

if __name__=='__main__':main()
