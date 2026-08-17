"""Friday T-Method F5.3 — why Tuesday A5.2 separates but Friday F5.2 does not.

This is attribution, not a new champion search.

Apple-to-apple design:
- Tuesday control: frozen A5.2 parent/hinge/action implementation.
- Friday target: frozen F5.2 parent/hinge/action implementation.
- Every scheduled entry is retained.
- Hinge decision is causal: completed +0.50% trigger candle, act next 5m open.
- Compare oracle PROTECT-better vs RUNNER-better separability.
- Split remains first 60% discovery / last 40% validation.
- For each single feature, choose a threshold ONLY on discovery, freeze it, then
  report validation transfer. This is diagnostic transfer, not production tuning.

Feature families:
1) LOCAL_PATH: information accumulated from entry through the +0.50% hinge.
2) PREENTRY_REGIME: information fully known before the scheduled entry.

Question: Is Friday's failure caused by weak/non-stationary local path information,
or does a broader pre-entry regime variable restore stable RUNNER/PROTECT separation?
"""
import json, math, statistics
import btc_temporal_a52_runner_protect as T
import btc_temporal_friday15_f52_runner_protect as F
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END

LOCAL = (
    'time_min','progress_close','progress_decision','mfe','mae','taker_avg',
    'taker_last','close_pos_trigger','up_frac','efficiency','range_ratio','volume_ratio'
)
REGIME = (
    'day_pos','pre1','pre4','pre24','pre_ret15','pre_ret60','pre_ret240',
    'pre_rv60','pre_rv240','pre_range60','pre_range240','pre_taker60','pre_taker240',
    'pre_eff60','pre_eff240','pre_volume_pressure'
)


def med(xs):
    xs=[x for x in xs if x is not None and math.isfinite(x)]
    return rnd(statistics.median(xs),4) if xs else None


def mean(xs):
    xs=[x for x in xs if x is not None and math.isfinite(x)]
    return rnd(statistics.mean(xs),4) if xs else None


def quantile(xs,q):
    xs=sorted(x for x in xs if x is not None and math.isfinite(x))
    if not xs:return None
    if len(xs)==1:return xs[0]
    p=(len(xs)-1)*q; lo=int(math.floor(p)); hi=int(math.ceil(p))
    if lo==hi:return xs[lo]
    return xs[lo]+(xs[hi]-xs[lo])*(p-lo)


def auc_pairwise(pos,neg):
    """AUC for feature value: higher value predicts PROTECT-better."""
    pos=[x for x in pos if x is not None and math.isfinite(x)]
    neg=[x for x in neg if x is not None and math.isfinite(x)]
    if not pos or not neg:return None
    wins=ties=0
    for a in pos:
        for b in neg:
            if a>b:wins+=1
            elif a==b:ties+=1
    return rnd((wins+0.5*ties)/(len(pos)*len(neg)),4)


def contiguous_back(rows,i,n):
    if i-n<0:return False
    return all(rows[j][0]==rows[i][0]-(i-j)*TF for j in range(i-n,i))


def preentry_features(rows,i):
    e=rows[i][1]
    def window(n):
        if not contiguous_back(rows,i,n):return None
        q=rows[i-n:i]
        closes=[x[4] for x in q]
        rets=[]
        prev=q[0][1]
        for x in q:
            rets.append(100*(x[4]-prev)/prev)
            prev=x[4]
        rng=[100*(x[2]-x[3])/x[1] for x in q]
        tk=[x[9]/x[6]-0.5 if x[6] else 0.0 for x in q]
        path=sum(abs(x) for x in rets)
        signed=100*(e-q[0][1])/q[0][1]
        return {'ret':signed,'rv':statistics.mean(abs(x) for x in rets),
                'range':statistics.mean(rng),'taker':statistics.mean(tk),
                'eff':abs(signed)/max(path,1e-9),'vol_mean':statistics.mean(x[6] for x in q)}
    w3=window(3); w12=window(12); w48=window(48); w192=window(192)
    if not w12 or not w48:return {}
    # Current 60m volume relative to preceding 16h mean; pre-entry only.
    vp=None
    if w192 and w192['vol_mean']:
        vp=w12['vol_mean']/w192['vol_mean']
    return {
      'pre_ret15': w3['ret'] if w3 else None,
      'pre_ret60': w12['ret'], 'pre_ret240': w48['ret'],
      'pre_rv60': w12['rv'], 'pre_rv240': w48['rv'],
      'pre_range60': w12['range'], 'pre_range240': w48['range'],
      'pre_taker60': w12['taker'], 'pre_taker240': w48['taker'],
      'pre_eff60': w12['eff'], 'pre_eff240': w48['eff'],
      'pre_volume_pressure': vp,
    }


