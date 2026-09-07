#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A17_PATH = Path(__file__).resolve().parent / "sol_long_multi_clock_expansion_a17.py"
spec = importlib.util.spec_from_file_location("a17", A17_PATH)
a17 = importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(a17)
a4 = a17.a4; a3 = a4.a3; a2 = a17.a2

OUT_TRADES = ROOT / "SOL_LONG_15UTC_EXECUTABLE_GUARD_A53_TRADES.csv"
OUT_METRICS = ROOT / "SOL_LONG_15UTC_EXECUTABLE_GUARD_A53_METRICS.csv"
OUT_BLOCKS = ROOT / "SOL_LONG_15UTC_EXECUTABLE_GUARD_A53_BLOCKS.csv"
OUT_MD = ROOT / "SOL_LONG_15UTC_EXECUTABLE_GUARD_A53_Result.md"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_EXECUTABLE_GUARD_A53_Status.txt"

REF_MIN = 360
HOUR = 15
TARGET_R = 0.40
NOTIONAL = 500.0
STRESS = 0.0005
BAR = pd.Timedelta(minutes=5)
HORIZON = pd.Timedelta(minutes=720)
PARTS = ("development", "external", "reference_validation")
EXPECTED_N = {"development": 601, "external": 281, "reference_validation": 337}
EXPECTED_WIN = {"development": 244, "external": 115, "reference_validation": 150}
GUARDS = ("BASELINE", "G1_PRE_L25", "G2_POST_H05", "G3_POST_H10")
EPS = 1e-12


def fmt(v, d=2):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"

def pct(v): return "-" if pd.isna(v) else f"{100.0*float(v):.1f}%"

def pf(vals):
    x = pd.to_numeric(vals, errors="coerce").dropna()
    gp = float(x[x > 0].sum()); gl = float(-x[x <= 0].sum())
    if gl == 0: return np.inf if gp > 0 else np.nan
    return gp / gl

def max_dd(vals):
    x = pd.to_numeric(vals, errors="coerce").fillna(0.0).to_numpy(float)
    eq = np.concatenate([[0.0], np.cumsum(x)])
    peak = np.maximum.accumulate(eq)
    return float(np.max(peak - eq))

def max_loss_streak(vals):
    best = 0; cur = 0
    for v in pd.to_numeric(vals, errors="coerce").fillna(0.0):
        if float(v) <= 0:
            cur += 1; best = max(best, cur)
        else:
            cur = 0
    return best

def bar_pos(idx, ts):
    i = int(idx.searchsorted(pd.Timestamp(ts), "left"))
    if i >= len(idx) or idx[i] != pd.Timestamp(ts):
        raise RuntimeError(f"timestamp parity failure {ts}")
    return i


def parent(m, part):
    q = a17.simulate_cell(m, part, REF_MIN, HOUR, "A53", "CENTRAL").copy()
    if q.empty: return q
    q["loss_class"] = [a3.loss_class(r) for _, r in q.iterrows()]
    return q.sort_values("entry_ts").reset_index(drop=True)


def guard_hit(guard, confirmed, close_i, H, L, R):
    if guard == "G1_PRE_L25":
        return bool((not confirmed) and close_i <= L + 0.25 * R + EPS)
    if guard == "G2_POST_H05":
        return bool(confirmed and close_i > H + EPS and close_i <= H + 0.05 * R + EPS)
    if guard == "G3_POST_H10":
        return bool(confirmed and close_i > H + EPS and close_i <= H + 0.10 * R + EPS)
    return False


