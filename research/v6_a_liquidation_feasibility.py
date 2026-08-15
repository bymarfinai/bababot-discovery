#!/usr/bin/env python3
"""V6-A — bounded historical forced-liquidation data feasibility probe.

Research-only. No strategy/trading/live logic. Validates Tardis Binance USD-M
forceOrder coverage, raw liquidation CSV schema and whether full arbitrary-date
history needs entitlement. Sample reads are intentionally bounded.
"""
import csv
import gzip
import io
import json
import urllib.error
import urllib.request

PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
META_URL = "https://api.tardis.dev/v1/exchanges/binance-futures"
BASE = "https://datasets.tardis.dev/v1/binance-futures/liquidations"
SAMPLE_DATE = "2024/01/01"
NON_SAMPLE_DATE = "2023/12/18"
EXPECTED = {"exchange", "symbol", "timestamp", "local_timestamp", "id", "side", "price", "amount"}
UA = {"User-Agent": "bababot-v6-feasibility/1.1"}


def get_small(url, limit=4096, timeout=12):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(limit), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(limit), dict(e.headers)
    except Exception as e:
        return None, str(e).encode(), {}


def get_json(url, timeout=12):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read(512).decode("utf-8", "replace")}
    except Exception as e:
        return None, {"error": str(e)}


def sample_csv(url, max_rows=500, timeout=15):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            gz = gzip.GzipFile(fileobj=resp)
            txt = io.TextIOWrapper(gz, encoding="utf-8-sig", newline="")
            reader = csv.DictReader(txt)
            fields = set(reader.fieldnames or [])
            rows = []
            for i, row in enumerate(reader):
                rows.append(row)
                if i + 1 >= max_rows:
                    break
            side_counts = {}
            symbols = {}
            for r in rows:
                s = r.get("side")
                if s: side_counts[s] = side_counts.get(s, 0) + 1
                p = r.get("symbol")
                if p: symbols[p] = symbols.get(p, 0) + 1
            return {
                "http_status": resp.status,
                "header": sorted(fields),
                "expected_schema_ok": EXPECTED.issubset(fields),
                "rows_sampled": len(rows),
                "side_counts_sample": side_counts,
                "symbol_counts_sample": symbols,
                "first_row": rows[0] if rows else None,
            }
    except urllib.error.HTTPError as e:
        return {"http_status": e.code, "error": e.read(256).decode("utf-8", "replace")}
    except Exception as e:
        return {"http_status": None, "error": str(e)}


def main():
    out = {"phase":"V6-A","status":"HISTORICAL_LIQUIDATION_FEASIBILITY_PROBE",
           "targets":PAIRS,"metadata":{},"public_samples":{},"non_sample_probe":{},"errors":{}}

    status, meta = get_json(META_URL)
    out["metadata"]["http_status"] = status
    if status == 200:
        chans = meta.get("availableChannels") or []
        syms = meta.get("availableSymbols") or []
        sm = {str(x.get("id", "")).upper(): x for x in syms if isinstance(x, dict)}
        out["metadata"].update({
            "exchange_id": meta.get("id"), "available_since": meta.get("availableSince"),
            "force_order_channel": "forceOrder" in chans,
            "target_symbols": {p:{"present":p in sm,"available_since":sm.get(p,{}).get("availableSince"),
                                  "available_to":sm.get(p,{}).get("availableTo"),"type":sm.get(p,{}).get("type")}
                               for p in PAIRS},
            "incident_reports_n": len(meta.get("incidentReports") or []),
        })
    else:
        out["errors"]["metadata"] = meta

    for p in PAIRS:
        out["public_samples"][p] = sample_csv(f"{BASE}/{SAMPLE_DATE}/{p}.csv.gz")

    for p in PAIRS:
        status, body, _ = get_small(f"{BASE}/{NON_SAMPLE_DATE}/{p}.csv.gz", limit=256)
        out["non_sample_probe"][p] = {
            "http_status":status,
            "anonymous_full_history_available":status in (200,206),
            "body_preview":None if status in (200,206) else body.decode("utf-8","replace")[:160],
        }

    meta_ok = bool(out["metadata"].get("force_order_channel")) and all(
        x.get("present") for x in out["metadata"].get("target_symbols",{}).values())
    sample_ok = all(x.get("http_status")==200 and x.get("expected_schema_ok")
                    for x in out["public_samples"].values())
    anon_full = all(x.get("anonymous_full_history_available")
                    for x in out["non_sample_probe"].values())
    out["verdict"] = {
        "raw_forceorder_path_technically_feasible": bool(meta_ok and sample_ok),
        "971d_anonymous_download_feasible": bool(meta_ok and sample_ok and anon_full),
        "requires_historical_entitlement_for_971d": bool(meta_ok and sample_ok and not anon_full),
        "ready_for_v6_b_backtest_now": bool(meta_ok and sample_ok and anon_full),
        "next_required_input": None if anon_full else "Tardis historical-data entitlement/API key or purchased CSV access",
    }
    print("V6_A_RESULT", json.dumps(out, separators=(",",":")))

if __name__ == "__main__":
    main()