def make_indices(rows,weekday,hour):
    im={x[0]:i for i,x in enumerate(rows)}; out=[]
    for x in rows:
        if EVAL_START<=x[0]<EVAL_END:
            dt=ldt(x[0])
            if dt.weekday()==weekday and dt.hour==hour and dt.minute==0:out.append(im[x[0]])
    return out


def enrich(rows,recs):
    out=[]
    for r in recs:
        q=dict(r); s=dict(r['state']) if r.get('state') else None
        if s:
            s.update(preentry_features(rows,r['i']))
            q['state']=s
        out.append(q)
    return out


def hinge(recs):
    return [r for r in recs if r.get('state') is not None and r.get('protect') is not None]


def split_records(recs):
    n=int(len(recs)*.60)
    return recs[:n],recs[n:]


def feature_atlas(recs,features):
    z=hinge(recs); p=[r for r in z if r['protect']>r['base']]; rr=[r for r in z if r['base']>=r['protect']]
    out={}
    for f in features:
        pv=[r['state'].get(f) for r in p]; rv=[r['state'].get(f) for r in rr]
        out[f]={'protect_med':med(pv),'runner_med':med(rv),'auc_hi_protect':auc_pairwise(pv,rv),
                'n_protect':sum(x is not None for x in pv),'n_runner':sum(x is not None for x in rv)}
    return out


def apply_feature(recs,feature,op,thr):
    pnl=base=0.0; actions=correct=wrong=0
    for r in recs:
        base+=r['base']; final=r['base']; s=r.get('state')
        if s is not None and r.get('protect') is not None:
            v=s.get(feature)
            fire=v is not None and ((v<=thr) if op=='LE' else (v>=thr))
            if fire:
                final=r['protect']; actions+=1
                if r['protect']>r['base']:correct+=1
                else:wrong+=1
        pnl+=final
    return {'pnl':rnd(pnl,3),'base_pnl':rnd(base,3),'delta':rnd(pnl-base,3),
            'actions':actions,'protect_better_actions':correct,'runner_better_actions':wrong}


def select_feature_threshold(disc,feature):
    vals=[r['state'].get(feature) for r in hinge(disc) if r['state'].get(feature) is not None]
    if len(vals)<8:return None
    candidates=[]
    for q in (0.20,0.30,0.40,0.50,0.60,0.70,0.80):
        th=quantile(vals,q)
        for op in ('LE','GE'):
            e=apply_feature(disc,feature,op,th)
            if e['actions']>=3:
                candidates.append((e['delta'],e['protect_better_actions']-e['runner_better_actions'],e['actions'],op,th,e))
    if not candidates:return None
    candidates.sort(key=lambda x:(x[0],x[1],-x[2]),reverse=True)
    _,_,_,op,th,e=candidates[0]
    return {'feature':feature,'op':op,'threshold':rnd(th,6),'discovery':e}


def transfer_table(disc,val,full,features):
    out=[]
    for f in features:
        s=select_feature_threshold(disc,f)
        if not s:continue
        s['validation']=apply_feature(val,f,s['op'],s['threshold'])
        s['full']=apply_feature(full,f,s['op'],s['threshold'])
        out.append(s)
    out.sort(key=lambda x:(min(x['discovery']['delta'],x['validation']['delta']),x['full']['delta']),reverse=True)
    return out


