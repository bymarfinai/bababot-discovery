"""Friday T-Method F5.4 — high-confidence local + pre-entry regime conjunction.

F5.3 found an important distinction:
- Friday HAS stable ranking information (local range/volume expansion and several
  pre-entry regime features),
- but no single feature converts that ranking into positive economics across both
  chronological halves, because false-positive PROTECT actions can clip large runners.

F5.4 therefore tests only a compact, predeclared architecture:
1) local expansion must be high (range_ratio OR volume_ratio family), AND
2) a broader pre-entry regime feature must also be high.
Optional strict family requires BOTH local range and local volume high plus regime high.

No new entry filter. All Friday15 entries remain. Management action is still the
frozen F5.2 +0.20% protection after the causal +0.50% hinge. Thresholds are chosen
from discovery quantiles only; validation is report-only for each configuration.

IMPORTANT: architecture was motivated by F5.3, whose validation was already visible,
so this is exploratory/provisional, not fresh OOS proof.
"""
import json
import btc_temporal_friday15_f52_runner_protect as F
import btc_temporal_friday15_f53_separability_attribution as A
from btc_temporal_a34_5m_events import load, rnd, EVAL_START, EVAL_END

LOCAL=('range_ratio','volume_ratio')
REGIME=('pre_taker240','pre_eff240','pre_ret15','pre4')
QS=(0.50,0.60,0.70,0.80)


def eval_cfg(recs,cfg):
    base=pnl=0.0; actions=tp=fp=0; gain=harm=0.0
    for r in recs:
        base+=r['base']; final=r['base']; s=r.get('state')
        if s is not None and r.get('protect') is not None:
            ok=True
            for f,th in cfg['conds']:
                v=s.get(f)
                if v is None or v < th: ok=False; break
            if ok:
                actions+=1; final=r['protect']; d=r['protect']-r['base']
                if d>0: tp+=1; gain+=d
                else: fp+=1; harm+=-d
        pnl+=final
    return {'pnl':rnd(pnl,3),'base_pnl':rnd(base,3),'delta':rnd(pnl-base,3),'actions':actions,
            'protect_better_actions':tp,'runner_better_actions':fp,
            'action_precision':rnd(tp/actions,3) if actions else None,
            'true_gain_usd':rnd(gain,3),'false_damage_usd':rnd(harm,3),
            'gain_damage_ratio':rnd(gain/harm,3) if harm else None}


def threshold_map(disc):
    hz=A.hinge(disc); out={}
    for f in LOCAL+REGIME:
        vals=[r['state'].get(f) for r in hz if r['state'].get(f) is not None]
        out[f]={q:A.quantile(vals,q) for q in QS}
    return out


def build_cfgs(th):
    out=[]
    for l in LOCAL:
      for rg in REGIME:
       for ql in QS:
        for qr in QS:
          out.append({'family':l.upper()+'_AND_'+rg.upper(),'qs':[ql,qr],
                      'conds':[(l,th[l][ql]),(rg,th[rg][qr])]})
    # stricter architecture: both local expansion dimensions + one regime dimension.
    for rg in REGIME:
      for qrange in QS:
       for qvol in QS:
        for qr in QS:
          out.append({'family':'RANGE_VOLUME_AND_'+rg.upper(),'qs':[qrange,qvol,qr],
                      'conds':[('range_ratio',th['range_ratio'][qrange]),
                               ('volume_ratio',th['volume_ratio'][qvol]),
                               (rg,th[rg][qr])]})
    return out


def block_delta(recs,cfg):
    out=[]
    for b in range(8):
        q=[r for r in recs if min(7,max(0,int((r['ts']-EVAL_START)*8/(EVAL_END-EVAL_START))))==b]
        e=eval_cfg(q,cfg) if q else {'delta':0,'actions':0}
        out.append({'block':b+1,'delta':e['delta'],'actions':e['actions']})
    return out


def compact_cfg(cfg):
    return {'family':cfg['family'],'qs':cfg['qs'],
            'conds':[[f,rnd(th,6)] for f,th in cfg['conds']]}


def main():
    rows=load(); fi=A.make_indices(rows,4,15)
    recs=A.enrich(rows,F.build(rows,fi)); disc,val=A.split_records(recs)
    th=threshold_map(disc); tested=[]
    for cfg in build_cfgs(th):
        d=eval_cfg(disc,cfg)
        if d['actions']<3: continue
        v=eval_cfg(val,cfg); full=eval_cfg(recs,cfg)
        tested.append({'cfg':compact_cfg(cfg),'discovery':d,'validation':v,'full':full,
                       '_cfg':cfg})
    # discovery economics first, then precision, then fewer actions.
    tested.sort(key=lambda x:(x['discovery']['delta'],x['discovery']['action_precision'] or 0,-x['discovery']['actions']),reverse=True)
    top=[]
    for x in tested[:25]:
        y={k:v for k,v in x.items() if k!='_cfg'}
        y['blocks']=block_delta(recs,x['_cfg']); top.append(y)
    cross=[]
    for x in tested:
        if x['discovery']['delta']>0 and x['validation']['delta']>0:
            y={k:v for k,v in x.items() if k!='_cfg'}
            y['blocks']=block_delta(recs,x['_cfg']); cross.append(y)
    cross.sort(key=lambda x:(x['full']['delta'],x['validation']['delta'],x['full']['action_precision'] or 0),reverse=True)
    # Require positive delta and no chronological half failure; report a stricter robustness subset.
    robust=[]
    for x in cross:
        pos=sum(b['delta']>0 for b in x['blocks']); neg=sum(b['delta']<0 for b in x['blocks'])
        if pos>=3 and neg<=3: robust.append(x)
    out={'status':'FRIDAY_TMETHOD_F54_HIGHCONFIDENCE_CONJUNCTION',
         'data':{'entries':len(recs),'discovery':len(disc),'validation':len(val),'tested':len(tested)},
         'threshold_quantiles':{f:{str(q):rnd(v,6) for q,v in z.items()} for f,z in th.items()},
         'discovery_selected':top,'strict_cross_positive':cross[:20],'block_robust_subset':robust[:20],
         'notes':'Exploratory architecture informed by F5.3; not fresh OOS and not live.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)

if __name__=='__main__':main()
