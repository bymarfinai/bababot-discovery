#!/usr/bin/env python3
"""V6-A — historical forced-liquidation data feasibility probe.

Research-only. No strategy, no trading logic, no live integration.

Purpose:
- verify Tardis Binance USD-M metadata exposes the forceOrder channel;
- verify target symbols are covered;
- verify public first-day-of-month liquidation CSV samples are downloadable and
  contain the expected raw liquidation schema;
- verify an arbitrary non-sample historical date is not anonymously available,
  so full 971d acquisition requires a paid historical entitlement/API key.

This probe does not claim that Binance's forceOrder stream contains every
individual liquidation. It only validates the exchange-published stream that
Tardis records.
"""
import csv
import gzip
import io
import json
import urllib.error
import urllib.request

PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
META_URL = "https://api.tardis.dev/v1/exchanges/binance-futures"
DATASET_BASE = "https://datasets.tardis.dev/v1/binance-futures/liquidations"
SAMPLE_DATE = "2024/01/01"       # first day of month; documented public sample pattern
NON_SAMPLE_DATE = "2023/12/18"   # inside the intended ~971d research horizon
EXPECTED = {"exchange", "symbol", "timestamp", "local_timestamp", "id", "side", "price", "amount"}


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "bababot-v6-feasibility/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)
    except Exception as e:
        return None, str(e).encode(), {}


def parse_sample(raw):
    text = gzip.decompress(raw).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    header = set(reader.fieldnames or [])
    pair_counts = {}
    sides = {}
    for r in rows:
        sym = r.get("symbol")
        if sym:
            pair_counts[sym] = pair_counts.get(sym, 0) + 1
        side = r.get("side")
        if side:
            sides[side] = sides.get(side, 0) + 1
    return {
        "rows": len(rows),
        "header": sorted(header),
        "expected_schema_ok": EXPECTED.issubset(header),
        "pair_counts": pair_counts,
        "side_counts": sides,
        "first_row": rows[0] if rows else None,
    }


def main():
    out = {
        "phase": "V6-A",
        "status": "HISTORICAL_LIQUIDATION_FEASIBILITY_PROBE",
        "targets": PAIRS,
        "metadata": {},
        "public_samples": {},
        "non_sample_probe": {},
        "errors": {},
    }

    # 1) Public exchange metadata.
    status, raw, _ = fetch(META_URL)
    out["metadata"]["http_status"] = status
    if status == 200:
        try:
            meta = json.loads(raw.decode("utf-8"))
            chans = meta.get("availableChannels") or []
            syms = meta.get("availableSymbols") or []
            sym_map = {str(s.get("id", "")).upper(): s for s in syms if isinstance(s, dict)}
            out["metadata"].update({
                "exchange_id": meta.get("id"),
                "available_since": meta.get("availableSince"),
                "force_order_channel": "forceOrder" in chans,
                "target_symbols": {
                    p: {
                        "present": p in sym_map,
                        "available_since": sym_map.get(p, {}).get("availableSince"),
                        "available_to": sym_map.get(p, {}).get("availableTo"),
                        "type": sym_map.get(p, {}).get("type"),
                    } for p in PAIRS
                },
                "incident_reports_n": len(meta.get("incidentReports") or []),
            })
        except Exception as e:
            out["errors"]["metadata_parse"] = str(e)
    else:
        out["errors"]["metadata_fetch"] = raw[:300].decode("utf-8", "replace")

    # 2) Documented free samples: first day of a month.
    for p in PAIRS:
        url = f"{DATASET_BASE}/{SAMPLE_DATE}/{p}.csv.gz"
        status, raw, headers = fetch(url)
        rec = {"http_status": status, "bytes": len(raw) if raw else 0}
        if status == 200:
            try:
                rec.update(parse_sample(raw))
            except Exception as e:
                rec["parse_error"] = str(e)
        else:
            rec["body_preview"] = raw[:200].decode("utf-8", "replace")
        out["public_samples"][p] = rec

    # 3) Anonymous non-sample historical date. We expect entitlement failure.
    for p in PAIRS:
        url = f"{DATASET_BASE}/{NON_SAMPLE_DATE}/{p}.csv.gz"
        status, raw, _ = fetch(url)
        out["non_sample_probe"][p] = {
            "http_status": status,
            "anonymous_full_history_available": status == 200,
            "body_preview": None if status == 200 else raw[:160].decode("utf-8", "replace"),
        }

    meta_ok = bool(out["metadata"].get("force_order_channel")) and all(
        x.get("present") for x in out["metadata"].get("target_symbols", {}).values()
    )
    sample_ok = all(
        x.get("http_status") == 200 and x.get("expected_schema_ok")
        for x in out["public_samples"].values()
    )
    anon_full = any(x.get("anonymous_full_history_available") for x in out["non_sample_probe"].values())

    out["verdict"] = {
        "raw_forceorder_path_technically_feasible": bool(meta_ok and sample_ok),
        "971d_anonymous_download_feasible": bool(meta_ok and sample_ok and anon_full),
        "requires_historical_entitlement_for_971d": bool(meta_ok and sample_ok and not anon_full),
        "ready_for_v6_b_backtest_now": False,
        "why_not_ready": (
            "Full 971d liquidation history requires a Tardis historical-data entitlement/API key; "
            "this probe only validates public metadata and documented monthly samples."
            if meta_ok and sample_ok and not anon_full else
            "Public metadata/sample validation did not fully pass; inspect probe output before acquisition."
        ),
    }
    print("V6_A_RESULT", json.dumps(out, separators=(",", ":")))


if __name__ == "__main__":
    main()
