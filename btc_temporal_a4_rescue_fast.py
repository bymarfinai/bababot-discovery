"""Fast cached runner for BTC Temporal A4 post-entry rescue research.
Methodology is identical to btc_temporal_a4_rescue_engine.py; expensive analogue
probabilities are computed once per Tuesday/checkpoint and reused across the
threshold/policy grid.
"""
import json, math, statistics
import btc_temporal_a4_rescue_engine as a4


def mean(xs): return statistics.mean(xs) if xs else 0.0


def probabilities_for_ks(history, curx):
    if len(history) < 12:
        return {k: None for k in a4.KS}
    d=len(curx)
    mus=[mean([h['x'][z] for h in history]) for z in range(d)]
    sds=[]
    for z in range(d):
        vals=[h['x'][z] for h in history]
        sd=statistics.pstdev(vals) if len(vals)>1 else 1.0
        sds.append(max(sd,1e-6))
    ds=[]
    for h in history:
        dist=0.0
        for z in range(d):
            aa=(curx[z]-mus[z])/sds[z]
            bb=(h['x'][z]-mus[z])/sds[z]
            dist+=(aa-bb)**2
        ds.append((dist,h['label']))
    ds.sort(key=lambda q:q[0])
    out={}
    for k in a4.KS:
        if len(history)<max(12,k//2):
            out[k]=None; continue
        q=ds[:min(k,len(ds))]
        sw=sl=0.0
        for dist,lab in q:
            w=1.0/(0.25+math.sqrt(max(dist,0.0)))
            sw+=w; sl+=w*lab
        out[k]=(sl+1.0)/(sw+2.0)
    return out


def apply_action(rows, rec, cp, policy):
    i=rec['i']; fv=rec['fv'][cp]
    if policy=='CUT':
        return 'CUT', a4.exit_short_at(rows,i,cp)
    if policy=='FLIP':
        q=a4.long_after_flip(rows,i,cp)
        return ('FLIP',q) if q is not None else ('HOLD',rec['base'])
    if a4.bullish_confirmation(fv):
        q=a4.long_after_flip(rows,i,cp)
        if q is not None:return 'FLIP',q
    return 'CUT',a4.exit_short_at(rows,i,cp)


def summarize(records, cp,k,th,policy):
    cooked=[]
    for r in records:
        action='HOLD'; final=r['base']
        p=r['prob'][cp].get(k)
        if r['fv'][cp] is not None and p is not None and p>=th:
            action,final=apply_action(r['rows'],r,cp,policy)
        cooked.append({'ts':r['ts'],'base':r['base'],'final':final,
                       'original_class':r['original_class'],'action':action,'p_loss':p})
    return a4.summarize_policy(cooked,cp,k,th,policy)


def main():
    rows=a4.load(); im={x[0]:i for i,x in enumerate(rows)}
    expected=(a4.EVAL_END-a4.EVAL_START)//a4.TF
    exact=sum(a4.EVAL_START<=x[0]<a4.EVAL_END for x in rows)
    all_idx=[]; tue_idx=[]
    for x in rows:
        dt=a4.ldt(x[0])
        if dt.hour==6 and dt.minute==0:
            i=im[x[0]];all_idx.append(i)
            if a4.EVAL_START<=x[0]<a4.EVAL_END and dt.weekday()==1:tue_idx.append(i)
    examples={cp:a4.build_examples(rows,all_idx,cp) for cp in a4.CHECKPOINTS}
    recs=[]
    for i in tue_idx:
        b=a4.base_trade(rows,i,a4.TP,a4.SL,a4.HOLD)
        ft=a4.first_touch_state(rows,i)
        rec={'i':i,'ts':rows[i][0],'base':b['net_usd'],'original_class':ft[0] if ft else 'NA',
             'fv':{},'prob':{},'rows':rows}
        for cp in a4.CHECKPOINTS:
            fv=a4.feature_vector(rows,i,cp);rec['fv'][cp]=fv
            if fv is None:
                rec['prob'][cp]={k:None for k in a4.KS};continue
            hist=[h for h in examples[cp] if h['ts']<rows[i][0]]
            rec['prob'][cp]=probabilities_for_ks(hist,fv)
        recs.append(rec)
    results=[]
    for cp in a4.CHECKPOINTS:
        for k in a4.KS:
            for th in a4.THRESHOLDS:
                for pol in a4.POLICIES:
                    results.append(summarize(recs,cp,k,th,pol))
    split=max(1,int(len(recs)*0.60));disc=recs[:split];val=recs[split:]
    ranked=[]
    for cp in a4.CHECKPOINTS:
        for k in a4.KS:
            for th in a4.THRESHOLDS:
                for pol in a4.POLICIES:
                    r=summarize(disc,cp,k,th,pol)
                    score=r['delta_vs_base_usd']-2.0*r['damaged_positive_to_negative']
                    ranked.append((score,r))
    ranked.sort(key=lambda z:(z[0],z[1]['positive_blocks'],z[1]['net_wr']),reverse=True)
    frozen=[]
    for score,r in ranked[:10]:
        vr=summarize(val,r['cp_min'],r['k'],r['threshold'],r['policy'])
        frozen.append({'discovery_score':a4.rnd(score,3),'discovery':r,'validation':vr})
    bynet=sorted(results,key=lambda r:(r['net_pnl_usd'],r['positive_blocks'],-r['damaged_positive_to_negative']),reverse=True)
    byrescue=sorted(results,key=lambda r:(r['sl_to_positive']-r['tp_damaged'],r['net_pnl_usd']),reverse=True)
    basep=[r['base'] for r in recs]
    out={'status':'A4_POST_ENTRY_RESCUE_CACHED','data':{
        'coverage':a4.rnd(100*exact/expected,2),'rows_5m':exact,'tuesdays':len(recs),
        'entry':'Tuesday 06:00 WIB SELL','tp_pct':a4.TP,'sl_pct':a4.SL,'hold_min':a4.HOLD,
        'fee_per_position_roundtrip_pct':a4.FEE_PCT,'notional_usd':a4.NOTIONAL,
        'baseline_first_touch':{'tp':sum(r['original_class']=='TP' for r in recs),'sl':sum(r['original_class']=='SL' for r in recs),'timeout':sum(r['original_class']=='TIMEOUT' for r in recs)},
        'baseline_money':{'net_pnl_usd':a4.rnd(sum(basep),3),'net_wins':sum(x>0 for x in basep),'net_losses':sum(x<=0 for x in basep),'net_wr':a4.rnd(100*sum(x>0 for x in basep)/len(basep),2)},
        'config_count':len(results),'split':{'discovery_tuesdays':len(disc),'validation_tuesdays':len(val)}},
        'oracle_rescue_capacity':a4.oracle(rows,tue_idx),
        'best_fullsample_net':bynet[:20],
        'best_fullsample_rescue_balance':byrescue[:20],
        'discovery_selected_validation':frozen}
    print('COVERAGE',exact,expected,a4.rnd(100*exact/expected,2),'TUESDAYS',len(recs),flush=True)
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)

if __name__=='__main__':main()
