#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A17_PATH = Path(__file__).resolve().parent / "sol_long_multi_clock_expansion_a17.py"
A53_PATH = Path(__file__).resolve().parent / "sol_long_15utc_executable_guard_a53.py"

spec = importlib.util.spec_from_file_location("a17", A17_PATH)
a17 = importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(a17)
spec53 = importlib.util.spec_from_file_location("a53", A53_PATH)
a53 = importlib.util.module_from_spec(spec53); assert spec53.loader is not None; spec53.loader.exec_module(a53)

a4 = a17.a4; a3 = a4.a3; a2 = a17.a2

OUT_TRADES = ROOT / "SOL_LONG_15UTC_LOSS_CONFIRMATION_GUARD_A56_TRADES.csv"
OUT_METRICS = ROOT / "SOL_LONG_15UTC_LOSS_CONFIRMATION_GUARD_A56_METRICS.csv"
OUT_BLOCKS = ROOT / "SOL_LONG_15UTC_LOSS_CONFIRMATION_GUARD_A56_BLOCKS.csv"
OUT_ID = ROOT / "SOL_LONG_15UTC_LOSS_CONFIRMATION_GUARD_A56_IDENTITY.csv"
OUT_MD = ROOT / "SOL_LONG_15UTC_LOSS_CONFIRMATION_GUARD_A56_Result.md"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_LOSS_CONFIRMATION_GUARD_A56_Status.txt"

REF_MIN=360; HOUR=15; TARGET_R=0.40; NOTIONAL=500.0; STRESS=0.0005
BAR=pd.Timedelta(minutes=5); HORIZON=pd.Timedelta(minutes=720)
PARTS=("development","external","reference_validation")
EXPECTED_N={"development":601,"external":281,"reference_validation":337}
EXPECTED_WIN={"development":244,"external":115,"reference_validation":150}
EPS=1e-12


def fmt(v,d=2):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"

def pct(v): return "-" if pd.isna(v) else f"{100*float(v):.1f}%"

def pf(vals):
    x=pd.to_numeric(vals,errors="coerce").dropna(); gp=float(x[x>0].sum()); gl=float(-x[x<=0].sum())
    if gl==0: return np.inf if gp>0 else np.nan
    return gp/gl

def max_dd(vals):
    x=pd.to_numeric(vals,errors="coerce").fillna(0).to_numpy(float); eq=np.concatenate([[0.0],np.cumsum(x)]); pk=np.maximum.accumulate(eq)
    return float(np.max(pk-eq))

def max_loss_streak(vals):
    best=cur=0
    for v in pd.to_numeric(vals,errors="coerce").fillna(0):
        if float(v)<=0: cur+=1; best=max(best,cur)
        else: cur=0
    return best

def bar_pos(idx,ts):
    i=int(idx.searchsorted(pd.Timestamp(ts),"left"))
    if i>=len(idx) or idx[i]!=pd.Timestamp(ts): raise RuntimeError(f"timestamp parity failure: {ts}")
    return i


def parent(m,part):
    q=a17.simulate_cell(m,part,REF_MIN,HOUR,"A56","CENTRAL").copy()
    if q.empty: return q
    q["loss_class"]=[a3.loss_class(r) for _,r in q.iterrows()]
    return q.sort_values("entry_ts").reset_index(drop=True)


def guard_hit(confirmed, close_i, L, R):
    # A55 selected binary state. While structurally alive pre-break, close cannot be < L;
    # retain explicit lower bound to match the frozen A55 characteristic literally.
    return bool((not confirmed) and close_i >= L-EPS and close_i <= L+0.25*R+EPS)


