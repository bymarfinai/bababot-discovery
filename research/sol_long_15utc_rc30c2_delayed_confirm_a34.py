#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
A33_PATH = Path(__file__).resolve().parent / "sol_long_15utc_rc30c2_early_fail_a33.py"
spec = importlib.util.spec_from_file_location("a33", A33_PATH)
a33 = importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(a33)
a26 = a33.a26; a4 = a33.a4; a2 = a33.a2

OUT_MD = ROOT / "SOL_LONG_15UTC_RC30C2_DELAYED_CONFIRM_A34_Result.md"
OUT_DEV = ROOT / "SOL_LONG_15UTC_RC30C2_DELAYED_CONFIRM_A34_DEVELOPMENT.csv"
OUT_OOS = ROOT / "SOL_LONG_15UTC_RC30C2_DELAYED_CONFIRM_A34_OOS.csv"
OUT_TRADES = ROOT / "SOL_LONG_15UTC_RC30C2_DELAYED_CONFIRM_A34_TRADES.csv"
OUT_STATUS = ROOT / "SOL_LONG_15UTC_RC30C2_DELAYED_CONFIRM_A34_Status.txt"

LANES = ("DC5_C10", "DC10_C12", "DC5_OR10")
CELLS = a33.CELLS
TARGET_R = 0.40
STRESS = a2.STRESS


def pf(v):
    x = pd.to_numeric(v, errors="coerce").dropna()
    gp = float(x[x > 0].sum()); gl = float(-x[x <= 0].sum())
    if gl == 0: return np.inf if gp > 0 else np.nan
    return gp / gl


def fmt(v, d=2):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"


def pct(v): return "-" if pd.isna(v) else f"{100*float(v):.1f}%"


def rc30c2_signal(m, r):
    w = a4.recovery_window(m, r)
    if w is None: return None
    _, xi, endpos, _ = w
    idx = m["idx"]; hi = m["high"]; cl = m["close"]
    H = float(r.H); R = float(r.R); target = H + TARGET_R * R
    count = 0; signal = -1
    for i in range(xi, min(xi + 6, endpos)):
        if float(hi[i]) >= target:
            return None
        if float(cl[i]) > H:
            count += 1
            if count >= 2:
                signal = i
                break
    if signal < 0: return None
    return signal, endpos


def confirmation_index(m, r, lane, signal, endpos):
    idx = m["idx"]; hi = m["high"]; cl = m["close"]
    H = float(r.H); R = float(r.R); target = H + TARGET_R * R
    c5 = signal + 1
    c10 = signal + 2

    def alive_through(i):
        if i >= endpos: return False
        for j in range(signal + 1, i + 1):
            if float(hi[j]) >= target: return False
            if float(cl[j]) <= H: return False
        return True

    if lane == "DC5_C10":
        if not alive_through(c5): return -1
        return c5 if (float(cl[c5]) - H) / R >= 0.10 else -1

    if lane == "DC10_C12":
        if not alive_through(c10): return -1
        return c10 if (float(cl[c10]) - H) / R >= 0.12 else -1

    # DC5_OR10: use the first qualifying frozen confirmation.
    if alive_through(c5) and (float(cl[c5]) - H) / R >= 0.10:
        return c5
    if alive_through(c10) and (float(cl[c10]) - H) / R >= 0.12:
        return c10
    return -1


