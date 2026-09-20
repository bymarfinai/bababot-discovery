#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import bnb_b31_s1_swing_structure_library as b31

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B37_S1_H4_DEMAND_H1_TWIN"
DISC_START=pd.Timestamp("2022-01-01T00:00:00Z")
DISC_END=pd.Timestamp("2024-12-31T23:59:59Z")
BAR5=pd.Timedelta(minutes=5)
BAR1H=pd.Timedelta(hours=1)
BAR4H=pd.Timedelta(hours=4)

def exact_bars(raw, freq, n5):
    z=raw.reset_index().rename(columns={"ts":"close_ts"})
    z["bucket"]=z["close_ts"].dt.ceil(freq)
    g=z.groupby("bucket",sort=True)
    out=g.agg(open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last"),
              n=("close","size"),first_ts=("close_ts","first"),last_ts=("close_ts","last")).reset_index()
    need=pd.Timedelta(minutes=5*(n5-1))
    out=out[(out.n==n5)&((out.last_ts-out.first_ts)==need)].copy()
    return out.set_index("bucket")[["open","high","low","close"]].astype(float)

def pivots(b):
    hi=b.high.to_numpy(float); lo=b.low.to_numpy(float); idx=b.index
    hc={}; lc={}
    for i in range(2,len(b)-2):
        if hi[i] > max(hi[i-2],hi[i-1],hi[i+1],hi[i+2]):
            hc.setdefault(idx[i+2],[]).append((idx[i+2],idx[i],float(hi[i])))
        if lo[i] < min(lo[i-2],lo[i-1],lo[i+1],lo[i+2]):
            lc.setdefault(idx[i+2],[]).append((idx[i+2],idx[i],float(lo[i])))
    return hc,lc

def h4_demand_zones(b4):
    hc,_=pivots(b4)
    active=[]; used=set(); rows=[]; prev_close=None
    arr=b4.reset_index().rename(columns={"bucket":"ts"})
    # index map for origin search
    for i,(t,r) in enumerate(b4.iterrows()):
        latest=active[-1] if active else None
        if latest is not None and prev_close is not None:
            confirm_ts,pivot_ts,level=latest
            if pivot_ts not in used and prev_close <= level and float(r.close) > level:
                origin=None
                for j in range(i-1,max(-1,i-7),-1):
                    rr=b4.iloc[j]
                    if float(rr.close) < float(rr.open):
                        origin=(j,b4.index[j],rr)
                        break
                if origin is not None:
                    j,ots,orr=origin
                    zlow=float(orr.low); zhigh=float(orr.open)
                    if zhigh>zlow:
                        rows.append({
                            "zone_id":f"H4D_{t.isoformat()}",
                            "activation_ts":t,
                            "h4_bos_ts":t,
                            "broken_h4_swing_ts":pivot_ts,
                            "broken_h4_level":level,
                            "origin_ts":ots,
                            "demand_low":zlow,
                            "demand_high":zhigh,
                            "h4_bos_open":float(r.open),
                            "h4_bos_high":float(r.high),
                            "h4_bos_low":float(r.low),
                            "h4_bos_close":float(r.close),
                        })
                        used.add(pivot_ts)
        for x in hc.get(t,[]): active.append(x)
        prev_close=float(r.close)
    return pd.DataFrame(rows)

def h1_bos_events(b1):
    hc,_=pivots(b1)
    active=[]; rows=[]; prev_close=None
    for t,r in b1.iterrows():
        latest=active[-1] if active else None
        if latest is not None and prev_close is not None:
            confirm_ts,pivot_ts,level=latest
            if prev_close<=level and float(r.close)>level:
                rows.append({"bos_ts":t,"broken_h1_swing_ts":pivot_ts,"broken_h1_level":level,
                             "bos_close":float(r.close),"bos_high":float(r.high)})
        for x in hc.get(t,[]): active.append(x)
        prev_close=float(r.close)
    return pd.DataFrame(rows)

def confirmed_h1_highs(b1):
    hc,_=pivots(b1)
    rows=[]
    for cts,vals in hc.items():
        for confirm_ts,pivot_ts,level in vals:
            rows.append({"confirm_ts":confirm_ts,"pivot_ts":pivot_ts,"pivot_high":level})
    return pd.DataFrame(rows).sort_values("confirm_ts") if rows else pd.DataFrame(columns=["confirm_ts","pivot_ts","pivot_high"])

def overlap(r,zlow,zhigh):
    return float(r.low)<=zhigh and float(r.high)>=zlow