def simulate_a56(m,r,guard_on):
    idx,op,hi,cl=m["idx"],m["open"],m["high"],m["close"]
    ei=bar_pos(idx,r.entry_ts); end_ts=pd.Timestamp(r.execution_start)+HORIZON
    endpos=int(idx.searchsorted(end_ts,"left")); final_i=endpos-1
    if endpos<=ei or endpos>len(idx) or idx[final_i]!=end_ts-BAR: raise RuntimeError("horizon parity")
    bi=bar_pos(idx,r.h1_break_ts) if pd.notna(r.h1_break_ts) else -1
    H,L,R=float(r.H),float(r.L),float(r.R); entry=float(r.entry_price); target=H+TARGET_R*R
    exit_i=final_i; exit_price=float(cl[final_i]); reason="TIME"; guarded=False; wi=-1
    confirmed=bool(bi==ei)

    # Entry candle can be a causal warning opportunity, matching A53 semantics.
    if guard_on and guard_hit(confirmed,float(cl[ei]),L,R):
        ni=ei+1
        if ni<endpos:
            exit_i=ni; exit_price=float(op[ni]); reason="A56_M0_L25_EXIT"; guarded=True; wi=ei

    if not guarded:
        for i in range(ei+1,endpos):
            if not confirmed and bi>=0 and i>=bi: confirmed=True
            if float(hi[i])>=target:
                exit_i=i; exit_price=target; reason="TARGET"; break
            bad=(float(cl[i])<=H+EPS) if confirmed else (float(cl[i])<L-EPS)
            if bad:
                ni=i+1
                if ni<endpos:
                    exit_i=ni; exit_price=float(op[ni]); reason="FAILED_BREAK" if confirmed else "REFERENCE_INVALIDATION"
                else:
                    exit_i=i; exit_price=float(cl[i]); reason="TIME_AFTER_FINAL_INVALIDATION"
                break
            if guard_on and guard_hit(confirmed,float(cl[i]),L,R):
                ni=i+1
                if ni<endpos:
                    exit_i=ni; exit_price=float(op[ni]); reason="A56_M0_L25_EXIT"; guarded=True; wi=i
                    break

    ret=exit_price/entry-1.0; pnl=ret*NOTIONAL; pnl5=(ret-STRESS)*NOTIONAL
    return {
        "variant":"A56_M0_L25" if guard_on else "BASELINE",
        "partition":r.partition,"dev_block":r.dev_block,"execution_start":r.execution_start,"entry_ts":r.entry_ts,
        "parent_exit_ts":r.exit_ts,"parent_exit_reason":r.exit_reason,"parent_pnl":float(r.pnl),"parent_pnl_5bps":float(r.pnl_5bps),
        "parent_won":bool(float(r.pnl)>0),"parent_loss_class":r.loss_class,
        "exit_ts":idx[exit_i],"exit_reason":reason,"exit_price":exit_price,"pnl":pnl,"pnl_5bps":pnl5,
        "won":bool(pnl>0),"won_5bps":bool(pnl5>0),"guard_exit":guarded,
        "warning_ts":idx[wi] if wi>=0 else pd.NaT,"warning_known_ts":idx[wi]+BAR if wi>=0 else pd.NaT,
        "delta_pnl":pnl-float(r.pnl),"delta_pnl_5bps":pnl5-float(r.pnl_5bps),
    }


def replay(m):
    rows=[]; errors=[]
    for p in PARTS:
        q=parent(m,p)
        if len(q)!=EXPECTED_N[p]: errors.append(f"{p} N {len(q)} != {EXPECTED_N[p]}")
        if int((pd.to_numeric(q.pnl,errors="coerce")>0).sum())!=EXPECTED_WIN[p]: errors.append(f"{p} winner mismatch")
        for _,r in q.iterrows():
            b=simulate_a56(m,r,False)
            if abs(float(b["pnl"])-float(r.pnl))>1e-7 or abs(float(b["pnl_5bps"])-float(r.pnl_5bps))>1e-7:
                errors.append(f"baseline parity {p} {r.entry_ts}")
            rows += [b, simulate_a56(m,r,True)]
    if errors: raise RuntimeError("; ".join(errors[:20]))
    t=pd.DataFrame(rows).sort_values(["partition","variant","entry_ts"]).reset_index(drop=True)
    if len(t)!=2438: raise RuntimeError(f"row count {len(t)}")
    return t


def week_rate(q,col):
    z=q.copy(); z["week"]=pd.to_datetime(z.execution_start,utc=True).dt.to_period("W-SUN").astype(str)
    w=z.groupby("week")[col].sum()
    return float((w>0).mean()) if len(w) else np.nan


def metrics_one(q):
    q=q.sort_values("entry_ts"); p=pd.to_numeric(q.pnl,errors="coerce"); p5=pd.to_numeric(q.pnl_5bps,errors="coerce")
    pw=q.parent_won.astype(bool); gd=q.guard_exit.astype(bool)
    return {
        "n":len(q),"wr":float((p>0).mean()),"pf":pf(p),"expectancy":float(p.mean()),"net":float(p.sum()),"max_dd":max_dd(p),"max_loss_streak":max_loss_streak(p),"positive_week_rate":week_rate(q,"pnl"),
        "wr_5bps":float((p5>0).mean()),"pf_5bps":pf(p5),"expectancy_5bps":float(p5.mean()),"net_5bps":float(p5.sum()),"max_dd_5bps":max_dd(p5),"max_loss_streak_5bps":max_loss_streak(p5),"positive_week_rate_5bps":week_rate(q,"pnl_5bps"),
        "guard_exits":int(gd.sum()),"parent_winners_guarded":int((gd&pw).sum()),"parent_winner_guard_rate":float((gd&pw).sum()/pw.sum()) if pw.sum() else np.nan,
        "parent_winners_flipped_nonpositive":int((pw&(p<=0)).sum()),"winner_pnl_delta":float(pd.to_numeric(q.loc[pw,"delta_pnl"],errors="coerce").sum()),
        "loss_pnl_delta":float(pd.to_numeric(q.loc[~pw,"delta_pnl"],errors="coerce").sum()),"delta_net":float(pd.to_numeric(q.delta_pnl,errors="coerce").sum()),"delta_net_5bps":float(pd.to_numeric(q.delta_pnl_5bps,errors="coerce").sum())
    }


