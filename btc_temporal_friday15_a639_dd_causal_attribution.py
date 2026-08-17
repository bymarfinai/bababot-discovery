"""A6.39 Friday15 max-DD causal attribution.
Diagnostics only. No strategy changes.
Compare A6.33 max-DD descent against non-DD history and parent counterfactual.
"""
import json, statistics
import btc_temporal_friday15_a636_maxdd_forensics as a636
import btc_temporal_friday15_a60_money_geometry as a60
from btc_temporal_a34_5m_events import ldt, rnd


def econ(vals):
    n=len(vals); pos=sum(x for x in vals if x>0); neg=-sum(x for x in vals if x<0)
    return {'n':n,'wr':rnd(100*sum(x>0 for x in vals)/n,2) if n else None,
            'pnl':rnd(sum(vals),3),'avg':rnd(sum(vals)/n,4) if n else None,
            'avg_win':rnd(statistics.mean([x for x in vals if x>0]),4) if any(x>0 for x in vals) else None,
            'avg_loss':rnd(statistics.mean([x for x in vals if x<=0]),4) if any(x<=0 for x in vals) else None,
            'pf':rnd(pos/neg,3) if neg else None,'mdd':rnd(a60.max_dd(vals),3)}

def label_group(r):
    s=r['label']
    if s.startswith('A_'): return 'A_WRONGWAY'
    if s.startswith('B_'): return 'B_WEAK_POP'
    if s.startswith('C_'): return 'C_GIVEBACK'
    if s.startswith('D_'): return 'D_DEEP_GIVEBACK'
    return 'WIN'

def pack(q):
    labels={}
    layers={}
    for r in q:
        labels.setdefault(label_group(r),[]).append(r)
        layers.setdefault(r['layer'],[]).append(r)
    def gstats(d):
        out={}
        for k,v in d.items():
            out[k]={'n':len(v),'rate':rnd(100*len(v)/len(q),2),
                    'managed_pnl':rnd(sum(r['chosen'] for r in v),3),
                    'parent_pnl':rnd(sum(r['base'] for r in v),3),
                    'mgmt_delta':rnd(sum(r['chosen']-r['base'] for r in v),3),
                    'mfe_med':rnd(statistics.median(r['path']['mfe'] for r in v),3),
                    'mae_med':rnd(statistics.median(r['path']['mae'] for r in v),3)}
        return out
    return {'managed':econ([r['chosen'] for r in q]),'parent':econ([r['base'] for r in q]),
            'management_delta':rnd(sum(r['chosen']-r['base'] for r in q),3),
            'label_mix':gstats(labels),'layer_mix':gstats(layers),
            'mfe_med':rnd(statistics.median(r['path']['mfe'] for r in q),3),
            'mae_med':rnd(statistics.median(r['path']['mae'] for r in q),3)}

def main():
    _,rec=a636.build(); eps=a636.episodes(rec); e=eps[0]
    start=e['peak_i']+1; end=e['trough_i']+1
    dd=rec[start:end]; pre=rec[:start]; post=rec[end:]
    # split DD into two halves to see deterioration path
    mid=len(dd)//2
    dd1=dd[:mid]; dd2=dd[mid:]
    # parent SL vs timeout and management incidence
    def exits(q):
        z={}
        for r in q:z[r['trade']['reason']]=z.get(r['trade']['reason'],0)+1
        return z
    out={'status':'FRIDAY15_A639_DD_CAUSAL_ATTRIBUTION',
         'episode':{'start':str(ldt(dd[0]['ts']).date()),'end':str(ldt(dd[-1]['ts']).date()),'n':len(dd),
                    'peak_date':str(ldt(rec[e['peak_i']]['ts']).date()),'max_dd':rnd(e['max_dd'],3)},
         'pre_dd':pack(pre),'dd_full':pack(dd),'dd_first_half':pack(dd1),'dd_second_half':pack(dd2),'post_trough':pack(post),
         'parent_exit_reasons':{'pre':exits(pre),'dd':exits(dd),'post':exits(post)},
         'notes':'Diagnostics only; label/layer mix and parent-vs-managed attribution. No thresholds selected.'}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
