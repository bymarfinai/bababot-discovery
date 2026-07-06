"""
mode3_eval_predictor.py
========================

Isolate predictor evaluation dari trading logic. 
Ukur SEHARUSNYA predictor Mode 3 kasih arah yang bener atau nggak,
TANPA simulasi trade, TANPA SL/TP, TANPA fee.

Output: accuracy per confidence bucket, per direction, per pair.

Endpoint:
  POST /mode3/eval-predictor
  Body:
    {
      "symbol": "DOGEUSDT",
      "timeframe": "15m",
      "days": 1825,
      "lookforward": 8,
      "move_threshold": 0.004
    }
"""

from __future__ import annotations
import os, time, gc
import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from mode3_drc import (
    DRCConfig, KNN_FEATURES,
    load_klines, compute_btc_returns,
    build_features, normalize_features,
    compute_forward_labels, ensemble_vote,
)
try:
    from mode3_drc import build_pair_context
    _HAS_CTX = True
except ImportError:
    _HAS_CTX = False

try:
    from mode3_drc import _KDTREE_AVAILABLE
    if _KDTREE_AVAILABLE:
        from scipy.spatial import cKDTree
except ImportError:
    _KDTREE_AVAILABLE = False


DB_PATH = os.environ.get("DB_PATH", "market_data.db")

router = APIRouter(prefix="/mode3", tags=["mode3-eval"])


class EvalRequest(BaseModel):
    symbol: str = "DOGEUSDT"
    timeframe: str = "15m"
    days: int = 1825
    lookforward: int = 8              # candles ahead untuk cek outcome
    move_threshold: float = 0.004     # 0.4% move minimum untuk label BULL/BEAR
    knn_k: int = 50
    knn_warmup: int = 5000
    sample_stride: int = 1            # Setiap N candle di-eval (1=semua, 4=setiap 4 candle)


# ═══════════════════════════════════════════════════════════════
# BUCKETING & ACCURACY MATH
# ═══════════════════════════════════════════════════════════════

CONFIDENCE_BUCKETS = [
    (0.33, 0.45, "0.33-0.45 (near-random)"),
    (0.45, 0.55, "0.45-0.55 (weak signal)"),
    (0.55, 0.65, "0.55-0.65 (moderate)"),
    (0.65, 0.75, "0.65-0.75 (strong)"),
    (0.75, 0.85, "0.75-0.85 (very strong)"),
    (0.85, 1.01, "0.85+ (extreme)"),
]


def _bucket_accuracy(p_bull_arr, p_bear_arr, labels_arr, min_samples=10):
    """
    Given arrays of P(BULL), P(BEAR) and actual labels (+1/-1/0),
    return accuracy per confidence bucket.
    
    Accuracy formula:
      - Kalau confidence P(BULL) > P(BEAR): predicted = LONG
        actual match: label == +1 → correct
      - Kalau confidence P(BEAR) > P(BULL): predicted = SHORT
        actual match: label == -1 → correct
    
    We measure at MAX(P_BULL, P_BEAR) — sisi predictor yang lebih percaya diri.
    """
    n = len(p_bull_arr)
    max_conf = np.maximum(p_bull_arr, p_bear_arr)
    direction = np.where(p_bull_arr > p_bear_arr, 1, -1)  # predicted direction
    
    results = []
    for lo, hi, label in CONFIDENCE_BUCKETS:
        mask = (max_conf >= lo) & (max_conf < hi)
        n_bucket = int(mask.sum())
        if n_bucket < min_samples:
            results.append({
                "range": label,
                "n": n_bucket,
                "accuracy": None,
                "acc_bull_side": None,
                "acc_bear_side": None,
                "sideways_ratio": None,
                "note": f"insufficient samples (< {min_samples})"
            })
            continue
        
        pred_dir = direction[mask]
        actual = labels_arr[mask]
        
        # Overall directional accuracy (ignoring sideways in denom)
        directional_mask = actual != 0
        correct = ((pred_dir == 1) & (actual == 1)) | ((pred_dir == -1) & (actual == -1))
        
        n_bull_predictions = int((pred_dir == 1).sum())
        n_bear_predictions = int((pred_dir == -1).sum())
        
        n_bull_correct = int(((pred_dir == 1) & (actual == 1)).sum())
        n_bear_correct = int(((pred_dir == -1) & (actual == -1)).sum())
        
        n_sideways = int((actual == 0).sum())
        
        n_directional = int(directional_mask.sum())
        n_correct = int(correct.sum())
        
        overall_acc = round(n_correct / n_directional * 100, 2) if n_directional > 0 else None
        bull_acc = round(n_bull_correct / n_bull_predictions * 100, 2) if n_bull_predictions > 0 else None
        bear_acc = round(n_bear_correct / n_bear_predictions * 100, 2) if n_bear_predictions > 0 else None
        
        results.append({
            "range": label,
            "n": n_bucket,
            "n_directional": n_directional,
            "n_bull_pred": n_bull_predictions,
            "n_bear_pred": n_bear_predictions,
            "n_sideways_actual": n_sideways,
            "accuracy_overall": overall_acc,
            "acc_bull_side": bull_acc,
            "acc_bear_side": bear_acc,
            "sideways_ratio": round(n_sideways / n_bucket * 100, 2),
        })
    
    return results