def build_metrics(t):
    return pd.DataFrame([{"partition":p,"variant":v,**metrics_one(q)} for (p,v),q in t.groupby(["partition","variant"],sort=False)])


def build_blocks(t):
    d=t[t.partition=="development"]
    b=d[d.variant=="BASELINE"][["entry_ts","dev_block","pnl","pnl_5bps"]].rename(columns={"pnl":"base_pnl","pnl_5bps":"base_pnl_5bps"})
    z=d[d.variant=="A56_M0_L25"][["entry_ts","dev_block","pnl","pnl_5bps"]].merge(b,on=["entry_ts","dev_block"],how="inner")
    rows=[]
    for bi in range(6):
        q=z[pd.to_numeric(z.dev_block,errors="coerce")==bi]
        rows.append({"dev_block":bi,"n":len(q),"delta_net":float((q.pnl-q.base_pnl).sum()),"delta_net_5bps":float((q.pnl_5bps-q.base_pnl_5bps).sum())})
    return pd.DataFrame(rows)


def identity_a53(m,t):
    # Recompute frozen A53 and compare its G1 event set with independently implemented A56.
    t53=a53.replay(m)
    g=t53[t53.guard=="G1_PRE_L25"].copy(); a=t[t.variant=="A56_M0_L25"].copy()
    rows=[]; all_ok=True
    for p in PARTS:
        x=a[a.partition==p].sort_values("entry_ts").reset_index(drop=True); y=g[g.partition==p].sort_values("entry_ts").reset_index(drop=True)
        same_n=len(x)==len(y)
        same_entry=same_n and x.entry_ts.astype(str).tolist()==y.entry_ts.astype(str).tolist()
        same_guard=same_n and x.guard_exit.astype(bool).tolist()==y.guard_exit.astype(bool).tolist()
        # Compare warning/exit timestamps only on guarded rows; unguarded exits also should be identical.
        same_warning=same_n and x.warning_ts.astype(str).tolist()==y.warning_ts.astype(str).tolist()
        same_exit=same_n and x.exit_ts.astype(str).tolist()==y.exit_ts.astype(str).tolist()
        same_pnl=same_n and bool(np.allclose(pd.to_numeric(x.pnl),pd.to_numeric(y.pnl),atol=1e-8,rtol=0))
        same_pnl5=same_n and bool(np.allclose(pd.to_numeric(x.pnl_5bps),pd.to_numeric(y.pnl_5bps),atol=1e-8,rtol=0))
        ok=all([same_n,same_entry,same_guard,same_warning,same_exit,same_pnl,same_pnl5]); all_ok=all_ok and ok
        rows.append({"partition":p,"n":len(x),"a56_guard_exits":int(x.guard_exit.sum()),"a53_guard_exits":int(y.guard_exit.sum()),"same_n":same_n,"same_entry":same_entry,"same_guard_flags":same_guard,"same_warning_ts":same_warning,"same_exit_ts":same_exit,"same_pnl":same_pnl,"same_pnl_5bps":same_pnl5,"identity_exact":ok})
    return pd.DataFrame(rows),all_ok


def evaluate(metrics,blocks):
    b=metrics[(metrics.partition=="development")&(metrics.variant=="BASELINE")].iloc[0]; g=metrics[(metrics.partition=="development")&(metrics.variant=="A56_M0_L25")].iloc[0]
    pr=int((blocks.delta_net>0).sum()); ps=int((blocks.delta_net_5bps>0).sum())
    dev=bool(g.net>b.net+EPS and g.net_5bps>b.net_5bps+EPS and g.pf>b.pf+EPS and g.pf_5bps>b.pf_5bps+EPS and g.wr_5bps+EPS>=b.wr_5bps and g.max_dd<=b.max_dd+EPS and pr>=4 and ps>=4)
    oos={}
    for p in ("external","reference_validation"):
        bb=metrics[(metrics.partition==p)&(metrics.variant=="BASELINE")].iloc[0]; gg=metrics[(metrics.partition==p)&(metrics.variant=="A56_M0_L25")].iloc[0]
        oos[p]=bool(gg.net>bb.net+EPS and gg.net_5bps>bb.net_5bps+EPS and gg.pf>bb.pf+EPS and gg.pf_5bps>bb.pf_5bps+EPS and gg.wr_5bps+EPS>=bb.wr_5bps and gg.max_dd<=bb.max_dd+EPS)
    return dev,oos,pr,ps


