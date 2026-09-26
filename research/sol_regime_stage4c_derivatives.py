"""SOL Regime Stage 4C — derivatives-positioning robustness audit.

Research-only evaluator for the compact Stage 4C matrices committed with this
branch. It intentionally does NOT retune the frozen Stage 4 Bull head.

Inputs:
- research/stage4c_price_candidates.csv
- research/stage4c_premium_compact.csv
- research/stage4c_funding_compact.csv

The historical OI endpoint is NOT used for model selection because Binance's
REST endpoint only exposes the latest ~30 days. OI is treated separately as an
exploratory recent-OOS diagnostic.
"""

from __future__ import annotations
import csv
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
FUNDING = ROOT / "research" / "stage4c_funding_compact.csv"

GLOBAL = {
    "DEV": {"n": 9480, "bear": 1345},
    "VAL": {"n": 8736, "bear": 1368},
    "OOS": {"n": 6396, "bear": 717},
}

# DEV 75th-percentile magnitude of funding deterioration.
# Selected from the DEV shortlist; 2025 used only as validation.
FUNDING_DROP_Q75 = -0.000038280000000000006

QUARTERS = {
    "2025 Q1": (1735689600000, 1743465600000, 2160, 427),
    "2025 Q2": (1743465600000, 1751328000000, 2184, 294),
    "2025 Q3": (1751328000000, 1759276800000, 2208, 279),
    "2025 Q4": (1759276800000, 1767139200000, 2184, 368),
    "2026 Q1": (1767225600000, 1775001600000, 2160, 348),
    "2026 Q2": (1775001600000, 1782864000000, 2184, 237),
    "2026 Q3": (1782864000000, 1790337600000, 2052, 132),
}

def load_rows():
    with FUNDING.open(newline="", encoding="utf-8") as f:
        out = []
        for r in csv.DictReader(f):
            for k in ("t","v1","broad","bull","fund","fund_delta","fund_mean3","fund_z30","fund_pos6","fund_pct90"):
                r[k] = float(r[k])
            r["t"] = int(r["t"])
            out.append(r)
        return out

def selected(r, threshold=FUNDING_DROP_Q75):
    # Stage 4B broad exhaustion price precursor + derivatives deterioration.
    # Frozen Stage 4 Bull conflict is rejected to TRANSITION.
    return bool(r["broad"]) and r["fund_delta"] <= threshold and not bool(r["bull"])

def metric(rows, period, threshold=FUNDING_DROP_Q75):
    q = [r for r in rows if r["period"] == period and selected(r, threshold)]
    tp = sum(r["gt"] == "BEAR" for r in q)
    base = GLOBAL[period]["bear"] / GLOBAL[period]["n"]
    precision = tp / len(q) if q else 0.0
    return {
        "n": len(q),
        "tp": tp,
        "precision": precision,
        "recall": tp / GLOBAL[period]["bear"],
        "lift": precision / base if base else 0.0,
    }

def quarter_metric(rows, name, threshold=FUNDING_DROP_Q75):
    start,end,n,bear = QUARTERS[name]
    q = [r for r in rows if start <= r["t"] < end and selected(r, threshold)]
    tp = sum(r["gt"] == "BEAR" for r in q)
    precision = tp / len(q) if q else 0.0
    base = bear / n
    return {
        "n": len(q),
        "tp": tp,
        "precision": precision,
        "recall": tp / bear,
        "lift": precision / base if base else 0.0,
    }

def run():
    rows = load_rows()
    return {
        "candidate": {
            "price_gate": "ret4>=1.053869 & accel4v12>=0.877085 & distLow8>=3.046480",
            "derivative_gate": f"fund_delta<={FUNDING_DROP_Q75}",
            "conflict": "frozen Stage4 Bull conflict -> TRANSITION",
        },
        "annual": {p: metric(rows,p) for p in ("DEV","VAL","OOS")},
        "quarters": {q: quarter_metric(rows,q) for q in QUARTERS},
        "verdict": "REJECT for promotion: annual lift improves, but 2025 Q1/Q2 fail the >1x quarter robustness gate.",
    }

if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2))
