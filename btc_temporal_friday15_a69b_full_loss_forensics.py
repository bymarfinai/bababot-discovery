"""BTC Friday15 A6.9b — FULL 138-trade loss forensics.

No Friday pullback selector. Analyze the original Friday15 BUY parent across all 138 occurrences:
- exact Friday 15:00 WIB BUY
- TP 2.0%, SL 0.7%, max hold 360m
- 0.15% roundtrip fee, $500 notional
- adverse-first if TP/SL same 5m bar

Goal: explain all executable losses before any filtering.
"""
import json, statistics
import btc_temporal_friday15_a60_money_geometry as a60
import btc_temporal_saturday18_a74_loss_forensics as a74
import btc_temporal_saturday18_a724_preentry_wrongway_atlas as a724
from btc_temporal_a34_5m_events import load, ldt, rnd, TF, EVAL_START, EVAL_END

TP=2.0; SL=.7; HOLD=360; FEE=.15
CHECKS=(15,30,60,120,240,360)


def mean(xs): return statistics.mean(xs) if xs else 0.0
def med(xs): return rnd(statistics.median(xs),4) if xs else None

def path_stats(rows,i,e):
    end=i+HOLD//5
    if end>=len(rows) or rows[end][0]!=rows[i][0]+(HOLD//5)*TF:return None
    q=rows[i:end]
    mfe=max(100*(x[2]-e)/e for x in q); mae=max(100*(e-x[3])/e for x in q)
    ups=(.3,.5,.8,1.0,1.5,2.0); dns=(.3,.5,.7)
    fu={str(z):None for z in ups}; fd={str(z):None for z in dns}
    peak=-1e9; pk=0; trough=1e9; tk=0
    for k,x in enumerate(q):
        hi=100*(x[2]-e)/e; lo=100*(x[3]-e)/e
        if hi>peak: peak=hi;pk=k
        if lo<trough: trough=lo;tk=k
        for z in ups:
            if fu[str(z)] is None and hi>=z:fu[str(z)]=k*5
        for z in dns:
            if fd[str(z)] is None and lo<=-z:fd[str(z)]=k*5
    return {'mfe':mfe,'mae':mae,'peak_min':pk*5,'trough_min':tk*5,'first_up':fu,'first_dn':fd,'close360':100*(q[-1][4]-e)/e}

def label(r):
    if r['trade']['net_usd']>0:return 'WIN'
    m=r['path']['mfe']
    if m<.3:return 'A_WRONG_WAY_LT_03'
    if m<.5:return 'B_WEAK_POP_03_05'
    if m<1.0:return 'C_GIVEBACK_05_10'
    return 'D_DEEP_GIVEBACK_GE_10'

def checkpoint(rows,r,e7,e20,h):
    i=r['i'];j=i+h//5
    if j>=len(rows) or rows[j][0]!=rows[i][0]+(h//5)*TF:return None
    e=r['entry'];op=rows[j][1];done=rows[i:j]
    if not done:return None
    last=j-1; prev=max(0,last-3)
    return {'progress':100*(op-e)/e,
      'mfe':max(100*(x[2]-e)/e for x in done),'mae':max(100*(e-x[3])/e for x in done),
      'taker':mean([(x[9]/x[6] if x[6] else .5) for x in done])-.5,
      'd7':100*(op-e7[last])/e7[last],'d20':100*(op-e20[last])/e20[last],
      's7_15':100*(e7[last]-e7[prev])/e7[prev] if e7[prev] else 0,
      's20_15':100*(e20[last]-e20[prev])/e20[prev] if e20[prev] else 0}

def recover_after_sl(rows,r):
    if r['trade']['reason'] not in ('SL','AMB_SL'):return None
    start=r['i']+r['trade']['bars']; end=r['i']+HOLD//5; e=r['entry'];q=rows[start:end]
    if not q:return None
    mfe=max(100*(x[2]-e)/e for x in q)
    return {'mfe_after_sl':rnd(mfe,4),'netpos':mfe>=FEE,'ge05':mfe>=.5,'ge10':mfe>=1.0,'ge20':mfe>=2.0}

def pack(q):
    labs=('WIN','A_WRONG_WAY_LT_03','B_WEAK_POP_03_05','C_GIVEBACK_05_10','D_DEEP_GIVEBACK_GE_10')
    out={}
    for lab in labs:
        z=[r for r in q if r['label']==lab];d={'n':len(z)}
        if z:
            d.update({'mfe_med':med([r['path']['mfe'] for r in z]),'mae_med':med([r['path']['mae'] for r in z]),'peak_min_med':med([r['path']['peak_min'] for r in z]),
              'pre1_med':med([r['prex']['pre1'] for r in z]),'pre4_med':med([r['prex']['pre4'] for r in z]),'d20_entry_med':med([r['prex']['d20'] for r in z]),'s20_entry_med':med([r['prex']['s20_15'] for r in z])})
            for h in CHECKS:
                zz=[r['checks'][str(h)] for r in z if r['checks'][str(h)]]
                for f in ('progress','mfe','mae','taker','d7','d20','s7_15','s20_15'):
                    d[f'{h}_{f}_med']=med([x[f] for x in zz])
        out[lab]=d
    return out

def counts(q):
    return {lab:sum(r['label']==lab for r in q) for lab in ('WIN','A_WRONG_WAY_LT_03','B_WEAK_POP_03_05','C_GIVEBACK_05_10','D_DEEP_GIVEBACK_GE_10')}

def recovery(q):
    z=[r for r in q if r.get('recovery')]
    return {'sl_losses':len(z),'recover_netpositive':sum(r['recovery']['netpos'] for r in z),'recover_05':sum(r['recovery']['ge05'] for r in z),'recover_10':sum(r['recovery']['ge10'] for r in z),'recover_tp2':sum(r['recovery']['ge20'] for r in z),'mfe_after_sl_med':med([r['recovery']['mfe_after_sl'] for r in z])}

def main():
    rows=load();im={x[0]:i for i,x in enumerate(rows)};e7=a74.ema_series(rows,7);e20=a74.ema_series(rows,20);rec=[]
    for x in rows:
        if not(EVAL_START<=x[0]<EVAL_END):continue
        d=ldt(x[0])
        if not(d.weekday()==4 and d.hour==15 and d.minute==0):continue
        i=im[x[0]];px=a724.pre_features(rows,i,e7,e20);t=a60.trade(rows,i,TP,SL,HOLD);p=path_stats(rows,i,x[1])
        if px is None or t is None or p is None:continue
        r={'i':i,'ts':x[0],'entry':x[1],'prex':px,'trade':t,'path':p};r['label']=label(r)
        r['checks']={str(h):checkpoint(rows,r,e7,e20,h) for h in CHECKS};r['recovery']=recover_after_sl(rows,r);rec.append(r)
    disc=rec[:82];val=rec[82:];loss=[r for r in rec if r['label']!='WIN']
    out={'status':'FRIDAY15_A69B_FULL_LOSS_FORENSICS','n':len(rec),'wins':sum(r['label']=='WIN' for r in rec),'losses':len(loss),
      'counts':{'full':counts(rec),'discovery':counts(disc),'validation':counts(val)},
      'exit_reasons_full':{z:sum(r['trade']['reason']==z for r in rec) for z in ('TP','SL','AMB_SL','TIMEOUT')},
      'loss_exit_reasons':{z:sum(r['trade']['reason']==z for r in loss) for z in ('SL','AMB_SL','TIMEOUT')},
      'loss_capacity':{'mfe_ge_03':sum(r['path']['mfe']>=.3 for r in loss),'mfe_ge_05':sum(r['path']['mfe']>=.5 for r in loss),'mfe_ge_08':sum(r['path']['mfe']>=.8 for r in loss),'mfe_ge_10':sum(r['path']['mfe']>=1.0 for r in loss),'mfe_ge_15':sum(r['path']['mfe']>=1.5 for r in loss)},
      'recovery_after_sl':{'full':recovery(rec),'discovery':recovery(disc),'validation':recovery(val)},
      'atlas':{'full':pack(rec),'discovery':pack(disc),'validation':pack(val)},
      'loss_cases':[{'ts':r['ts'],'label':r['label'],'reason':r['trade']['reason'],'net':rnd(r['trade']['net_usd'],3),'mfe':rnd(r['path']['mfe'],4),'mae':rnd(r['path']['mae'],4),'peak_min':r['path']['peak_min'],'first_up':r['path']['first_up'],'first_dn':r['path']['first_dn'],'recovery':r['recovery']} for r in loss]}
    print('RESULT_JSON',json.dumps(out,separators=(',',':')),flush=True)
if __name__=='__main__':main()