def scan_twins(b1,zones):
    bos=h1_bos_events(b1)
    highs=confirmed_h1_highs(b1)
    out=[]; checks=[]
    for z in zones.itertuples(index=False):
        if z.activation_ts>DISC_END or z.activation_ts<DISC_START-pd.Timedelta(days=30):
            continue
        after=b1[(b1.index>z.activation_ts)&(b1.index<=DISC_END)]
        if after.empty: continue

        touch_ts=None; touch=None
        for t,r in after.iterrows():
            if overlap(r,z.demand_low,z.demand_high):
                touch_ts=t; touch=r; break
        if touch_ts is None: continue

        qbos=bos[(bos.bos_ts>z.activation_ts)&(bos.bos_ts<touch_ts)]
        has_h1_bos=not qbos.empty
        chosen_bos=None
        new_high=None
        if has_h1_bos:
            # first causal H1 BOS after H4 activation; the structure must then print a confirmed new high before touch
            for br in qbos.itertuples(index=False):
                qh=highs[(highs.confirm_ts>br.bos_ts)&(highs.confirm_ts<touch_ts)&
                         (highs.pivot_high>br.broken_h1_level)]
                if not qh.empty:
                    chosen_bos=br
                    new_high=qh.iloc[0]
                    break
        has_new_high=new_high is not None

        enough_retrace=False; lower_high=False; lower_low=False
        if has_new_high:
            seg=b1[(b1.index>new_high.pivot_ts)&(b1.index<touch_ts)]
            enough_retrace=len(seg)>=2
            if len(seg)>=2:
                lower_high=bool((seg.high.diff()<0).any())
                lower_low=bool((seg.low.diff()<0).any())

        close_holds=float(touch.close)>=float(z.demand_low)
        exact=bool(has_h1_bos and has_new_high and enough_retrace and lower_high and lower_low and close_holds)

        rec={
            "zone_id":z.zone_id,
            "activation_ts":z.activation_ts,
            "origin_ts":z.origin_ts,
            "demand_low":z.demand_low,
            "demand_high":z.demand_high,
            "h4_bos_ts":z.h4_bos_ts,
            "broken_h4_swing_ts":z.broken_h4_swing_ts,
            "broken_h4_level":z.broken_h4_level,
            "first_touch_ts":touch_ts,
            "touch_open":float(touch.open),"touch_high":float(touch.high),
            "touch_low":float(touch.low),"touch_close":float(touch.close),
            "h1_bos_ts":pd.NaT if chosen_bos is None else chosen_bos.bos_ts,
            "broken_h1_swing_ts":pd.NaT if chosen_bos is None else chosen_bos.broken_h1_swing_ts,
            "broken_h1_level":np.nan if chosen_bos is None else chosen_bos.broken_h1_level,
            "new_high_pivot_ts":pd.NaT if new_high is None else new_high.pivot_ts,
            "new_high_confirm_ts":pd.NaT if new_high is None else new_high.confirm_ts,
            "new_high_price":np.nan if new_high is None else new_high.pivot_high,
            "has_h1_bos":has_h1_bos,
            "has_confirmed_new_high":has_new_high,
            "retrace_ge2_bars":enough_retrace,
            "has_lower_high":lower_high,
            "has_lower_low":lower_low,
            "retest_close_holds_demand":close_holds,
            "exact_structural_twin":exact,
        }
        checks.append(rec)
        if exact and DISC_START<=touch_ts<=DISC_END:
            out.append(rec)
    return pd.DataFrame(checks),pd.DataFrame(out)