def simulate(m, r, guard):
    idx, op, hi, cl = m["idx"], m["open"], m["high"], m["close"]
    ei = bar_pos(idx, r.entry_ts)
    end_ts = pd.Timestamp(r.execution_start) + HORIZON
    endpos = int(idx.searchsorted(end_ts, "left"))
    if endpos <= ei or endpos > len(idx): raise RuntimeError("bad horizon")
    final_i = endpos - 1
    if idx[final_i] != end_ts - BAR: raise RuntimeError("horizon parity")
    bi = bar_pos(idx, r.h1_break_ts) if pd.notna(r.h1_break_ts) else -1
    H, L, R = float(r.H), float(r.L), float(r.R)
    entry_price = float(r.entry_price)
    target = H + TARGET_R * R

    exit_i = final_i
    exit_price = float(cl[final_i])
    exit_reason = "TIME"
    guard_exit = False
    warning_i = -1
    confirmed = bool(bi == ei)

    # The E0 entry bar itself is not evaluated for parent target/invalidation,
    # but its completed close is a causal A51/A52 warning opportunity.
    if guard != "BASELINE" and guard_hit(guard, confirmed, float(cl[ei]), H, L, R):
        ni = ei + 1
        if ni < endpos:
            exit_i = ni; exit_price = float(op[ni]); exit_reason = f"{guard}_EXIT"
            guard_exit = True; warning_i = ei

    if not guard_exit:
        for i in range(ei + 1, endpos):
            if not confirmed and bi >= 0 and i >= bi:
                confirmed = True

            # Frozen A2 precedence: target first.
            if float(hi[i]) >= target:
                exit_i = i; exit_price = target; exit_reason = "TARGET"
                break

            # Frozen terminal structure next.
            bad = (float(cl[i]) <= H + EPS) if confirmed else (float(cl[i]) < L - EPS)
            if bad:
                ni = i + 1
                if ni < endpos:
                    exit_i = ni; exit_price = float(op[ni])
                    exit_reason = "FAILED_BREAK" if confirmed else "REFERENCE_INVALIDATION"
                else:
                    exit_i = i; exit_price = float(cl[i]); exit_reason = "TIME_AFTER_FINAL_INVALIDATION"
                break

            # Only a still-live trade may be pre-empted by the guard.
            if guard != "BASELINE" and guard_hit(guard, confirmed, float(cl[i]), H, L, R):
                ni = i + 1
                if ni < endpos:
                    exit_i = ni; exit_price = float(op[ni]); exit_reason = f"{guard}_EXIT"
                    guard_exit = True; warning_i = i
                    break

    ret = exit_price / entry_price - 1.0
    pnl = ret * NOTIONAL
    ret5 = ret - STRESS
    pnl5 = ret5 * NOTIONAL
    return {
        "guard": guard,
        "partition": r.partition,
        "dev_block": r.dev_block,
        "execution_start": r.execution_start,
        "entry_ts": r.entry_ts,
        "parent_exit_ts": r.exit_ts,
        "parent_exit_reason": r.exit_reason,
        "parent_pnl": float(r.pnl),
        "parent_pnl_5bps": float(r.pnl_5bps),
        "parent_won": bool(float(r.pnl) > 0),
        "parent_loss_class": r.loss_class,
        "exit_ts": idx[exit_i],
        "exit_reason": exit_reason,
        "exit_price": exit_price,
        "pnl": pnl,
        "pnl_5bps": pnl5,
        "won": bool(pnl > 0),
        "won_5bps": bool(pnl5 > 0),
        "guard_exit": guard_exit,
        "warning_ts": idx[warning_i] if warning_i >= 0 else pd.NaT,
        "warning_known_ts": idx[warning_i] + BAR if warning_i >= 0 else pd.NaT,
        "delta_pnl": pnl - float(r.pnl),
        "delta_pnl_5bps": pnl5 - float(r.pnl_5bps),
    }


def replay(m):
    rows=[]; errors=[]
    for part in PARTS:
        q = parent(m, part)
        if len(q) != EXPECTED_N[part]: errors.append(f"{part} N={len(q)}")
        if int((pd.to_numeric(q.pnl, errors="coerce") > 0).sum()) != EXPECTED_WIN[part]:
            errors.append(f"{part} winner count mismatch")
        for _, r in q.iterrows():
            base = simulate(m, r, "BASELINE")
            if abs(float(base["pnl"]) - float(r.pnl)) > 1e-7:
                errors.append(f"baseline raw parity {part} {r.entry_ts}: {base['pnl']} vs {r.pnl}")
            if abs(float(base["pnl_5bps"]) - float(r.pnl_5bps)) > 1e-7:
                errors.append(f"baseline stress parity {part} {r.entry_ts}: {base['pnl_5bps']} vs {r.pnl_5bps}")
            rows.append(base)
            for g in GUARDS[1:]:
                rows.append(simulate(m, r, g))
    if errors:
        raise RuntimeError("; ".join(errors[:20]))
    t = pd.DataFrame(rows).sort_values(["partition","guard","entry_ts"]).reset_index(drop=True)
    if len(t) != 1219 * len(GUARDS): raise RuntimeError("A53 row-count failure")
    return t


