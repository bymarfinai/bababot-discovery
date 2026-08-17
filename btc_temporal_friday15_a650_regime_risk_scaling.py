"""BTC Friday15 A6.50 — causal regime risk scaling.

Keep A6.33 direction and management unchanged on every Friday. Keep all 138
occurrences traded. If the frozen A6.48 shadow detector is DEFENSIVE before the
entry AND current pre-entry state is stress_unwind, use 50% notional for that
Friday occurrence. Otherwise use normal notional.

50% is a predeclared natural half-risk action, not a parameter sweep.
This tests whether the useful conclusion from A6.49 is risk reduction rather
than a directional SHORT edge.
"""
import json
import btc_temporal_friday15_a649_regime_direction_switch as a649
import btc_temporal_friday15_a636_maxdd_forensics as a636
from btc_temporal_a34_5m_events import rnd

SCALE=.50

def econ(p):
    n=len(p);pos=sum(x for x in p if x>0);neg=-sum(x for x in p if x<0)
    return {'n':n,'wr':rnd(100*sum(x>0 for x in p)/n,2),'pnl':rnd(sum(p),3),'avg':rnd(sum(p)/n,4),
            'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(a636.a60.max_dd(p),3),'ls':a636.a60.loss_streak(p)}

def main():
    rows,u=a649.build()
    for r in u:
        r['basep']=r['chosen']
        r['scaledp']=r['chosen']*SCALE if r['switch'] else r['chosen']
    sw=[r for r in u if r['switch']]
    out={'status':'FRIDAY15_A650_REGIME_RISK_SCALING','scale_on_switch':SCALE,'switch_n':len(sw),
         'base':econ([r['basep'] for r in u]),'scaled':econ([r['scaledp'] for r in u]),
         'delta_pnl':rnd(sum(r['scaledp']-r['basep'] for r in u),3),
         'discovery':{'base':econ([r['basep'] for r in u[:82]]),'scaled':econ([r['scaledp'] for r in u[:82]])},
         'validation':{'base':econ([r['basep'] for r in u[82:]]),'scaled':econ([r['scaledp'] for r in u[82:]])},
         'by_period':{},
         'switch_cases':[{'date':r['date'],'grp':r['grp'],'base':rnd(r['basep'],3),'scaled':rnd(r['scaledp'],3),'delta':rnd(r['scaledp']-r['basep'],3)} for r in sw],
         'notes':'All Friday entries retained; direction and A6.33 management unchanged. Only notional is halved in causal DEFENSIVE+stress_unwind state. No size sweep.'}
    for g in ('PRE_DD','DD','POST'):
        q=[r for r in u if r['grp']==g];s=[r for r in q if r['switch']]
        out['by_period'][g]={'switch_n':len(s),'base':econ([r['basep'] for r in q]),'scaled':econ([r['scaledp'] for r in q]),
                             'switch_base':econ([r['basep'] for r in s]) if s else None,
                             'switch_scaled':econ([r['scaledp'] for r in s]) if s else None}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
