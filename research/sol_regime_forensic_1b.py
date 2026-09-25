"""SOL regime forensic Stage 1B: deterministic synthetic tests.

This file intentionally reproduces the legacy V4H regime implementation before
we change it. It tests timing, partial 4H aggregation, cold-start sensitivity,
and stale swing-state behavior without touching production code.
"""
import numpy as np

BLOCK = 4 * 3600 * 1000

def ema(c,p):
    c=np.asarray(c,dtype=float); e=np.zeros(len(c)); e[0]=c[0]; k=2.0/(p+1)
    for i in range(1,len(c)): e[i]=c[i]*k+e[i-1]*(1-k)
    return e

def atr(H,L,C,p=14):
    n=len(H); a=np.zeros(n)
    for i in range(1,n):
        t=max(H[i]-L[i],abs(H[i]-C[i-1]),abs(L[i]-C[i-1]))
        a[i]=a[i-1]+(t-a[i-1])/min(i,p)
    return a

def build_4h_legacy(rows):
    cs=[]; buf=[]
    for r in rows:
        if buf and (r[0]//BLOCK)!=(buf[0][0]//BLOCK):
            cs.append((buf[0][0],buf[0][1],max(x[2] for x in buf),min(x[3] for x in buf),buf[-1][4],sum(x[5] for x in buf),buf[-1][0],len(buf)))
            buf=[]
        buf.append(r)
    if len(buf)==4:
        cs.append((buf[0][0],buf[0][1],max(x[2] for x in buf),min(x[3] for x in buf),buf[-1][4],sum(x[5] for x in buf),buf[-1][0],len(buf)))
    return cs

def build_4h_strict(rows):
    groups={}
    for r in rows: groups.setdefault(r[0]//BLOCK,[]).append(r)
    out=[]
    for _,b in sorted(groups.items()):
        if len(b)!=4: continue
        b=sorted(b,key=lambda x:x[0])
        if any(b[j][0]-b[j-1][0]!=3600000 for j in range(1,4)): continue
        out.append((b[0][0],b[0][1],max(x[2] for x in b),min(x[3] for x in b),b[-1][4],sum(x[5] for x in b),b[-1][0],4))
    return out

class SwingRegime:
    def __init__(self,slb=5,sa=0.5):
        self.slb=slb; self.sa=sa; self.hh=self.hl=self.lh=self.ll=0
        self.lsh=self.lsl=self.psh=self.psl=None
    def process(self,i,H,L,C,ef,es,A):
        if i<self.slb:return "SIDEWAYS"
        mid=i-self.slb//2
        wh=H[max(0,i-self.slb):i+1]; wl=L[max(0,i-self.slb):i+1]
        am=self.sa*A[i] if A[i]>0 else 0
        if H[mid]==max(wh) and (self.lsh is None or abs(H[mid]-self.lsh)>=am):
            self.psh=self.lsh; self.lsh=float(H[mid])
            if self.psh:
                if self.lsh>self.psh:self.hh+=1
                else:self.lh+=1; self.hh=max(0,self.hh-1)
        if L[mid]==min(wl) and (self.lsl is None or abs(L[mid]-self.lsl)>=am):
            self.psl=self.lsl; self.lsl=float(L[mid])
            if self.psl:
                if self.lsl>self.psl:self.hl+=1; self.ll=max(0,self.ll-1)
                else:self.ll+=1; self.hl=max(0,self.hl-1)
        if self.hh>=2 and self.hl>=2 and ef[i]>es[i] and C[i]>es[i]:return "BULL"
        if self.lh>=2 and self.ll>=2 and ef[i]<es[i] and C[i]<es[i]:return "BEAR"
        return "SIDEWAYS"

def regimes(C,mode):
    C=np.asarray(C,float); ef=ema(C,7); es=ema(C,20)
    if mode=="ema_cross": return np.where(ef>es,"BULL",np.where(ef<es,"BEAR","SIDEWAYS")).tolist()
    if mode=="ema_simple": return np.where((C>ef)&(C>es),"BULL",np.where((C<ef)&(C<es),"BEAR","SIDEWAYS")).tolist()
    if mode=="dual": return np.where((ef>es)&(C>ef)&(C>es),"BULL",np.where((ef<es)&(C<ef)&(C<es),"BEAR","SIDEWAYS")).tolist()
    H=C+0.4; L=C-0.4; A=atr(H,L,C); d=SwingRegime()
    return [d.process(i,H,L,C,ef,es,A) for i in range(len(C))]

def rows_1h(n=48,start_hour=0):
    out=[]
    for i in range(n):
        t=(start_hour+i)*3600000; o=100+i*.1; c=o+.05
        out.append((t,o,max(o,c)+.1,min(o,c)-.1,c,1.0))
    return out

def first_after(seq,label,start):
    return next((i-start for i in range(start,len(seq)) if seq[i]==label),None)

def run():
    report={}
    up=np.linspace(100,140,80); down=np.linspace(140,100,80); flat=np.full(80,120.)
    for mode in ["ema_cross","ema_simple","dual","swing"]:
        report[mode+"_mono"]={
            "up_tail":regimes(up,mode)[-10:],
            "down_tail":regimes(down,mode)[-10:],
            "flat_tail":regimes(flat,mode)[-10:],
        }
        x=np.r_[up,down]; r=regimes(x,mode)
        report[mode+"_bull_to_bear_delay_4h"]=first_after(r,"BEAR",len(up))

    base=rows_1h()
    # Start at 01:00 UTC: legacy emits first 3-hour partial block as valid 4H.
    shifted=rows_1h(47,1)
    missing=[r for j,r in enumerate(base) if j!=10]
    report["aggregation"]={
        "aligned_legacy_sizes":[x[-1] for x in build_4h_legacy(base)],
        "shifted_legacy_sizes":[x[-1] for x in build_4h_legacy(shifted)],
        "shifted_strict_sizes":[x[-1] for x in build_4h_strict(shifted)],
        "missing_legacy_sizes":[x[-1] for x in build_4h_legacy(missing)],
        "missing_strict_sizes":[x[-1] for x in build_4h_strict(missing)],
    }

    # Same physical tail, different query start: quantify cold-start disagreement.
    long=np.r_[np.linspace(80,120,60),np.linspace(120,95,25),np.linspace(95,130,60)]
    for mode in ["ema_cross","ema_simple","dual"]:
        full=regimes(long,mode)
        cut=regimes(long[40:],mode)
        aligned=full[40:]
        report[mode+"_cold_start_disagreement_first40"]=sum(a!=b for a,b in zip(aligned[:40],cut[:40]))

    # Assertions define non-negotiable expected mechanics.
    assert all(x==4 for x in report["aggregation"]["aligned_legacy_sizes"])
    assert report["aggregation"]["shifted_legacy_sizes"][0] == 3
    assert 3 in report["aggregation"]["missing_legacy_sizes"]
    assert all(x==4 for x in report["aggregation"]["shifted_strict_sizes"])
    assert all(x==4 for x in report["aggregation"]["missing_strict_sizes"])
    return report

if __name__=="__main__":
    import json
    print(json.dumps(run(),indent=2))