def simulate_one(m, r, lane):
    z = rc30c2_signal(m, r)
    if z is None: return None
    signal, endpos = z
    idx = m["idx"]; op = m["open"]; hi = m["high"]; cl = m["close"]
    H = float(r.H); L = float(r.L); R = float(r.R); target = H + TARGET_R * R
    ci = confirmation_index(m, r, lane, signal, endpos)
    if ci < 0: return None
    entry_i = ci + 1
    if entry_i >= endpos: return None
    entry = float(op[entry_i])
    if entry >= target: return None

    exit_i = endpos - 1; exit_price = float(cl[exit_i]); reason = "TIME"; invalid = -1
    # Match frozen reclaim lifecycle: no target/invalidation credit on delayed-entry bar.
    for i in range(entry_i + 1, endpos):
        if float(hi[i]) >= target:
            exit_i = i; exit_price = target; reason = "TARGET"; break
        if float(cl[i]) <= H:
            invalid = i; ni = i + 1
            if ni < endpos:
                exit_i = ni; exit_price = float(op[ni]); reason = "FAILED_RECLAIM"
            else:
                exit_i = i; exit_price = float(cl[i]); reason = "TIME_AFTER_FINAL_FAILED_RECLAIM"
            break

    ret = exit_price / entry - 1.0
    pnl = ret * a2.NOTIONAL
    pnl5 = (ret - STRESS) * a2.NOTIONAL
    comb = float(r.pnl) + pnl
    comb5 = float(r.pnl_5bps) + pnl5
    return {
        "role": r.role, "partition": r.partition, "dev_block": r.dev_block,
        "execution_start": r.execution_start, "lane": lane,
        "H": H, "L": L, "R": R,
        "parent_entry_ts": r.entry_ts, "parent_exit_ts": r.exit_ts,
        "parent_pnl": float(r.pnl), "parent_pnl_5bps": float(r.pnl_5bps),
        "signal_ts": idx[signal], "confirm_ts": idx[ci],
        "confirm_delay_min": float((idx[ci] - idx[signal]) / pd.Timedelta(minutes=1)),
        "confirm_close_R": (float(cl[ci]) - H) / R,
        "reentry_ts": idx[entry_i], "reentry_price": entry,
        "reentry_R": (entry - H) / R,
        "exit_ts": idx[exit_i], "exit_price": exit_price, "exit_reason": reason,
        "invalidation_close_ts": idx[invalid] if invalid >= 0 else pd.NaT,
        "recovery_pnl": pnl, "recovery_pnl_5bps": pnl5,
        "combined_episode_pnl": comb, "combined_episode_pnl_5bps": comb5,
        "rescued": comb > 0, "rescued_5bps": comb5 > 0,
    }


def simulate_lane(m, parent, lane):
    rows = []
    for _, r in parent[parent.pnl <= 0].iterrows():
        z = simulate_one(m, r, lane)
        if z is not None: rows.append(z)
    return pd.DataFrame(rows)


def stats(parent, t):
    bp = pd.to_numeric(parent.pnl, errors="coerce"); bp5 = pd.to_numeric(parent.pnl_5bps, errors="coerce")
    r = pd.to_numeric(t.recovery_pnl, errors="coerce") if len(t) else pd.Series(dtype=float)
    r5 = pd.to_numeric(t.recovery_pnl_5bps, errors="coerce") if len(t) else pd.Series(dtype=float)
    over = pd.concat([bp, r], ignore_index=True); over5 = pd.concat([bp5, r5], ignore_index=True)
    rmap = {pd.Timestamp(x.parent_entry_ts): x for _, x in t.iterrows()} if len(t) else {}
    ep = []; ep5 = []
    for _, p in parent.iterrows():
        rr = rmap.get(pd.Timestamp(p.entry_ts))
        ep.append(float(p.pnl) + (float(rr.recovery_pnl) if rr is not None else 0.0))
        ep5.append(float(p.pnl_5bps) + (float(rr.recovery_pnl_5bps) if rr is not None else 0.0))
    ep = pd.Series(ep, dtype=float); ep5 = pd.Series(ep5, dtype=float)
    loss_n = int((bp <= 0).sum())
    return {
        "parent_n": len(parent), "parent_wr": float((bp > 0).mean()), "parent_pf": pf(bp), "parent_net": float(bp.sum()),
        "parent_wr_5bps": float((bp5 > 0).mean()), "parent_pf_5bps": pf(bp5), "parent_net_5bps": float(bp5.sum()),
        "recovery_n": len(t), "attempt_rate": len(t) / loss_n if loss_n else np.nan,
        "median_confirm_delay_min": float(pd.to_numeric(t.confirm_delay_min, errors="coerce").median()) if len(t) else np.nan,
        "median_reentry_R": float(pd.to_numeric(t.reentry_R, errors="coerce").median()) if len(t) else np.nan,
        "recovery_wr": float((r > 0).mean()) if len(r) else np.nan, "recovery_pf": pf(r), "recovery_exp": float(r.mean()) if len(r) else np.nan, "recovery_net": float(r.sum()),
        "recovery_wr_5bps": float((r5 > 0).mean()) if len(r5) else np.nan, "recovery_pf_5bps": pf(r5), "recovery_exp_5bps": float(r5.mean()) if len(r5) else np.nan, "recovery_net_5bps": float(r5.sum()),
        "rescue_rate": float(t.rescued.mean()) if len(t) else np.nan, "rescue_rate_5bps": float(t.rescued_5bps.mean()) if len(t) else np.nan,
        "episode_wr": float((ep > 0).mean()), "episode_wr_5bps": float((ep5 > 0).mean()),
        "overlay_pf": pf(over), "overlay_net": float(over.sum()), "overlay_pf_5bps": pf(over5), "overlay_net_5bps": float(over5.sum()),
        "overlay_net_improvement": float(r.sum()), "overlay_net_improvement_5bps": float(r5.sum()),
    }


