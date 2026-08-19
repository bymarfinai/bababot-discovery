#!/usr/bin/env python3
"""G4 — pooled frozen-A5.11 execution compatibility.

Research only; live BBC untouched.

Preregistered in BTC_Global_Regime_G4_Preregistration.md.
The frozen Tuesday A5.11 SELL stack is replayed at every eligible hourly BTC
state to create an execution-aligned pooled binary target. Strategy parameters
are never tuned here.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import g0_global_pooled_regime_dataset as g0
import g0_global_pooled_regime_dataset_fast as g0fast
import tuesday_a511_true_oos_august as tue

OUT = Path(os.getenv("G4_OUT", "g4_out"))
OUT.mkdir(parents=True, exist_ok=True)
G0_DATA = Path(os.getenv("G0_DATA", "../BTC_Global_Regime_G0_Pooled_Hourly_States.csv"))

FEATURES = list(g0.FEATURES)
FIRST_MONTH = pd.Timestamp("2024-03-01", tz="UTC")
HIST_END = pd.Timestamp("2026-07-30", tz="UTC")
EMBARGO = pd.Timedelta(hours=6)
EXPECTED_AUG = ["2026-08-04", "2026-08-11", "2026-08-18"]

# Frozen A5.11 constants copied from the canonical Tuesday replay.
NOTIONAL = 500.0
FEE = 0.0015 * NOTIONAL
TP = 0.0135
SL = 0.0080
HOLD_BARS = 72                 # 6h on 5m bars
HINGE = 0.0050
LOCK = 0.0020
A52_WEAK = 0.0035
A52_MAE = 0.0020
FAST_D20 = 0.0040
FAST_GIVEBACK = 0.0030
FAST_BARS = 12                 # 60m
RECOVERY_PROGRESS = 0.0030


@dataclass
class Parent:
    start: int
    exit_exclusive: int
    entry: float
    exit_px: float
    pnl: float
    mfe: float
    mae: float
    reason: str


@dataclass
class Hinge:
    bar: int
    decision: int
    close_progress: float
    cum_mae: float
    d20: float


class FastFrozenA511:
    """Array-backed simulator matching the canonical frozen Tuesday functions."""

    def __init__(self, k: pd.DataFrame):
        self.k = k.sort_index()
        self.idx = self.k.index
        self.open = self.k.open.to_numpy(float)
        self.high = self.k.high.to_numpy(float)
        self.low = self.k.low.to_numpy(float)
        self.close = self.k.close.to_numpy(float)
        self.ema7 = self.k.ema7.to_numpy(float)
        self.ema20 = self.k.ema20.to_numpy(float)
        self.pos = {t: i for i, t in enumerate(self.idx)}

    @staticmethod
    def pnl_at(ep: float, px: float) -> float:
        return float(NOTIONAL * (1.0 - float(px) / float(ep)) - FEE)

    def parent(self, t: pd.Timestamp) -> Parent:
        s = self.pos.get(t)
        if s is None:
            raise RuntimeError(f"decision timestamp missing from klines: {t}")
        emax = s + HOLD_BARS
        if emax > len(self.idx):
            raise RuntimeError(f"incomplete 6h horizon: {t}")
        # Enforce exactly contiguous 5m horizon like canonical replay.
        if self.idx[emax - 1] != t + pd.Timedelta(minutes=5 * (HOLD_BARS - 1)):
            raise RuntimeError(f"noncontiguous 6h horizon: {t}")

        ep = float(self.open[s])
        tpp = ep * (1.0 - TP)
        slp = ep * (1.0 + SL)
        reason = "TIMEOUT"
        exit_excl = emax
        exit_px = float(self.close[emax - 1])
        mfe = 0.0
        mae = 0.0
        for p in range(s, emax):
            mfe = max(mfe, 1.0 - float(self.low[p]) / ep)
            mae = max(mae, float(self.high[p]) / ep - 1.0)
            # Canonical conservative OHLC ordering: SL before TP inside a bar.
            if float(self.high[p]) >= slp:
                reason = "SL"
                exit_excl = p + 1
                exit_px = slp
                break
            if float(self.low[p]) <= tpp:
                reason = "TP"
                exit_excl = p + 1
                exit_px = tpp
                break
        return Parent(
            start=s,
            exit_exclusive=exit_excl,
            entry=ep,
            exit_px=exit_px,
            pnl=self.pnl_at(ep, exit_px),
            mfe=float(mfe),
            mae=float(mae),
            reason=reason,
        )

    def first_hinge(self, tr: Parent) -> Hinge | None:
        ep = tr.entry
        for p in range(tr.start, tr.exit_exclusive):
            if 1.0 - float(self.low[p]) / ep >= HINGE:
                d = p + 1
                if tr.exit_exclusive <= d:
                    return None
                cum_mae = float(np.max(self.high[tr.start:d])) / ep - 1.0
                return Hinge(
                    bar=p,
                    decision=d,
                    close_progress=1.0 - float(self.close[p]) / ep,
                    cum_mae=float(cum_mae),
                    d20=float(self.ema20[p]) / float(self.close[p]) - 1.0,
                )
        return None

    def run_protect(self, tr: Parent, h: Hinge | None) -> tuple[float, bool, str | None]:
        if h is None:
            return float(tr.pnl), False, None
        if not (h.close_progress <= A52_WEAK and h.cum_mae >= A52_MAE):
            return float(tr.pnl), False, None
        ep = tr.entry
        lp = ep * (1.0 - LOCK)
        op = float(self.open[h.decision])
        if op >= lp:
            return self.pnl_at(ep, op), True, "A5.2_MARKET"
        for p in range(h.decision, tr.exit_exclusive):
            if float(self.high[p]) >= lp:
                return self.pnl_at(ep, lp), True, "A5.2_LOCK"
            if float(self.low[p]) <= ep * (1.0 - TP):
                return float(tr.pnl), True, "PARENT_TP"
        return float(tr.pnl), True, "PARENT"

    def fastmr_arm(self, tr: Parent, h: Hinge | None) -> int | None:
        if h is None or h.d20 < FAST_D20:
            return None
        stop = min(tr.exit_exclusive, h.decision + FAST_BARS)
        ep = tr.entry
        for p in range(h.decision, stop):
            prog = 1.0 - float(self.close[p]) / ep
            if prog <= FAST_GIVEBACK:
                d = p + 1
                if tr.exit_exclusive <= d:
                    return None
                return d
        return None

    def run_fastmr(self, tr: Parent, arm: int | None, recovery: bool) -> tuple[float, bool, bool, str]:
        if arm is None:
            return float(tr.pnl), False, False, "PARENT"
        ep = tr.entry
        lp = ep * (1.0 - LOCK)
        op = float(self.open[arm])
        if op >= lp:
            return self.pnl_at(ep, op), True, False, "FASTMR_MARKET"
        for p in range(arm, tr.exit_exclusive):
            if float(self.high[p]) >= lp:
                return self.pnl_at(ep, lp), True, False, "FASTMR_LOCK"
            if recovery:
                prog = 1.0 - float(self.close[p]) / ep
                if (
                    float(self.high[p]) >= float(self.ema7[p])
                    and float(self.close[p]) < float(self.ema7[p])
                    and prog >= RECOVERY_PROGRESS
                ):
                    cancel = p + 1
                    if tr.exit_exclusive > cancel:
                        return float(tr.pnl), True, True, "A5.11_RUNNER_RECOVERY"
        return float(tr.pnl), True, False, "PARENT"

    def simulate(self, t: pd.Timestamp) -> dict:
        tr = self.parent(t)
        h = self.first_hinge(tr)
        a52_pnl, a52_act, a52_layer = self.run_protect(tr, h)
        if a52_act:
            return {
                "parent_pnl": float(tr.pnl),
                "a511_pnl": float(a52_pnl),
                "win": bool(a52_pnl > 0),
                "a52_act": True,
                "fastmr_act": False,
                "recovery": False,
                "final_layer": a52_layer,
                "mfe": tr.mfe,
                "mae": tr.mae,
            }
        arm = self.fastmr_arm(tr, h)
        a511, fast_act, rec, layer = self.run_fastmr(tr, arm, True)
        return {
            "parent_pnl": float(tr.pnl),
            "a511_pnl": float(a511),
            "win": bool(a511 > 0),
            "a52_act": False,
            "fastmr_act": bool(fast_act),
            "recovery": bool(rec),
            "final_layer": layer if fast_act else "PARENT",
            "mfe": tr.mfe,
            "mae": tr.mae,
        }


def parity_check(k: pd.DataFrame, sim: FastFrozenA511) -> dict:
    rows = []
    max_abs_delta = 0.0
    for t in tue.entries(k):
        fast = sim.simulate(t)
        ref_tr = tue.simulate_parent(k, t)
        ref = tue.layered(k, ref_tr)
        delta = float(fast["a511_pnl"] - ref["a511_pnl"])
        max_abs_delta = max(max_abs_delta, abs(delta))
        rows.append({"t": t, **fast, "ref_pnl": float(ref["a511_pnl"]), "delta": delta})
    df = pd.DataFrame(rows)
    p = df.a511_pnl.to_numpy(float)
    summary = {
        "n": int(len(df)),
        "wins": int((p > 0).sum()),
        "pnl": float(p.sum()),
        "a52_actions": int(df.a52_act.sum()),
        "fastmr_actions": int(df.fastmr_act.sum()),
        "recoveries": int(df.recovery.sum()),
        "max_abs_trade_pnl_delta_vs_canonical": float(max_abs_delta),
    }
    checks = {
        "n139": summary["n"] == 139,
        "wins89": summary["wins"] == 89,
        "pnl_130_33": abs(summary["pnl"] - 130.3285205371619) < 1e-8,
        "a52_actions7": summary["a52_actions"] == 7,
        "fastmr_actions12": summary["fastmr_actions"] == 12,
        "recoveries4": summary["recoveries"] == 4,
        "trade_level_exact": summary["max_abs_trade_pnl_delta_vs_canonical"] < 1e-10,
    }
    return {"summary": summary, "checks": checks, "pass": bool(all(checks.values()))}


def make_model() -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("logit", LogisticRegression(
            penalty="l2", C=1.0, solver="lbfgs", max_iter=2000,
            class_weight=None, random_state=7,
        )),
    ])


def binary_metrics(y: np.ndarray, p: np.ndarray, pred: np.ndarray) -> dict:
    y = np.asarray(y, int)
    p = np.asarray(p, float)
    pred = np.asarray(pred, bool)
    return {
        "n": int(len(y)),
        "win_rate": float(y.mean()),
        "accuracy": float(accuracy_score(y, pred.astype(int))),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "brier": float(brier_score_loss(y, p)),
        "auc": float(roc_auc_score(y, p)),
        "trade_coverage": float(pred.mean()),
        "trade_win_rate": float(y[pred].mean()) if pred.any() else None,
        "trades": int(pred.sum()),
        "waits": int((~pred).sum()),
    }


def load_g0() -> pd.DataFrame:
    df = pd.read_csv(G0_DATA)
    df["decision_t_utc"] = pd.to_datetime(df.decision_t_utc, utc=True)
    df = df.sort_values("decision_t_utc").reset_index(drop=True)
    if len(df) != 23304:
        raise RuntimeError(f"unexpected G0 row count {len(df)}")
    return df


def build_execution_labels(g0df: pd.DataFrame, sim: FastFrozenA511) -> pd.DataFrame:
    rows = []
    for t in g0df.decision_t_utc:
        r = sim.simulate(t)
        rows.append(r)
    x = pd.DataFrame(rows)
    out = pd.concat([g0df.reset_index(drop=True), x], axis=1)
    return out


def month_starts() -> list[pd.Timestamp]:
    out = []
    cur = FIRST_MONTH
    while cur < HIST_END:
        out.append(cur)
        cur = cur + pd.offsets.MonthBegin(1)
    return out


def walkforward(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rows = []
    embargo_checks = []
    for ms in month_starts():
        me = min(ms + pd.offsets.MonthBegin(1), HIST_END)
        train = df[(df.decision_t_utc + EMBARGO) <= ms]
        test = df[(df.decision_t_utc >= ms) & (df.decision_t_utc < me)]
        if test.empty:
            continue
        if len(train) < 1000 or train.win.nunique() < 2:
            raise RuntimeError(f"invalid training set for {ms}: n={len(train)} classes={train.win.value_counts().to_dict()}")
        latest_mature = train.decision_t_utc.max() + EMBARGO
        ok = bool(latest_mature <= ms)
        embargo_checks.append({
            "month": str(ms.date()), "train_n": int(len(train)), "test_n": int(len(test)),
            "latest_train_label_matures": str(latest_mature), "month_start": str(ms), "pass": ok,
        })
        if not ok:
            raise RuntimeError(f"embargo violation for {ms}")

        model = make_model()
        model.fit(train[FEATURES], train.win.astype(int))
        p = model.predict_proba(test[FEATURES])[:, 1]
        trade = p >= 0.50
        prior = float(train.win.mean())
        base_p = np.full(len(test), prior, dtype=float)
        base_pred = base_p >= 0.50
        for j, (_, r) in enumerate(test.iterrows()):
            rows.append({
                "decision_t_utc": r.decision_t_utc,
                "actual_win": int(bool(r.win)),
                "a511_pnl": float(r.a511_pnl),
                "p_win": float(p[j]),
                "trade": bool(trade[j]),
                "baseline_p_win": prior,
                "baseline_trade": bool(base_pred[j]),
                "model_month": str(ms.date()),
                "train_n": int(len(train)),
            })

    wf = pd.DataFrame(rows).sort_values("decision_t_utc").reset_index(drop=True)
    y = wf.actual_win.to_numpy(int)
    p = wf.p_win.to_numpy(float)
    tr = wf.trade.to_numpy(bool)
    bp = wf.baseline_p_win.to_numpy(float)
    btr = wf.baseline_trade.to_numpy(bool)
    model_m = binary_metrics(y, p, tr)
    base_m = binary_metrics(y, bp, btr)

    blocks = []
    for b, idx in enumerate(np.array_split(np.arange(len(wf)), 4), start=1):
        x = wf.iloc[idx]
        yy = x.actual_win.to_numpy(int)
        pp = x.p_win.to_numpy(float)
        bb = x.baseline_p_win.to_numpy(float)
        ml = float(log_loss(yy, pp, labels=[0, 1]))
        bl = float(log_loss(yy, bb, labels=[0, 1]))
        mb = float(brier_score_loss(yy, pp))
        bbr = float(brier_score_loss(yy, bb))
        blocks.append({
            "block": b, "start": str(x.iloc[0].decision_t_utc), "end": str(x.iloc[-1].decision_t_utc),
            "n": int(len(x)), "model_log_loss": ml, "baseline_log_loss": bl,
            "model_brier": mb, "baseline_brier": bbr, "logloss_improved": bool(ml < bl),
        })

    trade_wr = model_m["trade_win_rate"] if model_m["trade_win_rate"] is not None else 0.0
    checks = {
        "predictions_ge_18000": bool(len(wf) >= 18000),
        "causal_embargo_all_months": bool(all(x["pass"] for x in embargo_checks)),
        "logloss_beats_prior": bool(model_m["log_loss"] < base_m["log_loss"]),
        "brier_beats_prior": bool(model_m["brier"] < base_m["brier"]),
        "auc_ge_055": bool(model_m["auc"] >= 0.55),
        "trade_coverage_ge_20pct": bool(model_m["trade_coverage"] >= 0.20),
        "trade_wr_enrichment_ge_3pp": bool(trade_wr >= model_m["win_rate"] + 0.03),
        "logloss_improves_3_of_4_blocks": bool(sum(x["logloss_improved"] for x in blocks) >= 3),
    }
    return wf, {
        "model": model_m,
        "baseline": base_m,
        "wr_enrichment_pp": 100.0 * (trade_wr - model_m["win_rate"]),
        "blocks": blocks,
        "embargo_checks": embargo_checks,
        "acceptance_checks": checks,
        "pass": bool(all(checks.values())),
    }


def trade_metrics(pnls: np.ndarray, traded: np.ndarray | None = None) -> dict:
    pnls = np.asarray(pnls, float)
    if traded is None:
        traded = np.ones(len(pnls), dtype=bool)
    else:
        traded = np.asarray(traded, bool)
    realized = np.where(traded, pnls, 0.0)
    x = pnls[traded]
    wins = int((x > 0).sum()) if len(x) else 0
    gp = float(x[x > 0].sum()) if len(x) else 0.0
    gl = float(-x[x <= 0].sum()) if len(x) else 0.0
    eq = np.cumsum(realized)
    if len(eq):
        peak = np.maximum.accumulate(np.r_[0.0, eq])
        dd = float(np.max(peak[1:] - eq))
    else:
        dd = 0.0
    return {
        "opportunities": int(len(pnls)), "trades": int(traded.sum()), "waits": int((~traded).sum()),
        "coverage": float(traded.mean()) if len(traded) else None,
        "wins": wins, "losses": int(len(x) - wins),
        "trade_wr": float(wins / len(x)) if len(x) else None,
        "pnl": float(realized.sum()),
        "exp_per_opportunity": float(realized.mean()) if len(realized) else None,
        "exp_per_trade": float(x.mean()) if len(x) else None,
        "pf": float(gp / gl) if gl > 0 else (999.0 if gp > 0 else None),
        "max_dd": dd,
    }


def tuesday_overlay(wf: pd.DataFrame, labeled: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    pred = wf.set_index("decision_t_utc")
    lmap = labeled.set_index("decision_t_utc")
    rows = []
    local = labeled.decision_t_utc + pd.Timedelta(hours=7)
    tue_mask = (local.dt.dayofweek == 1) & (local.dt.hour == 6) & (local.dt.minute == 0)
    for t in labeled.loc[tue_mask, "decision_t_utc"]:
        if t not in pred.index:
            continue
        p = pred.loc[t]
        r = lmap.loc[t]
        rows.append({
            "date_wib": str((t + pd.Timedelta(hours=7)).date()),
            "decision_t_utc": t,
            "p_win": float(p.p_win),
            "trade": bool(p.trade),
            "a511_pnl": float(r.a511_pnl),
            "a511_win": bool(r.win),
        })
    td = pd.DataFrame(rows).sort_values("decision_t_utc").reset_index(drop=True)
    pnls = td.a511_pnl.to_numpy(float)
    tr = td.trade.to_numpy(bool)
    base = trade_metrics(pnls)
    gate = trade_metrics(pnls, tr)
    blocks = []
    for b, idx in enumerate(np.array_split(np.arange(len(td)), 4), start=1):
        x = td.iloc[idx]
        xb = trade_metrics(x.a511_pnl.to_numpy(float))
        xg = trade_metrics(x.a511_pnl.to_numpy(float), x.trade.to_numpy(bool))
        blocks.append({
            "block": b, "start": x.iloc[0].date_wib, "end": x.iloc[-1].date_wib,
            "baseline": xb, "gated": xg, "pnl_delta": float(xg["pnl"] - xb["pnl"]),
        })
    checks = {
        "coverage_ge_35pct": bool(gate["coverage"] >= 0.35),
        "exp_per_opportunity_improves": bool(gate["exp_per_opportunity"] > base["exp_per_opportunity"]),
        "total_pnl_ge_baseline": bool(gate["pnl"] >= base["pnl"]),
        "trade_wr_improves": bool(gate["trade_wr"] > base["trade_wr"]),
        "positive_delta_3_of_4_blocks": bool(sum(x["pnl_delta"] > 0 for x in blocks) >= 3),
    }
    return td, {
        "baseline": base, "gated": gate, "blocks": blocks,
        "promotion_checks": checks, "shadow_candidate_pass": bool(all(checks.values())),
    }


def final_model(labeled: pd.DataFrame) -> Pipeline:
    model = make_model()
    model.fit(labeled[FEATURES], labeled.win.astype(int))
    return model


def august_batch(labeled: pd.DataFrame, k: pd.DataFrame, sim: FastFrozenA511) -> tuple[pd.DataFrame, dict]:
    model = final_model(labeled)
    kprep = g0.prepare(k)
    rows = []
    times = tue.entries(kprep, pd.Timestamp("2026-08-01", tz="UTC"), pd.Timestamp("2026-08-19", tz="UTC"))
    for t in times:
        feat, ferr = g0fast.feature_row_fast(kprep, t)
        if ferr:
            raise RuntimeError(f"August feature error {t}: {ferr}")
        X = pd.DataFrame([{f: feat[f] for f in FEATURES}])
        p = float(model.predict_proba(X)[:, 1][0])
        ex = sim.simulate(t)
        rows.append({
            "date_wib": str((t + pd.Timedelta(hours=7)).date()), "decision_t_utc": t,
            "p_win": p, "trade": bool(p >= 0.50),
            "a511_pnl": float(ex["a511_pnl"]), "actual_win": bool(ex["win"]),
        })
    aug = pd.DataFrame(rows)
    if aug.date_wib.tolist() != EXPECTED_AUG:
        raise RuntimeError(f"unexpected August dates {aug.date_wib.tolist()}")
    return aug, {
        "n": int(len(aug)), "trades": int(aug.trade.sum()), "waits": int((~aug.trade).sum()),
        "always_trade_pnl": float(aug.a511_pnl.sum()),
        "gated_pnl": float(aug.loc[aug.trade, "a511_pnl"].sum()),
    }


def model_state(labeled: pd.DataFrame) -> dict:
    m = final_model(labeled)
    imp = m.named_steps["imputer"]
    sc = m.named_steps["scale"]
    lr = m.named_steps["logit"]
    return {
        "features": FEATURES,
        "imputer_medians": {f: float(v) for f, v in zip(FEATURES, imp.statistics_)},
        "scaler_mean": {f: float(v) for f, v in zip(FEATURES, sc.mean_)},
        "scaler_scale": {f: float(v) for f, v in zip(FEATURES, sc.scale_)},
        "logit_coef": {f: float(v) for f, v in zip(FEATURES, lr.coef_[0])},
        "logit_intercept": float(lr.intercept_[0]),
        "training_n": int(len(labeled)), "training_win_rate": float(labeled.win.mean()),
        "training_end_exclusive": str(HIST_END), "decision_threshold": 0.50,
    }


def main() -> None:
    g0df = load_g0()
    k = tue.load_extended()
    sim = FastFrozenA511(k)

    parity = parity_check(k, sim)
    if not parity["pass"]:
        (OUT / "g4_parity_failure.json").write_text(json.dumps(parity, indent=2, default=str))
        raise RuntimeError("G4 generic A5.11 simulator parity failed: " + json.dumps(parity, default=str))

    labeled = build_execution_labels(g0df, sim)
    wf, pooled = walkforward(labeled)
    td, overlay = tuesday_overlay(wf, labeled)
    aug, aug_summary = august_batch(labeled, k, sim)
    state = model_state(labeled)

    overall = {
        "status": (
            "G4_POOLED_PASS_TUESDAY_SHADOW_PASS" if pooled["pass"] and overlay["shadow_candidate_pass"]
            else "G4_POOLED_PASS_TUESDAY_SHADOW_FAIL" if pooled["pass"]
            else "G4_POOLED_GATE_FAILED"
        ),
        "preregistration": "BTC_Global_Regime_G4_Preregistration.md",
        "parity": parity,
        "pooled_label": {
            "n": int(len(labeled)), "wins": int(labeled.win.sum()),
            "losses": int((~labeled.win).sum()), "win_rate": float(labeled.win.mean()),
            "pnl": float(labeled.a511_pnl.sum()),
            "a52_actions": int(labeled.a52_act.sum()), "fastmr_actions": int(labeled.fastmr_act.sum()),
            "recoveries": int(labeled.recovery.sum()),
        },
        "pooled": pooled,
        "tuesday_overlay": overlay,
        "august_report_only": aug_summary,
        "guardrail": "Frozen A5.11 label at every hourly state; no tuning; August report-only; live BBC untouched.",
    }

    # Compact execution-aligned dataset keeps locked features plus outcomes.
    keep = ["decision_t_utc", *FEATURES, "a511_pnl", "win", "parent_pnl", "a52_act", "fastmr_act", "recovery"]
    labeled[keep].to_csv(OUT / "g4_pooled_execution_labels.csv", index=False)
    wf.to_csv(OUT / "g4_pooled_walkforward_predictions.csv", index=False)
    td.to_csv(OUT / "g4_tuesday_overlay.csv", index=False)
    aug.to_csv(OUT / "g4_august_tuesday.csv", index=False)
    (OUT / "g4_summary.json").write_text(json.dumps(overall, indent=2, default=str))
    (OUT / "g4_final_model_state.json").write_text(json.dumps(state, indent=2, default=str))

    def pct(v):
        return "-" if v is None else f"{100*v:.2f}%"

    pm = pooled["model"]
    pb = pooled["baseline"]
    tb = overlay["baseline"]
    tg = overlay["gated"]
    lines = [
        "# BTC Global/Pooled Regime Engine — G4 Execution Compatibility",
        "",
        f"**Status: {overall['status']}**",
        "",
        "Research only; live BBC untouched.",
        "",
        "## Mandatory A5.11 parity",
        f"- N: **{parity['summary']['n']}**",
        f"- Wins: **{parity['summary']['wins']}**",
        f"- PnL: **${parity['summary']['pnl']:+.6f}**",
        f"- A5.2 actions: **{parity['summary']['a52_actions']}**",
        f"- FastMR actions: **{parity['summary']['fastmr_actions']}**",
        f"- Recoveries: **{parity['summary']['recoveries']}**",
        f"- Max trade-level PnL delta vs canonical: **{parity['summary']['max_abs_trade_pnl_delta_vs_canonical']:.12g}**",
        f"- Verdict: **{'PASS' if parity['pass'] else 'FAIL'}**",
        "",
        "## Pooled frozen-A5.11 labels",
        f"- Hourly states: **{overall['pooled_label']['n']:,}**",
        f"- WIN rate: **{pct(overall['pooled_label']['win_rate'])}**",
        f"- Aggregate hypothetical PnL: **${overall['pooled_label']['pnl']:+.2f}**",
        "",
        "## Embargoed pooled walk-forward",
        f"- Pseudo-OOS states: **{pm['n']:,}**",
        f"- Unconditional WIN rate: **{pct(pm['win_rate'])}**",
        f"- Accuracy: **{pct(pm['accuracy'])}** (prior {pct(pb['accuracy'])})",
        f"- Log loss: **{pm['log_loss']:.6f}** (prior {pb['log_loss']:.6f})",
        f"- Brier: **{pm['brier']:.6f}** (prior {pb['brier']:.6f})",
        f"- ROC AUC: **{pm['auc']:.4f}**",
        f"- p>=0.50 TRADE coverage: **{pct(pm['trade_coverage'])}**",
        f"- WIN rate among predicted TRADE: **{pct(pm['trade_win_rate'])}**",
        f"- WIN-rate enrichment: **{pooled['wr_enrichment_pp']:+.2f} pp**",
        "",
        "### Pooled acceptance gate",
    ]
    for name, ok in pooled["acceptance_checks"].items():
        lines.append(f"- {'PASS' if ok else 'FAIL'} — `{name}`")
    lines += [
        "",
        "### Four chronological pooled blocks",
        "| Block | Dates | Model LL | Prior LL | Improved | Model Brier | Prior Brier |",
        "|---:|---|---:|---:|---|---:|---:|",
    ]
    for b in pooled["blocks"]:
        lines.append(f"| {b['block']} | {b['start']} → {b['end']} | {b['model_log_loss']:.5f} | {b['baseline_log_loss']:.5f} | {'YES' if b['logloss_improved'] else 'NO'} | {b['model_brier']:.5f} | {b['baseline_brier']:.5f} |")

    lines += [
        "",
        "## Frozen Tuesday A5.11 overlay",
        f"- Opportunities: **{tb['opportunities']}**",
        f"- Always: WR **{pct(tb['trade_wr'])}**, PnL **${tb['pnl']:+.2f}**, exp/oppty **${tb['exp_per_opportunity']:+.4f}**, PF **{tb['pf']:.3f}**, DD **${tb['max_dd']:.2f}**",
        f"- G4 gate: {tg['trades']} trades / {tg['waits']} waits ({pct(tg['coverage'])}), WR **{pct(tg['trade_wr'])}**, PnL **${tg['pnl']:+.2f}**, exp/oppty **${tg['exp_per_opportunity']:+.4f}**, PF **{tg['pf']:.3f}**, DD **${tg['max_dd']:.2f}**",
        f"- PnL delta: **${tg['pnl'] - tb['pnl']:+.2f}**",
        "",
        "### Tuesday shadow promotion gate",
    ]
    for name, ok in overlay["promotion_checks"].items():
        lines.append(f"- {'PASS' if ok else 'FAIL'} — `{name}`")
    lines += [
        "",
        "### Tuesday chronological blocks",
        "| Block | Dates | Baseline PnL | G4 PnL | Delta |",
        "|---:|---|---:|---:|---:|",
    ]
    for b in overlay["blocks"]:
        lines.append(f"| {b['block']} | {b['start']} → {b['end']} | ${b['baseline']['pnl']:+.2f} | ${b['gated']['pnl']:+.2f} | ${b['pnl_delta']:+.2f} |")

    lines += [
        "",
        "## August 2026 — report only",
        "| Date WIB | p(WIN) | Decision | A5.11 PnL |",
        "|---|---:|---|---:|",
    ]
    for r in aug.to_dict(orient="records"):
        lines.append(f"| {r['date_wib']} | {100*r['p_win']:.1f}% | {'TRADE' if r['trade'] else 'WAIT'} | ${r['a511_pnl']:+.2f} |")
    lines += [
        "",
        f"August always-trade: **${aug_summary['always_trade_pnl']:+.2f}**; G4 gated: **${aug_summary['gated_pnl']:+.2f}**.",
        "",
        f"**Pooled G4 gate: {'PASS' if pooled['pass'] else 'FAIL'}. Tuesday shadow gate: {'PASS' if overlay['shadow_candidate_pass'] else 'FAIL'}.**",
        "",
        "No live BBC changes were made.",
    ]
    (OUT / "BTC_GLOBAL_REGIME_G4_RESULT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(overall, indent=2, default=str))


if __name__ == "__main__":
    main()