def block_atlas(recs):
    z=hinge(recs); out=[]
    for b in range(8):
        q=[r for r in z if min(7,max(0,int((r['ts']-EVAL_START)*8/(EVAL_END-EVAL_START))))==b]
        if not q:
            out.append({'block':b+1,'n':0});continue
        pb=sum(r['protect']>r['base'] for r in q)
        delta=sum(r['protect']-r['base'] for r in q)
        out.append({'block':b+1,'n':len(q),'protect_better':pb,'protect_share':rnd(pb/len(q),3),
                    'protect_all_delta':rnd(delta,3)})
    return out


def stability(d_atlas,v_atlas,features):
    rows=[]
    for f in features:
        da=d_atlas[f]['auc_hi_protect']; va=v_atlas[f]['auc_hi_protect']
        if da is None or va is None:continue
        ds=1 if da>=.5 else -1; vs=1 if va>=.5 else -1
        rows.append({'feature':f,'disc_auc':da,'val_auc':va,'same_direction':ds==vs,
                     'disc_strength':rnd(abs(da-.5),4),'val_strength':rnd(abs(va-.5),4),
                     'min_strength':rnd(min(abs(da-.5),abs(va-.5)),4)})
    rows.sort(key=lambda x:(x['same_direction'],x['min_strength']),reverse=True)
    return rows


def analyze_market(name,recs):
    disc,val=split_records(recs)
    dl=feature_atlas(disc,LOCAL); vl=feature_atlas(val,LOCAL); fl=feature_atlas(recs,LOCAL)
    dr=feature_atlas(disc,REGIME); vr=feature_atlas(val,REGIME); fr=feature_atlas(recs,REGIME)
    lt=transfer_table(disc,val,recs,LOCAL); rt=transfer_table(disc,val,recs,REGIME)
    return {
      'name':name,'entries':len(recs),'discovery_entries':len(disc),'validation_entries':len(val),
      'hinges':{'discovery':len(hinge(disc)),'validation':len(hinge(val)),'full':len(hinge(recs))},
      'protect_share':{
        'discovery':rnd(sum(r['protect']>r['base'] for r in hinge(disc))/max(1,len(hinge(disc))),3),
        'validation':rnd(sum(r['protect']>r['base'] for r in hinge(val))/max(1,len(hinge(val))),3),
        'full':rnd(sum(r['protect']>r['base'] for r in hinge(recs))/max(1,len(hinge(recs))),3)},
      'local_stability':stability(dl,vl,LOCAL),
      'regime_stability':stability(dr,vr,REGIME),
      'local_transfer':lt,
      'regime_transfer':rt,
      'local_full_atlas':fl,'regime_full_atlas':fr,
      'blocks':block_atlas(recs)
    }


def concise_transfer(rows):
    return [x for x in rows if x['discovery']['delta']>0 and x['validation']['delta']>0][:12]


def main():
    rows=load()
    ti=make_indices(rows,1,6); fi=make_indices(rows,4,15)
    tr=enrich(rows,T.build(rows,ti)); fr=enrich(rows,F.build(rows,fi))
    ta=analyze_market('TUESDAY06_SELL_CONTROL',tr)
    fa=analyze_market('FRIDAY15_BUY_TARGET',fr)
    out={
      'status':'FRIDAY_TMETHOD_F53_SEPARABILITY_ATTRIBUTION',
      'design':'single-feature discovery threshold frozen into validation; all scheduled entries retained',
      'tuesday':ta,'friday':fa,
      'cross_positive':{
        'tuesday_local':concise_transfer(ta['local_transfer']),
        'tuesday_regime':concise_transfer(ta['regime_transfer']),
        'friday_local':concise_transfer(fa['local_transfer']),
        'friday_regime':concise_transfer(fa['regime_transfer'])
      }
    }
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)

if __name__=='__main__':main()