def _counter_trend_accuracy(p_bull_arr, p_bear_arr, labels_arr, min_samples=10):
    """
    Same as bucket_accuracy but INVERT direction.
    Predicted LONG → we test if going SHORT would have won.
    """
    n = len(p_bull_arr)
    max_conf = np.maximum(p_bull_arr, p_bear_arr)
    # Inverted direction — kalau bull confidence tinggi, kita test SHORT (bet reversal)
    direction = np.where(p_bull_arr > p_bear_arr, -1, 1)
    
    results = []
    for lo, hi, label in CONFIDENCE_BUCKETS:
        mask = (max_conf >= lo) & (max_conf < hi)
        n_bucket = int(mask.sum())
        if n_bucket < min_samples:
            results.append({
                "range": label,
                "n": n_bucket,
                "counter_trend_accuracy": None,
                "note": "insufficient"
            })
            continue
        
        pred_dir = direction[mask]
        actual = labels_arr[mask]
        directional_mask = actual != 0
        correct = ((pred_dir == 1) & (actual == 1)) | ((pred_dir == -1) & (actual == -1))
        n_directional = int(directional_mask.sum())
        n_correct = int(correct.sum())
        
        results.append({
            "range": label,
            "n": n_bucket,
            "counter_trend_accuracy": round(n_correct / n_directional * 100, 2) if n_directional > 0 else None,
        })
    
    return results


# ═══════════════════════════════════════════════════════════════
# MAIN EVAL ENDPOINT
# ═══════════════════════════════════════════════════════════════