def one_metrics(q):
    q = q.sort_values("entry_ts")
    p = pd.to_numeric(q.pnl, errors="coerce"); p5 = pd.to_numeric(q.pnl_5bps, errors="coerce")
    parent_win = q.parent_won.astype(bool)
    guarded = q.guard_exit.astype(bool)
    return {
        "n": len(q),
        "wr": float((p > 0).mean()), "pf": pf(p), "expectancy": float(p.mean()), "net": float(p.sum()),
        "max_dd": max_dd(p), "max_loss_streak": max_loss_streak(p),
        "wr_5bps": float((p5 > 0).mean()), "pf_5bps": pf(p5), "expectancy_5bps": float(p5.mean()), "net_5bps": float(p5.sum()),
        "max_dd_5bps": max_dd(p5), "max_loss_streak_5bps": max_loss_streak(p5),
        "guard_exits": int(guarded.sum()),
        "parent_winners_guarded": int((guarded & parent_win).sum()),
        "parent_winner_guard_rate": float((guarded & parent_win).sum() / parent_win.sum()) if parent_win.sum() else np.nan,
        "parent_winners_flipped_nonpositive": int((parent_win & (p <= 0)).sum()),
        "winner_pnl_delta": float(pd.to_numeric(q.loc[parent_win,"delta_pnl"],errors="coerce").sum()),
        "loss_pnl_delta": float(pd.to_numeric(q.loc[~parent_win,"delta_pnl"],errors="coerce").sum()),
        "delta_net": float(pd.to_numeric(q.delta_pnl,errors="coerce").sum()),
        "delta_net_5bps": float(pd.to_numeric(q.delta_pnl_5bps,errors="coerce").sum()),
    }


def build_metrics(t):
    rows=[]
    for (part,g),q in t.groupby(["partition","guard"], sort=False):
        rows.append({"partition":part,"guard":g,**one_metrics(q)})
    return pd.DataFrame(rows)


def build_blocks(t):
    rows=[]
    q=t[t.partition=="development"].copy()
    base=q[q.guard=="BASELINE"][["entry_ts","dev_block","pnl","pnl_5bps"]].rename(columns={"pnl":"base_pnl","pnl_5bps":"base_pnl_5bps"})
    for g in GUARDS[1:]:
        z=q[q.guard==g][["entry_ts","dev_block","pnl","pnl_5bps"]].merge(base,on=["entry_ts","dev_block"],how="inner")
        for bi in range(6):
            b=z[pd.to_numeric(z.dev_block,errors="coerce")==bi]
            rows.append({"guard":g,"dev_block":bi,"n":len(b),
                         "delta_net":float((b.pnl-b.base_pnl).sum()),
                         "delta_net_5bps":float((b.pnl_5bps-b.base_pnl_5bps).sum())})
    return pd.DataFrame(rows)


def evaluate(metrics, blocks):
    out=[]
    for g in GUARDS[1:]:
        dev=metrics[(metrics.partition=="development")&(metrics.guard==g)].iloc[0]
        bdev=metrics[(metrics.partition=="development")&(metrics.guard=="BASELINE")].iloc[0]
        bg=blocks[blocks.guard==g]
        pos_raw=int((bg.delta_net>0).sum()); pos5=int((bg.delta_net_5bps>0).sum())
        dev_pass=bool(
            dev.net > bdev.net + EPS and dev.net_5bps > bdev.net_5bps + EPS and
            dev.pf > bdev.pf + EPS and dev.pf_5bps > bdev.pf_5bps + EPS and
            dev.wr_5bps + EPS >= bdev.wr_5bps and dev.max_dd <= bdev.max_dd + EPS and
            pos_raw >= 4 and pos5 >= 4
        )
        oos_pass=True
        detail={"guard":g,"dev_pass":dev_pass,"dev_positive_blocks_raw":pos_raw,"dev_positive_blocks_5bps":pos5}
        for part in ("external","reference_validation"):
            z=metrics[(metrics.partition==part)&(metrics.guard==g)].iloc[0]
            b=metrics[(metrics.partition==part)&(metrics.guard=="BASELINE")].iloc[0]
            pp=bool(z.net>b.net+EPS and z.net_5bps>b.net_5bps+EPS and z.pf>b.pf+EPS and z.pf_5bps>b.pf_5bps+EPS and z.wr_5bps+EPS>=b.wr_5bps and z.max_dd<=b.max_dd+EPS)
            detail[f"{part}_pass"]=pp
            oos_pass = oos_pass and pp
        detail["fully_supported"]=bool(dev_pass and oos_pass)
        out.append(detail)
    return pd.DataFrame(out)