def draw_one(b1,r,path):
    t0=r.origin_ts-pd.Timedelta(hours=16)
    t1=r.first_touch_ts+pd.Timedelta(hours=8)
    q=b1[(b1.index>=t0)&(b1.index<=t1)].copy()
    if q.empty:return
    fig,ax=plt.subplots(figsize=(14,6))
    xs=np.arange(len(q))
    width=.55
    for i,(_,c) in enumerate(q.iterrows()):
        up=float(c.close)>=float(c.open)
        col="#16a085" if up else "#e74c3c"
        ax.vlines(i,float(c.low),float(c.high),color=col,linewidth=1)
        y=min(float(c.open),float(c.close)); h=max(abs(float(c.close)-float(c.open)),1e-9)
        ax.add_patch(Rectangle((i-width/2,y),width,h,facecolor=col,edgecolor=col,linewidth=.8))
    def xpos(ts):
        if ts is None or pd.isna(ts):return None
        return int(np.argmin(np.abs((q.index-ts).asi8)))
    x0=xpos(r.origin_ts); x1=xpos(r.first_touch_ts)
    if x0 is None:x0=0
    if x1 is None:x1=len(q)-1
    ax.add_patch(Rectangle((x0-.5,float(r.demand_low)),max(1,x1-x0+1),
                           float(r.demand_high-r.demand_low),facecolor="#2ecc71",alpha=.16,edgecolor="#27ae60"))
    for ts,label in [(r.h1_bos_ts,"H1 BOS / IMPULSE"),(r.new_high_pivot_ts,"NEW HIGH"),(r.first_touch_ts,"H4 DEMAND RETEST")]:
        x=xpos(ts)
        if x is not None:
            ax.axvline(x,color="#34495e",alpha=.35,linewidth=1)
            ax.text(x,ax.get_ylim()[1] if ax.get_ylim()[1]>0 else float(q.high.max()),label,rotation=90,va="top",fontsize=8)
    step=max(1,len(q)//10)
    ax.set_xticks(xs[::step])
    ax.set_xticklabels([q.index[i].strftime("%Y-%m-%d\n%H:%M") for i in xs[::step]],fontsize=7)
    ax.set_title(f"BNB H1 structural twin — retest {r.first_touch_ts}")
    ax.set_ylabel("BNBUSDT")
    ax.grid(alpha=.12)
    fig.tight_layout()
    fig.savefig(path,dpi=160)
    plt.close(fig)

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995:raise RuntimeError(f"raw coverage low: {diag}")
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(f"identity mismatch: {ident}")

    b1=exact_bars(raw,"1h",12)
    b4=exact_bars(raw,"4h",48)
    zones=h4_demand_zones(b4)
    checks,twins=scan_twins(b1,zones)

    checks.to_csv(ROOT/f"{PFX}_Checklist.csv.gz",index=False,compression="gzip")
    twins.to_csv(ROOT/f"{PFX}_ExactTwins.csv",index=False)

    # chart up to six exact matches, spread chronologically rather than outcome-ranked
    chart_rows=[]
    if len(twins):
        take=np.unique(np.linspace(0,len(twins)-1,min(6,len(twins)),dtype=int))
        for k,ix in enumerate(take,1):
            r=twins.iloc[int(ix)]
            fn=f"{PFX}_Twin_{k}_{r.first_touch_ts.strftime('%Y%m%d_%H%M')}.png"
            draw_one(b1,r,ROOT/fn)
            chart_rows.append((k,fn,r.first_touch_ts))

    cnt={y:int((pd.to_datetime(twins.first_touch_ts,utc=True).dt.year==y).sum()) if len(twins) else 0 for y in [2022,2023,2024]}
    L=[
      "# BNB B37-S1 — H4 Demand / H1 Pullback Structural Twin Result","",
      "**Phase: STEP 1 — STRUCTURAL MAP ONLY**","",
      "No forward outcome, WR, TP/SL, PnL, indicator, derivative, or session filter was opened.","",
      "## Integrity",
      f"- Raw rows: **{diag['rows']:,}**; coverage **{diag['coverage']:.6%}**.",
      f"- A1 ret15 max diff: **{ident['max_ret15_diff']:.12g}**.",
      f"- A1 close-location max diff: **{ident['max_close_location_diff']:.12g}**.",
      f"- Exact H1 bars: **{len(b1):,}**; exact H4 bars: **{len(b4):,}**.","",
      "## Frozen structural twin",
      "H4 demand origin → H4 bullish BOS → H1 bullish BOS/impulse → confirmed H1 new high → corrective lower-high + lower-low sequence → first fresh H1 retest into H4 demand → retest close holds demand.","",
      f"## Exact matches",
      f"- Exact structural twins in 2022-2024: **{len(twins):,}**.",
      f"- 2022 / 2023 / 2024: **{cnt[2022]} / {cnt[2023]} / {cnt[2024]}**.",""
    ]
    if len(twins):
        L += ["| # | H4 demand origin | H4 BOS | H1 impulse/BOS | H1 new high | First H1 retest | Demand |",
              "|---:|---|---|---|---|---|---|"]
        for i,r in twins.head(20).iterrows():
            L.append(f"| {i+1} | {r.origin_ts} | {r.h4_bos_ts} | {r.h1_bos_ts} | {r.new_high_pivot_ts} | {r.first_touch_ts} | {r.demand_low:.4f}-{r.demand_high:.4f} |")
        L += ["","## Saved visual twins"]
        for k,fn,ts in chart_rows:L.append(f"- Twin {k}: `{fn}` — retest {ts}")
        L += ["","## Step-1 verdict","**EXACT STRUCTURAL TWIN FOUND.**",
              "The detector has at least one BNB occurrence with every supplied structural state present in the same causal order.",
              "Stop here. Winner/loser anatomy and outcome validation belong to later steps and were not run."]
        status="BNB_B37_S1_EXACT_STRUCTURAL_TWIN_FOUND"
    else:
        L += ["## Step-1 verdict","**NO EXACT STRUCTURAL TWIN FOUND under the frozen interpretation.**",
              "Per stop rule, no rescue filter or structural rewrite was applied."]
        status="BNB_B37_S1_NO_EXACT_STRUCTURAL_TWIN"

    (ROOT/f"{PFX}_Result.md").write_text("\n".join(L)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")
    print("\n".join(L),flush=True)

if __name__=="__main__":
    main()