def write_result(metrics,blocks,ident,identity_ok,coverage,status,dev,oos,pr,ps):
    lines=["# SOL LONG 15:00 UTC Loss Confirmation Guard — A56 Result","",f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.","",
           "A56 executes the only A55-authorized binary characteristic, `M0_CLOSE_L25`, at the next 5m open whenever it occurs live before breakout confirmation. The future-relative `15m before terminal` label is not used in execution.","",
           "## Identity audit versus A53 G1_PRE_L25","","| Partition | A56 exits | A53 exits | Exact identity |","|---|---:|---:|---:|"]
    for _,r in ident.iterrows(): lines.append(f"| {r.partition} | {int(r.a56_guard_exits)} | {int(r.a53_guard_exits)} | {'YES' if r.identity_exact else 'NO'} |")
    lines += ["",f"Identity exact across all partitions: **{identity_ok}**.","","## Economics","","| Partition | Variant | WR | PF | Net | Exp/trade | DD | Week+ | 5bps WR | 5bps PF | 5bps Net | 5bps Exp | Guard exits | Winners guarded | Winner flips | Winner ΔPnL | Loss ΔPnL | ΔNet |","|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    order={"BASELINE":0,"A56_M0_L25":1}
    for p in PARTS:
        q=metrics[metrics.partition==p].copy(); q["o"]=q.variant.map(order); q=q.sort_values("o")
        for _,r in q.iterrows():
            lines.append(f"| {p} | {r.variant} | {pct(r.wr)} | {fmt(r.pf)} | ${fmt(r.net)} | ${fmt(r.expectancy)} | ${fmt(r.max_dd)} | {pct(r.positive_week_rate)} | {pct(r.wr_5bps)} | {fmt(r.pf_5bps)} | ${fmt(r.net_5bps)} | ${fmt(r.expectancy_5bps)} | {int(r.guard_exits)} | {int(r.parent_winners_guarded)} | {int(r.parent_winners_flipped_nonpositive)} | ${fmt(r.winner_pnl_delta)} | ${fmt(r.loss_pnl_delta)} | ${fmt(r.delta_net)} |")
    lines += ["","## Development block deltas","","| Block | N | Raw ΔNet | 5bps ΔNet |","|---:|---:|---:|---:|"]
    for _,r in blocks.iterrows(): lines.append(f"| {int(r.dev_block)} | {int(r.n)} | ${fmt(r.delta_net)} | ${fmt(r.delta_net_5bps)} |")
    lines += ["",f"Positive Development blocks: **{pr}/6 raw**, **{ps}/6 stress**.","",f"Development support gate: **{'PASS' if dev else 'FAIL'}**.",f"External gate: **{'PASS' if oos.get('external') else 'FAIL'}**.",f"Reference Validation gate: **{'PASS' if oos.get('reference_validation') else 'FAIL'}**.","","## Decision","",f"**Status: {status}**","",
              "If identity is exact, A56 closes the loop: A55's pre-terminal M0 candle anatomy is real, but converting that state into a live hard exit is exactly the already-tested A53 PRE_L25 guard. No new live rule is authorized unless the full preregistered economics gate passes.","","Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8")


def main():
    x,coverage=a2.a1.load5(); m=a2.make_market_with_open(x)
    t=replay(m); metrics=build_metrics(t); blocks=build_blocks(t); ident,identity_ok=identity_a53(m,t)
    dev,oos,pr,ps=evaluate(metrics,blocks)
    if not identity_ok: status="SOL_LONG_15UTC_LOSS_CONFIRMATION_GUARD_A56_IDENTITY_MISMATCH"
    elif dev and all(oos.values()): status="SOL_LONG_15UTC_LOSS_CONFIRMATION_GUARD_A56_SUPPORTED"
    else: status="SOL_LONG_15UTC_LOSS_CONFIRMATION_GUARD_A56_REJECTED"
    t.to_csv(OUT_TRADES,index=False); metrics.to_csv(OUT_METRICS,index=False); blocks.to_csv(OUT_BLOCKS,index=False); ident.to_csv(OUT_ID,index=False)
    OUT_STATUS.write_text(status+"\n",encoding="utf-8"); write_result(metrics,blocks,ident,identity_ok,coverage,status,dev,oos,pr,ps)
    print(status)

if __name__=="__main__": main()