def write_result(metrics, blocks, evals, coverage):
    lines=[
        "# SOL LONG 15:00 UTC Executable Failure Guard — A53 Result","",
        f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.","",
        "A53 executes only the three A52-replicated standalone warnings at the next 5m open. No warning combination or threshold retuning is used.","",
        "## Reconciliation","",
        "Baseline replay parity: **1219/1219 trades exact within tolerance**; expected winner counts 244/115/150 reconciled.","",
        "## Economics by partition","",
        "| Partition | Guard | WR | PF | Net | DD | 5bps WR | 5bps PF | 5bps Net | Guard exits | Parent winners guarded | Winner flips | Winner ΔPnL | Loss ΔPnL | Total ΔNet |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    order={g:i for i,g in enumerate(GUARDS)}
    for part in PARTS:
        q=metrics[metrics.partition==part].copy(); q["ord"]=q.guard.map(order); q=q.sort_values("ord")
        for _,r in q.iterrows():
            lines.append(f"| {part} | {r.guard} | {pct(r.wr)} | {fmt(r.pf)} | ${fmt(r.net)} | ${fmt(r.max_dd)} | {pct(r.wr_5bps)} | {fmt(r.pf_5bps)} | ${fmt(r.net_5bps)} | {int(r.guard_exits)} | {int(r.parent_winners_guarded)} ({pct(r.parent_winner_guard_rate)}) | {int(r.parent_winners_flipped_nonpositive)} | ${fmt(r.winner_pnl_delta)} | ${fmt(r.loss_pnl_delta)} | ${fmt(r.delta_net)} |")
    lines += ["","## Development six-block deltas","","| Guard | +blocks raw | +blocks 5bps | B1 | B2 | B3 | B4 | B5 | B6 |","|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for g in GUARDS[1:]:
        q=blocks[blocks.guard==g].sort_values("dev_block")
        vals=[float(x) for x in q.delta_net]
        lines.append(f"| {g} | {int((q.delta_net>0).sum())}/6 | {int((q.delta_net_5bps>0).sum())}/6 | " + " | ".join(f"${fmt(v)}" for v in vals) + " |")
    lines += ["","## Frozen gate decision","","| Guard | Dev | External | RefVal | Fully supported |","|---|---:|---:|---:|---:|"]
    for _,r in evals.iterrows():
        lines.append(f"| {r.guard} | {'PASS' if r.dev_pass else 'fail'} | {'PASS' if r.external_pass else 'fail'} | {'PASS' if r.reference_validation_pass else 'fail'} | {'YES' if r.fully_supported else 'no'} |")
    winners=evals[evals.fully_supported.astype(bool)].guard.tolist()
    status="SOL_LONG_15UTC_EXECUTABLE_GUARD_A53_SUPPORTED" if winners else "SOL_LONG_15UTC_EXECUTABLE_GUARD_A53_REJECTED"
    lines += ["","## Decision","",f"Fully supported standalone guards: **{', '.join(winners) if winners else 'none'}**.","",f"**Status: {status}**","",
              "A53 is the executable economics test. A warning that was predictive in A52 is rejected here if winner sacrifice or realized execution destroys portfolio economics.","","Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8")
    OUT_STATUS.write_text(status+"\n",encoding="utf-8")
    return status


def main():
    x,coverage=a2.a1.load5(); m=a2.make_market_with_open(x)
    t=replay(m)
    metrics=build_metrics(t); blocks=build_blocks(t); evals=evaluate(metrics,blocks)
    t.to_csv(OUT_TRADES,index=False); metrics.to_csv(OUT_METRICS,index=False); blocks.to_csv(OUT_BLOCKS,index=False)
    status=write_result(metrics,blocks,evals,coverage)
    print(status)

if __name__=="__main__": main()