def dev_row(parent, t, lane):
    s = stats(parent, t); adequate = pos = pos5 = 0; blocks = {}
    for bi in range(6):
        q = t[pd.to_numeric(t.dev_block, errors="coerce") == bi] if len(t) else t
        n = len(q); net = float(pd.to_numeric(q.recovery_pnl, errors="coerce").sum()) if n else 0.0; net5 = float(pd.to_numeric(q.recovery_pnl_5bps, errors="coerce").sum()) if n else 0.0
        blocks[f"b{bi+1}_n"] = n; blocks[f"b{bi+1}_net"] = net; blocks[f"b{bi+1}_net_5bps"] = net5
        if n >= 5:
            adequate += 1; pos += int(net > 0); pos5 += int(net5 > 0)
    up = s["episode_wr"] - s["parent_wr"]; up5 = s["episode_wr_5bps"] - s["parent_wr_5bps"]
    eligible = bool(
        s["recovery_n"] >= 60 and s["recovery_pf"] > 1.20 and s["recovery_pf_5bps"] > 1.05
        and s["recovery_exp"] > 0 and s["recovery_exp_5bps"] > 0 and s["recovery_net"] > 0 and s["recovery_net_5bps"] > 0
        and s["overlay_pf"] > s["parent_pf"] and s["overlay_pf_5bps"] > s["parent_pf_5bps"]
        and s["overlay_net"] > s["parent_net"] and s["overlay_net_5bps"] > s["parent_net_5bps"]
        and up >= 0.04 and up5 >= 0.03 and s["rescue_rate"] >= 0.30
        and adequate >= 4 and pos >= 4 and pos5 >= 4
    )
    return {"lane": lane, **s, "episode_wr_uplift": up, "episode_wr_uplift_5bps": up5,
            "adequate_blocks": adequate, "positive_blocks_raw": pos, "positive_blocks_5bps": pos5,
            "eligible": eligible, **blocks}


def choose(dev):
    q = dev[dev.eligible.astype(bool)].copy()
    if q.empty: return None
    order = {"DC5_C10": 0, "DC5_OR10": 1, "DC10_C12": 2}
    q["simplicity"] = q.lane.map(order)
    return q.sort_values(["overlay_net_improvement_5bps", "overlay_pf_5bps", "overlay_net_improvement", "episode_wr_uplift", "simplicity"], ascending=[False, False, False, False, True]).iloc[0]


