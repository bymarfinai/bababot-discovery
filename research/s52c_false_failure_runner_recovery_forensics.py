#!/usr/bin/env python3
"""Saturday T-Method S5.2C — False Failure / Runner Recovery Forensic.

Research only; live BBC untouched. No cancel-protect action is promoted here.

Frozen parent for this forensic is the 43-event FLOW_EMA_PROTECT cohort from S5.2B.
S5.2B proved that generic protection rescues some failed runners but damages latent
future-deep runners. S5.2C asks a narrower causal question:

    after the protect warning is armed, but BEFORE the +0.20% lock would actually
    close the trade, what recovery evidence appears on latent future-deep runners?

Only evidence observable before the frozen lock touch is counted. If the lock is
already lost at the warning decision-open, there is no causal recovery window.

Predeclared descriptive recovery signals (no threshold sweep):
- REBUILD_030: decision-open progress >= +0.30%
- REBUILD_040: decision-open progress >= +0.40%
- EMA7_RECLAIM: decision-open above completed-bar EMA7
- TWO_CLOSES_ABOVE_EMA7
- EMA20_RECLAIM: decision-open above completed-bar EMA20
- EMA20_RISING_RECLAIM: EMA20 reclaim with positive completed EMA20 slope60
- TAKER15_POS: latest 3 completed 5m taker-imbalance mean > 0
- CUM_TAKER_POS: cumulative post-warning taker-imbalance mean > 0
- EMA7_AND_TAKER15
- REBUILD030_AND_EMA7
- REBUILD040_AND_TAKER15
- DEEP_080: completed bar has causally touched +0.80%

Future-DEEP/NONDEEP labels are forensic outcomes only and are never used to form a
signal. The goal is to identify whether a later S5.2D cancel-protect test is even
causally feasible, not to optimize a rule on this sample.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

import s50_saturday_parent_forensics as s50
import s50a_saturday_adaptive_atlas_v2 as a50
import s52a_post_failure_recovery_forensics as a52
import s52b_selective_runner_protect as b52

OUT = Path(os.getenv("S52C_OUT", "s52c_out"))
OUT.mkdir(parents=True, exist_ok=True)
SPLIT = 83
LOCK = 0.002
DEEP = 0.008
TP = s50.TP

SIGNALS = [
    "REBUILD_030",
    "REBUILD_040",
    "EMA7_RECLAIM",
    "TWO_CLOSES_ABOVE_EMA7",
    "EMA20_RECLAIM",
    "EMA20_RISING_RECLAIM",
    "TAKER15_POS",
    "CUM_TAKER_POS",
    "EMA7_AND_TAKER15",
    "REBUILD030_AND_EMA7",
    "REBUILD040_AND_TAKER15",
    "DEEP_080",
]


def slope60(k: pd.DataFrame, bar_t: pd.Timestamp, col: str) -> float:
    old_t = bar_t - pd.Timedelta(minutes=60)
    if old_t not in k.index:
        return np.nan
    old = float(k.loc[old_t, col])
    cur = float(k.loc[bar_t, col])
    return cur / old - 1.0 if old else np.nan


def scan_recovery_window(k: pd.DataFrame, t: pd.Timestamp, tr, base_exit: pd.Timestamp, ev: dict) -> dict:
    """Map recovery signals strictly before the frozen +0.20 lock would close.

    S5.2B execution is adverse-first. Therefore if a bar touches the lock, signals
    from that same completed bar are NOT usable for cancelling protection.
    """
    d = pd.Timestamp(ev["decision_t"])
    op = float(ev["decision_open"])
    lock_px = tr.entry * (1.0 + LOCK)
    tp_px = tr.entry * (1.0 + TP)
    out = {
        "dead_on_arrival": bool(op <= lock_px),
        "lock_t": pd.NaT,
        "tp_before_lock": False,
        "window_minutes": 0.0,
    }
    for s in SIGNALS:
        out[f"{s}_t"] = pd.NaT
        out[f"{s}_min"] = np.nan

    if op <= lock_px:
        out["lock_t"] = d
        return out

    bars = k[(k.index >= d) & (k.index < base_exit)]
    recent_taker: list[float] = []
    cum_taker: list[float] = []
    above7_streak = 0

    for b in bars.itertuples(index=False):
        decision_t = b.ts + pd.Timedelta(minutes=5)
        if decision_t > base_exit:
            break

        # Frozen S5.2B adverse-first: lock touch ends the causal cancel window.
        if float(b.low) <= lock_px:
            out["lock_t"] = decision_t
            out["window_minutes"] = (decision_t - d).total_seconds() / 60.0
            break

        if float(b.high) >= tp_px:
            out["tp_before_lock"] = True

        tak = float(b.taker_imb) if np.isfinite(float(b.taker_imb)) else np.nan
        if np.isfinite(tak):
            recent_taker.append(tak)
            recent_taker = recent_taker[-3:]
            cum_taker.append(tak)

        if decision_t in k.index:
            next_open = float(k.loc[decision_t, "open"])
        else:
            next_open = float(b.close)
        progress = next_open / tr.entry - 1.0
        ema7 = float(k.loc[b.ts, "ema7"])
        ema20 = float(b.ema20)
        s20 = slope60(k, b.ts, "ema20")
        tak15 = float(np.mean(recent_taker)) if len(recent_taker) == 3 else np.nan
        cumtak = float(np.mean(cum_taker)) if cum_taker else np.nan

        close_above7 = float(b.close) > ema7
        above7_streak = above7_streak + 1 if close_above7 else 0

        flags = {
            "REBUILD_030": progress >= 0.003,
            "REBUILD_040": progress >= 0.004,
            "EMA7_RECLAIM": next_open > ema7,
            "TWO_CLOSES_ABOVE_EMA7": above7_streak >= 2,
            "EMA20_RECLAIM": next_open > ema20,
            "EMA20_RISING_RECLAIM": next_open > ema20 and np.isfinite(s20) and s20 > 0,
            "TAKER15_POS": np.isfinite(tak15) and tak15 > 0,
            "CUM_TAKER_POS": np.isfinite(cumtak) and cumtak > 0,
            "EMA7_AND_TAKER15": next_open > ema7 and np.isfinite(tak15) and tak15 > 0,
            "REBUILD030_AND_EMA7": progress >= 0.003 and next_open > ema7,
            "REBUILD040_AND_TAKER15": progress >= 0.004 and np.isfinite(tak15) and tak15 > 0,
            "DEEP_080": float(b.high) / tr.entry - 1.0 >= DEEP,
        }
        for name, flag in flags.items():
            if flag and pd.isna(out[f"{name}_t"]):
                out[f"{name}_t"] = decision_t
                out[f"{name}_min"] = (decision_t - d).total_seconds() / 60.0

        # If original TP is reached without a lock touch, protection itself would
        # close at TP. We can stop scanning after the completed bar is known.
        if float(b.high) >= tp_px:
            out["window_minutes"] = (decision_t - d).total_seconds() / 60.0
            break
    else:
        out["window_minutes"] = (base_exit - d).total_seconds() / 60.0

    return out


def signal_row(df: pd.DataFrame, name: str) -> dict:
    sig = df[f"{name}_t"].notna()
    deep = df.eventual_deep
    disc = df.idx < SPLIT
    val = ~disc
    damaged_deep = deep & (df.protect_delta < -1e-12)
    improved_nondeep = (~deep) & (df.protect_delta > 1e-12)

    def safe_rate(num, den):
        return float(num / den) if den else np.nan

    return {
        "signal": name,
        "n": int(sig.sum()),
        "disc_n": int((sig & disc).sum()),
        "val_n": int((sig & val).sum()),
        "future_deep_n": int((sig & deep).sum()),
        "future_deep_precision": safe_rate(int((sig & deep).sum()), int(sig.sum())),
        "deep_capture": safe_rate(int((sig & deep).sum()), int(deep.sum())),
        "nondeep_n": int((sig & ~deep).sum()),
        "nondeep_signal_rate": safe_rate(int((sig & ~deep).sum()), int((~deep).sum())),
        "disc_deep_capture": safe_rate(int((sig & deep & disc).sum()), int((deep & disc).sum())),
        "val_deep_capture": safe_rate(int((sig & deep & val).sum()), int((deep & val).sum())),
        "damaged_deep_recoverable": int((sig & damaged_deep).sum()),
        "improved_nondeep_at_risk": int((sig & improved_nondeep).sum()),
        "median_signal_min": float(df.loc[sig, f"{name}_min"].median()) if sig.any() else np.nan,
    }


def main():
    k = s50.load_klines()
    # EMA7 is forensic only and uses completed close history.
    k["ema7"] = k["close"].ewm(span=7, adjust=False).mean()
    f = s50.load_funding()
    entries = s50.saturday_entries(k)
    trades = [s50.simulate(k, f, t) for t in entries]

    rows = []
    for i, (t, tr) in enumerate(zip(entries, trades)):
        pre = a50.pre_context(k, t)
        s240 = a50.state240(k, t, tr)
        base_pnl = a50.a719_pnl(k, f, t, tr, s240)
        base_exit = b52.a719_exit_time(t, tr, s240)
        h05, h08 = a52.first_hinges(k, t, tr)
        mem = a52.prehinge_memory(k, t, tr, h05) if h05 is not None else {"prior_failure": False, "hinge_taker": np.nan}
        ev = b52.first_action_event(
            k, t, tr, base_exit, h05,
            bool(mem.get("prior_failure", False)), mem.get("hinge_taker", np.nan),
            adaptive=False,
        )
        if ev is None:
            continue
        protect_pnl, protect_reason, protect_exit_t, _ = b52.protected_pnl(k, f, t, tr, base_exit, base_pnl, ev)
        rec = {
            "idx": i,
            "date": tr.date,
            "pre_state": pre["pre_state"],
            "a719_pnl": float(base_pnl),
            "protect_pnl": float(protect_pnl),
            "protect_delta": float(protect_pnl - base_pnl),
            "protect_reason": protect_reason,
            "protect_exit_t": str(protect_exit_t),
            "event_t": str(ev["decision_t"]),
            "event_min": (ev["decision_t"] - t).total_seconds() / 60.0,
            "event_progress": ev["decision_open"] / tr.entry - 1.0,
            "event_post_taker": ev["post_taker"],
            "event_ema_dist": ev["decision_open"] / ev["ema20"] - 1.0,
            "prior_failure": bool(mem.get("prior_failure", False)),
            "hinge_taker": mem.get("hinge_taker", np.nan),
            "eventual_deep": bool(h08 is not None),
        }
        rec.update(scan_recovery_window(k, t, tr, base_exit, ev))
        rows.append(rec)

    df = pd.DataFrame(rows).sort_values("idx").reset_index(drop=True)

    # Hard S5.2B parity gates.
    if len(df) != 43:
        raise RuntimeError(f"FLOW_EMA action parity failed: {len(df)}")
    if (int((df.idx < SPLIT).sum()), int((df.idx >= SPLIT).sum())) != (28, 15):
        raise RuntimeError("FLOW_EMA D/V parity failed")
    if int(df.eventual_deep.sum()) != 19:
        raise RuntimeError("future-deep action parity failed")
    if int(((df.eventual_deep) & (df.protect_delta < -1e-12)).sum()) != 15:
        raise RuntimeError("future-deep damaged parity failed")
    if abs(df.loc[~df.eventual_deep, "protect_delta"].sum() - 29.221508) > 0.02:
        raise RuntimeError("nondeep rescue economics parity failed")
    if abs(df.loc[df.eventual_deep, "protect_delta"].sum() + 81.569365) > 0.02:
        raise RuntimeError("deep damage economics parity failed")

    df.to_csv(OUT / "s52c_event_forensics.csv", index=False)
    sig_rows = [signal_row(df, s) for s in SIGNALS]
    sig = pd.DataFrame(sig_rows).sort_values(["damaged_deep_recoverable", "future_deep_precision"], ascending=[False, False]).reset_index(drop=True)
    sig.to_csv(OUT / "s52c_recovery_signals.csv", index=False)

    deep = df[df.eventual_deep]
    nondeep = df[~df.eventual_deep]
    damaged_deep = df[df.eventual_deep & (df.protect_delta < -1e-12)]
    summary = {
        "flow_events": len(df),
        "disc_events": int((df.idx < SPLIT).sum()),
        "val_events": int((df.idx >= SPLIT).sum()),
        "future_deep": len(deep),
        "nondeep": len(nondeep),
        "future_deep_damaged": len(damaged_deep),
        "dead_on_arrival": int(df.dead_on_arrival.sum()),
        "dead_on_arrival_deep": int((df.dead_on_arrival & df.eventual_deep).sum()),
        "deep_damage_delta": float(deep.protect_delta.sum()),
        "nondeep_delta": float(nondeep.protect_delta.sum()),
        "signals": sig.to_dict(orient="records"),
    }
    (OUT / "s52c_summary.json").write_text(json.dumps(summary, indent=2, default=float))

    def pct(x):
        return "NA" if not np.isfinite(x) else f"{100*x:.2f}%"

    lines = [
        "# BTC Temporal Saturday T-Method S5.2C — False Failure / Runner Recovery Forensic",
        "",
        "**Status:** COMPLETE — FORENSIC ONLY; NO CANCEL-PROTECT RULE PROMOTED",
        "**Research only:** live BBC untouched",
        "",
        "## Frozen S5.2B parity",
        f"- FLOW_EMA protect events: **{len(df)}** = {int((df.idx<SPLIT).sum())} discovery / {int((df.idx>=SPLIT).sum())} validation",
        f"- Future deep runners among warnings: **{len(deep)}**",
        f"- Nondeep warnings: **{len(nondeep)}**",
        f"- Damaged future-deep: **{len(damaged_deep)}**",
        f"- Nondeep protect contribution: **${nondeep.protect_delta.sum():+.3f}**",
        f"- Future-deep protect contribution: **${deep.protect_delta.sum():+.3f}**",
        "",
        "## Causal recovery-window integrity",
        f"- Dead-on-arrival warning (lock already lost at decision-open): **{int(df.dead_on_arrival.sum())}**",
        f"- Future-deep dead-on-arrival: **{int((df.dead_on_arrival & df.eventual_deep).sum())}**",
        "- Signals from the same 5m bar that touches the +0.20 lock are excluded (adverse-first).",
        "- Therefore every reported recovery signal was actually knowable before frozen protection would have exited.",
        "",
        "## Predeclared recovery signals",
        "| Signal | N D/V | Future-deep precision | Deep capture | D deep capture | V deep capture | Damaged-deep recoverable | Improved-nondeep at risk | Median lead from warning |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in sig.iterrows():
        lines.append(
            f"| {r.signal} | {int(r.n)} {int(r.disc_n)}/{int(r.val_n)} | {pct(r.future_deep_precision)} | {pct(r.deep_capture)} | "
            f"{pct(r.disc_deep_capture)} | {pct(r.val_deep_capture)} | {int(r.damaged_deep_recoverable)} | {int(r.improved_nondeep_at_risk)} | "
            f"{('NA' if not np.isfinite(r.median_signal_min) else f'{r.median_signal_min:.1f}m')} |"
        )
    lines += [
        "",
        "## Interpretation guardrail",
        "- Future DEEP/NONDEEP is used only as a forensic outcome label.",
        "- No signal threshold is optimized here and no cancel action is applied.",
        "- A useful S5.2D candidate must appear before lock, recover a meaningful fraction of the 15 damaged latent deep runners, and avoid cancelling protection on too many nondeep trades that S5.2B genuinely improved.",
    ]
    (OUT / "S5.2C_CHECKPOINT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=2, default=float))


if __name__ == "__main__":
    main()