@router.post("/eval-predictor")
def eval_predictor(req: EvalRequest):
    """
    Evaluate predictor accuracy WITHOUT trading logic.
    Returns accuracy per confidence bucket for:
      - Predictor A (KNN) standalone
      - Predictor B (Ensemble) standalone
      - Joint A AND B agree
      - Counter-trend variant (invert direction)
    """
    t0 = time.time()
    
    # Load data
    try:
        data = load_klines(DB_PATH, req.symbol, req.timeframe, days=req.days)
    except Exception as e:
        raise HTTPException(404, f"No data: {e}")
    
    if req.symbol != "BTCUSDT":
        btc_r = compute_btc_returns(DB_PATH, req.timeframe)
    else:
        btc_r = None
    
    n = len(data['close'])
    if n < req.knn_warmup + req.lookforward + 100:
        raise HTTPException(400, f"Not enough data: {n} candles, need > {req.knn_warmup + req.lookforward + 100}")
    
    # Build features + labels once
    feats = build_features(data)
    labels = compute_forward_labels(
        data['close'], data['high'], data['low'],
        req.lookforward, req.move_threshold
    )
    feat_mat, _, _ = normalize_features(feats, KNN_FEATURES)
    
    # Build KDTree for KNN
    tree = None
    if _KDTREE_AVAILABLE:
        tree = cKDTree(feat_mat, leafsize=32, balanced_tree=True)
    
    # Iterate — collect predictions per candle
    p_bull_a_list = []
    p_bear_a_list = []
    p_bull_b_list = []
    p_bear_b_list = []
    label_list = []
    n_bull_votes_list = []
    n_bear_votes_list = []
    
    max_iter_end = n - req.lookforward
    
    for i in range(req.knn_warmup, max_iter_end, req.sample_stride):
        if np.any(np.isnan(feat_mat[i])):
            continue
        if np.isnan(feats['atr14'][i]) or feats['atr14'][i] <= 0:
            continue
        
        max_hist = i - req.lookforward
        if max_hist < req.knn_warmup:
            continue
        
        # KNN prediction
        if tree is not None:
            query_k = min(req.knn_k * 4, tree.n)
            dists, idxs = tree.query(feat_mat[i], k=query_k)
            valid_idxs = idxs[idxs < max_hist]
            if len(valid_idxs) < req.knn_k:
                # Fallback brute force
                diff = feat_mat[:max_hist] - feat_mat[i][None, :]
                dist = np.sqrt(np.sum(diff * diff, axis=1))
                idx = np.argpartition(dist, req.knn_k)[:req.knn_k]
            else:
                idx = valid_idxs[:req.knn_k]
        else:
            diff = feat_mat[:max_hist] - feat_mat[i][None, :]
            dist = np.sqrt(np.sum(diff * diff, axis=1))
            idx = np.argpartition(dist, req.knn_k)[:req.knn_k]
        
        lbls = labels[idx]
        n_bull = int(np.sum(lbls == 1))
        n_bear = int(np.sum(lbls == -1))
        p_bull_a = n_bull / req.knn_k
        p_bear_a = n_bear / req.knn_k
        
        # Ensemble prediction
        p_bull_b, p_bear_b, _, votes, nbv, nsv = ensemble_vote(
            i, feats, data['close'], btc_returns=btc_r
        )
        
        p_bull_a_list.append(p_bull_a)
        p_bear_a_list.append(p_bear_a)
        p_bull_b_list.append(p_bull_b)
        p_bear_b_list.append(p_bear_b)
        label_list.append(labels[i])
        n_bull_votes_list.append(nbv)
        n_bear_votes_list.append(nsv)
    
    # Convert to arrays
    pa_bull = np.array(p_bull_a_list)
    pa_bear = np.array(p_bear_a_list)
    pb_bull = np.array(p_bull_b_list)
    pb_bear = np.array(p_bear_b_list)
    lbls_arr = np.array(label_list, dtype=np.int8)
    n_total = len(lbls_arr)
    
    # Calculate accuracy per predictor
    acc_a = _bucket_accuracy(pa_bull, pa_bear, lbls_arr)
    acc_b = _bucket_accuracy(pb_bull, pb_bear, lbls_arr)
    
    # Joint: A and B agree — take AVG conf when they agree, mask when disagree
    max_a = np.maximum(pa_bull, pa_bear)
    max_b = np.maximum(pb_bull, pb_bear)
    dir_a = np.where(pa_bull > pa_bear, 1, -1)
    dir_b = np.where(pb_bull > pb_bear, 1, -1)
    agree_mask = dir_a == dir_b
    
    joint_bull = np.where(agree_mask & (dir_a == 1), (pa_bull + pb_bull) / 2, 0)
    joint_bear = np.where(agree_mask & (dir_a == -1), (pa_bear + pb_bear) / 2, 0)
    acc_joint = _bucket_accuracy(joint_bull, joint_bear, lbls_arr)
    
    # Counter-trend for A (bet on reversal)
    acc_a_counter = _counter_trend_accuracy(pa_bull, pa_bear, lbls_arr)
    acc_b_counter = _counter_trend_accuracy(pb_bull, pb_bear, lbls_arr)
    
    # Baseline: raw label distribution
    baseline = {
        "total_samples": int(n_total),
        "pct_bull_label": round((lbls_arr == 1).sum() / n_total * 100, 2),
        "pct_bear_label": round((lbls_arr == -1).sum() / n_total * 100, 2),
        "pct_sideways_label": round((lbls_arr == 0).sum() / n_total * 100, 2),
    }
    
    # Cleanup
    del feats, feat_mat, tree
    gc.collect()
    
    runtime = round(time.time() - t0, 1)
    
    return {
        "ok": True,
        "symbol": req.symbol,
        "timeframe": req.timeframe,
        "days": req.days,
        "lookforward": req.lookforward,
        "move_threshold_pct": req.move_threshold * 100,
        "sample_stride": req.sample_stride,
        "runtime_sec": runtime,
        "baseline_label_distribution": baseline,
        "predictor_A_knn": {
            "description": "KNN 50-nearest historical analog",
            "buckets": acc_a,
            "counter_trend": acc_a_counter,
        },
        "predictor_B_ensemble": {
            "description": "7-model weighted voting ensemble",
            "buckets": acc_b,
            "counter_trend": acc_b_counter,
        },
        "joint_A_AND_B_agree": {
            "description": "Both A and B must agree direction; conf = avg",
            "buckets": acc_joint,
        },
        "interpretation_guide": {
            "random_baseline": "50%",
            "meaningful_edge": "≥ 55% at any bucket",
            "strong_edge": "≥ 60% at high-confidence bucket (0.65+)",
            "counter_trend_signal": "counter_trend > overall accuracy → predictor arah kebalik → flip direction untuk profit",
        },
    }


# ═══════════════════════════════════════════════════════════════
# HEALTH CHECK for this router
# ═══════════════════════════════════════════════════════════════

@router.get("/eval-predictor/health")
def eval_health():
    return {
        "ok": True,
        "module": "eval_predictor",
        "version": "1.0",
        "kdtree_available": _KDTREE_AVAILABLE,
        "buckets": [b[2] for b in CONFIDENCE_BUCKETS],
    }