def main():
    x, coverage = a2.a1.load5(); m = a2.make_market_with_open(x)
    pdev = a26.parent_cell(m, "development", "CENTRAL", 360, 15)
    dev_rows = []; frames = {}
    for lane in LANES:
        t = simulate_lane(m, pdev, lane); frames[lane] = t; dev_rows.append(dev_row(pdev, t, lane))
    dev = pd.DataFrame(dev_rows); dev.to_csv(OUT_DEV, index=False)
    winner = choose(dev)

    oos_rows = []; alltr = []
    if winner is not None:
        lane = str(winner.lane); z = frames[lane].copy(); z["scope"] = "DEVELOPMENT_FROZEN"; alltr.append(z)
        for role, ref, hour in CELLS:
            for part in ("external", "reference_validation"):
                p = a26.parent_cell(m, part, role, ref, hour); t = simulate_lane(m, p, lane); s = stats(p, t)
                oos_rows.append({"role": role, "partition": part, "ref_min": ref, "hour": hour, "lane": lane, **s})
                if len(t): t = t.copy(); t["scope"] = "OOS"; alltr.append(t)
    oos = pd.DataFrame(oos_rows); oos.to_csv(OUT_OOS, index=False)

    if winner is None:
        status = "SOL_LONG_15UTC_RC30C2_DELAYED_CONFIRM_A34_REJECTED_DEVELOPMENT"
    else:
        central = oos[oos.role == "CENTRAL"]; support = oos[oos.role != "CENTRAL"]
        central_ok = bool(len(central) == 2
            and (central.recovery_net > 0).all() and (central.recovery_net_5bps > 0).all()
            and (central.overlay_pf > central.parent_pf).all() and (central.overlay_pf_5bps > central.parent_pf_5bps).all()
            and (central.overlay_net > central.parent_net).all() and (central.overlay_net_5bps > central.parent_net_5bps).all()
            and ((central.episode_wr - central.parent_wr) >= 0.02).all()
            and ((central.episode_wr_5bps - central.parent_wr_5bps) >= 0.01).all())
        sr = int((support.recovery_net > 0).sum()); ss = int((support.recovery_net_5bps > 0).sum())
        so = int((support.overlay_net > support.parent_net).sum()); so5 = int((support.overlay_net_5bps > support.parent_net_5bps).sum())
        status = "SOL_LONG_15UTC_RC30C2_DELAYED_CONFIRM_A34_SUPPORTED" if central_ok and sr >= 3 and ss >= 3 and so >= 3 and so5 >= 3 else "SOL_LONG_15UTC_RC30C2_DELAYED_CONFIRM_A34_REJECTED_OOS"

    (pd.concat(alltr, ignore_index=True) if alltr else pd.DataFrame()).to_csv(OUT_TRADES, index=False)
    lines = ["# SOL LONG 15:00 UTC RC30_C2 Delayed Confirmation — A34 Result", "", f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.", "",
             "A34 reuses the exact A33 +5/+10m follow-through states as pre-entry confirmation instead of paying for an immediate recovery and exiting weak follow-through later.", "", "## Development", "",
             "| Lane | N | Attempt/loss | Confirm delay | Reentry R | Rec WR | Rec PF | Rec Net | 5bps PF | 5bps Net | Rescue | Parent WR→Episode WR | PF→Overlay | 5bps PF→Overlay | +blocks raw/stress | Pass |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|"]
    for _, r in dev.iterrows():
        lines.append(f"| {r.lane} | {int(r.recovery_n)} | {pct(r.attempt_rate)} | {fmt(r.median_confirm_delay_min,0)}m | {fmt(r.median_reentry_R,3)}R | {pct(r.recovery_wr)} | {fmt(r.recovery_pf)} | ${fmt(r.recovery_net)} | {fmt(r.recovery_pf_5bps)} | ${fmt(r.recovery_net_5bps)} | {pct(r.rescue_rate)} | {pct(r.parent_wr)}→{pct(r.episode_wr)} | {fmt(r.parent_pf)}→{fmt(r.overlay_pf)} | {fmt(r.parent_pf_5bps)}→{fmt(r.overlay_pf_5bps)} | {int(r.positive_blocks_raw)}/{int(r.positive_blocks_5bps)} | {'YES' if bool(r.eligible) else 'NO'} |")
    lines += ["", f"Frozen Development winner: **{str(winner.lane) if winner is not None else 'NONE'}**.", ""]
    if len(oos):
        lines += ["## Frozen OOS", "", "| Role | Partition | N | Rec WR | PF | Net | 5bps PF | 5bps Net | Parent WR→Episode WR | PF→Overlay | 5bps PF→Overlay |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|"]
        for _, r in oos.iterrows():
            lines.append(f"| {r.role} | {r.partition} | {int(r.recovery_n)} | {pct(r.recovery_wr)} | {fmt(r.recovery_pf)} | ${fmt(r.recovery_net)} | {fmt(r.recovery_pf_5bps)} | ${fmt(r.recovery_net_5bps)} | {pct(r.parent_wr)}→{pct(r.episode_wr)} | {fmt(r.parent_pf)}→{fmt(r.overlay_pf)} | {fmt(r.parent_pf_5bps)}→{fmt(r.overlay_pf_5bps)} |")
    lines += ["", "## Decision", "", f"**Status: {status}**", "", "No neighboring follow-through threshold or delay scan is authorized after A34.", "", "Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8"); OUT_STATUS.write_text(status + "\n", encoding="utf-8"); print(status)

if __name__ == "__main__": main()
