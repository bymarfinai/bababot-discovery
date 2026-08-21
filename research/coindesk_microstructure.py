#!/usr/bin/env python3
"""CoinDesk true-microstructure adapter for BabaBot discovery research.

Research rule: this module NEVER falls back to OHLC/kline proxies when L2,
tick-trade, or OI data are unavailable. Missing entitlement/coverage must be
reported by the caller as BLOCKED_DATA_ACCESS / BLOCKED_DATA_COVERAGE.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
import socket
import time
from typing import Any, Iterable

import numpy as np
import pandas as pd
import requests

REST_BASE = os.getenv("COINDESK_DATA_API_BASE", "https://data-api.coindesk.com").rstrip("/")
WS_BASE = os.getenv("COINDESK_STREAMER_WS_URL", "wss://data-streamer.coindesk.com/")
DEFAULT_MARKET = os.getenv("COINDESK_FUTURES_MARKET", "binance")
DEFAULT_INSTRUMENT = os.getenv("COINDESK_FUTURES_INSTRUMENT", "BTC-USDT-VANILLA-PERPETUAL")
REPLAY_TYPE = "futures_v1_orderbook_replay_l2_updates"


class CoinDeskAccessError(RuntimeError):
    pass


class CoinDeskCoverageError(RuntimeError):
    pass


def _unix(v: Any) -> int:
    return int(pd.Timestamp(v).timestamp())


def _float(v: Any, default: float = np.nan) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def _flatten_ws_payload(msg: Any) -> list[dict[str, Any]]:
    if isinstance(msg, list):
        return [x for x in msg if isinstance(x, dict)]
    if not isinstance(msg, dict):
        return []
    data = msg.get("Data")
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        return [data]
    return [msg]


@dataclass
class CoinDeskMicrostructureClient:
    api_key: str
    market: str = DEFAULT_MARKET
    instrument: str = DEFAULT_INSTRUMENT
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "CoinDeskMicrostructureClient":
        key = os.getenv("COINDESK_API_KEY", "").strip()
        if not key:
            raise CoinDeskAccessError("COINDESK_API_KEY is not configured")
        return cls(api_key=key)

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Apikey {self.api_key}",
            "User-Agent": "bababot-discovery-microstructure/1.0",
        }

    def _get(self, path: str, params: dict[str, Any]) -> Any:
        url = f"{REST_BASE}{path}"
        r = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
        if r.status_code in (401, 403):
            raise CoinDeskAccessError(f"CoinDesk access denied ({r.status_code}) for {path}")
        if r.status_code == 404:
            raise CoinDeskCoverageError(f"CoinDesk returned 404 for {path}: {params}")
        r.raise_for_status()
        body = r.json()
        err = body.get("Err") if isinstance(body, dict) else None
        if err and isinstance(err, dict) and err.get("message"):
            raise CoinDeskAccessError(f"CoinDesk API error: {err.get('message')}")
        return body.get("Data", body) if isinstance(body, dict) else body

    def instrument_metadata(self) -> Any:
        return self._get(
            "/futures/v1/markets/instruments",
            {
                "market": self.market,
                "instruments": self.instrument,
                "instrument_status": "ACTIVE",
            },
        )

    def _messages_by_timestamp(
        self,
        path: str,
        start_ts: int,
        end_ts: int,
        groups: str,
        max_pages: int = 1000,
    ) -> list[dict[str, Any]]:
        """Causal pagination using TIMESTAMP + CCSEQ as documented by CoinDesk."""
        out: list[dict[str, Any]] = []
        after_ts = int(start_ts)
        last_ccseq = 0
        seen: set[tuple[int, int, str]] = set()
        for _ in range(max_pages):
            data = self._get(
                path,
                {
                    "market": self.market,
                    "instrument": self.instrument,
                    "groups": groups,
                    "after_ts": after_ts,
                    "last_ccseq": last_ccseq,
                    "limit": 5000,
                    "apply_mapping": "true",
                    "skip_invalid_messages": "false",
                },
            )
            if not isinstance(data, list) or not data:
                break
            progressed = False
            max_pair = (after_ts, last_ccseq)
            for row in data:
                if not isinstance(row, dict):
                    continue
                ts = int(_float(row.get("TIMESTAMP"), -1))
                cc = int(_float(row.get("CCSEQ"), 0))
                if ts < start_ts:
                    continue
                if ts >= end_ts:
                    continue
                key = (ts, cc, str(row.get("ID", "")))
                if key not in seen:
                    seen.add(key)
                    out.append(row)
                if (ts, cc) > max_pair:
                    max_pair = (ts, cc)
                    progressed = True
            raw_last = data[-1] if isinstance(data[-1], dict) else {}
            raw_ts = int(_float(raw_last.get("TIMESTAMP"), after_ts))
            raw_cc = int(_float(raw_last.get("CCSEQ"), last_ccseq))
            if raw_ts >= end_ts:
                break
            if not progressed and (raw_ts, raw_cc) <= (after_ts, last_ccseq):
                break
            after_ts, last_ccseq = raw_ts, raw_cc
        out.sort(key=lambda r: (int(_float(r.get("TIMESTAMP"), 0)), int(_float(r.get("TIMESTAMP_NS"), 0)), int(_float(r.get("CCSEQ"), 0))))
        return out

    def trades(self, start: Any, end: Any) -> list[dict[str, Any]]:
        return self._messages_by_timestamp(
            "/futures/v2/historical/trades",
            _unix(start),
            _unix(end),
            "ID,MAPPING,TRADE,STATUS",
        )

    def open_interest(self, start: Any, end: Any) -> list[dict[str, Any]]:
        return self._messages_by_timestamp(
            "/futures/v2/historical/open-interest-messages",
            _unix(start),
            _unix(end),
            "ID,MAPPING,MESSAGE,STATUS",
        )

    def replay_l2_features(
        self,
        start: Any,
        end: Any,
        objective_level: float,
        depth: int = 100,
        idle_complete_seconds: int = 8,
        hard_timeout_seconds: int = 90,
    ) -> dict[str, Any]:
        """Replay L2 and summarize book state/dynamics without storing the full stream."""
        try:
            import websocket  # websocket-client
        except ImportError as e:
            raise RuntimeError("websocket-client is required for CoinDesk Order Book Replay") from e

        start_ts, end_ts = _unix(start), _unix(end)
        if end_ts <= start_ts:
            raise ValueError("end must be after start")
        ws = websocket.create_connection(
            WS_BASE,
            timeout=idle_complete_seconds,
            header=[f"Authorization: Apikey {self.api_key}"],
        )
        payload = {
            "action": "SUBSCRIBE",
            "type": REPLAY_TYPE,
            "market": self.market,
            "instrument": self.instrument,
            "from_ts": start_ts,
            "to_ts": end_ts,
            "depth": int(depth),
            "apply_mapping": True,
        }
        ws.send(json.dumps(payload))

        bids: dict[float, float] = {}
        asks: dict[float, float] = {}
        initial_bids: dict[float, float] | None = None
        initial_asks: dict[float, float] | None = None
        first_data_ts: int | None = None
        last_data_ts: int | None = None
        previous_ccseq: int | None = None
        ccseq_gaps = 0
        updates = 0
        snapshots = 0
        near_bp = 25.0
        dynamics = {
            "bid_added_near_level": 0.0,
            "bid_removed_near_level": 0.0,
            "ask_added_near_level": 0.0,
            "ask_removed_near_level": 0.0,
            "bid_update_count_near_level": 0,
            "ask_update_count_near_level": 0,
        }
        began = time.monotonic()
        got_data = False
        try:
            while time.monotonic() - began < hard_timeout_seconds:
                try:
                    raw = ws.recv()
                except (socket.timeout, websocket.WebSocketTimeoutException):
                    if got_data:
                        break
                    raise CoinDeskCoverageError("Order Book Replay returned no data before timeout")
                if not raw:
                    if got_data:
                        break
                    continue
                try:
                    decoded = json.loads(raw)
                except Exception:
                    continue
                for row in _flatten_ws_payload(decoded):
                    if row.get("Err"):
                        raise CoinDeskAccessError(f"Order Book Replay error: {row.get('Err')}")
                    ts = int(_float(row.get("TIMESTAMP"), -1))
                    has_snapshot = isinstance(row.get("BIDS"), list) and isinstance(row.get("ASKS"), list)
                    has_update = str(row.get("SIDE", "")).upper() in ("BID", "ASK") and row.get("PRICE") is not None
                    if not (has_snapshot or has_update):
                        msg = str(row.get("MESSAGE", "")).upper()
                        if "ERROR" in msg or "UNAUTHORIZED" in msg or "FORBIDDEN" in msg:
                            raise CoinDeskAccessError(f"Order Book Replay control message: {row}")
                        if "COMPLETE" in msg or "FINISHED" in msg:
                            return _book_result(initial_bids, initial_asks, bids, asks, dynamics, snapshots, updates, ccseq_gaps, first_data_ts, last_data_ts, objective_level)
                        continue
                    got_data = True
                    if ts >= 0:
                        first_data_ts = ts if first_data_ts is None else min(first_data_ts, ts)
                        last_data_ts = ts if last_data_ts is None else max(last_data_ts, ts)
                    cc = int(_float(row.get("CCSEQ"), 0))
                    if cc > 0:
                        if previous_ccseq is not None and cc > previous_ccseq + 1:
                            ccseq_gaps += cc - previous_ccseq - 1
                        previous_ccseq = cc
                    if has_snapshot:
                        bids = {_float(x.get("PRICE")): _float(x.get("QUANTITY"), 0.0) for x in row["BIDS"] if isinstance(x, dict) and _float(x.get("PRICE")) > 0 and _float(x.get("QUANTITY"), 0.0) >= 0}
                        asks = {_float(x.get("PRICE")): _float(x.get("QUANTITY"), 0.0) for x in row["ASKS"] if isinstance(x, dict) and _float(x.get("PRICE")) > 0 and _float(x.get("QUANTITY"), 0.0) >= 0}
                        initial_bids, initial_asks = dict(bids), dict(asks)
                        snapshots += 1
                        continue
                    side = str(row["SIDE"]).upper()
                    price = _float(row.get("PRICE"))
                    qty = max(_float(row.get("QUANTITY"), 0.0), 0.0)
                    book = bids if side == "BID" else asks
                    old = book.get(price, 0.0)
                    delta = qty - old
                    if qty <= 0:
                        book.pop(price, None)
                    else:
                        book[price] = qty
                    updates += 1
                    if objective_level > 0 and abs(price / objective_level - 1.0) * 10000.0 <= near_bp:
                        prefix = "bid" if side == "BID" else "ask"
                        dynamics[f"{prefix}_update_count_near_level"] += 1
                        if delta > 0:
                            dynamics[f"{prefix}_added_near_level"] += delta
                        elif delta < 0:
                            dynamics[f"{prefix}_removed_near_level"] += -delta
                if last_data_ts is not None and last_data_ts >= end_ts:
                    break
        finally:
            try:
                ws.close()
            except Exception:
                pass
        if not got_data or initial_bids is None or initial_asks is None:
            raise CoinDeskCoverageError(f"No usable L2 snapshot/update data for {start_ts}..{end_ts}")
        return _book_result(initial_bids, initial_asks, bids, asks, dynamics, snapshots, updates, ccseq_gaps, first_data_ts, last_data_ts, objective_level)


def _depth_features(bids: dict[float, float], asks: dict[float, float], prefix: str) -> dict[str, float]:
    if not bids or not asks:
        return {f"{prefix}_mid": np.nan, f"{prefix}_spread_bps": np.nan}
    best_bid, best_ask = max(bids), min(asks)
    mid = (best_bid + best_ask) / 2.0
    out = {f"{prefix}_mid": mid, f"{prefix}_spread_bps": (best_ask / best_bid - 1.0) * 10000.0}
    for bp in (5, 10, 25):
        b = sum(q for p, q in bids.items() if p >= mid * (1.0 - bp / 10000.0))
        a = sum(q for p, q in asks.items() if p <= mid * (1.0 + bp / 10000.0))
        den = b + a
        out[f"{prefix}_bid_depth_{bp}bps"] = b
        out[f"{prefix}_ask_depth_{bp}bps"] = a
        out[f"{prefix}_imbalance_{bp}bps"] = (b - a) / den if den > 0 else np.nan
    return out


def _near_level_depth(book: dict[float, float], level: float, bp: float = 25.0) -> float:
    if not level or level <= 0:
        return np.nan
    return sum(q for p, q in book.items() if abs(p / level - 1.0) * 10000.0 <= bp)


def _book_result(
    initial_bids: dict[float, float] | None,
    initial_asks: dict[float, float] | None,
    bids: dict[float, float],
    asks: dict[float, float],
    dynamics: dict[str, Any],
    snapshots: int,
    updates: int,
    ccseq_gaps: int,
    first_ts: int | None,
    last_ts: int | None,
    level: float,
) -> dict[str, Any]:
    ib, ia = initial_bids or {}, initial_asks or {}
    out: dict[str, Any] = {
        **_depth_features(ib, ia, "l2_start"),
        **_depth_features(bids, asks, "l2_end"),
        **dynamics,
        "l2_start_bid_near_level_25bps": _near_level_depth(ib, level),
        "l2_start_ask_near_level_25bps": _near_level_depth(ia, level),
        "l2_end_bid_near_level_25bps": _near_level_depth(bids, level),
        "l2_end_ask_near_level_25bps": _near_level_depth(asks, level),
        "l2_snapshots": snapshots,
        "l2_updates": updates,
        "l2_ccseq_gaps": ccseq_gaps,
        "l2_first_ts": first_ts,
        "l2_last_ts": last_ts,
    }
    ar = float(out["ask_removed_near_level"])
    aa = float(out["ask_added_near_level"])
    br = float(out["bid_removed_near_level"])
    ba = float(out["bid_added_near_level"])
    out["ask_replenishment_ratio_25bps"] = aa / ar if ar > 0 else (np.inf if aa > 0 else np.nan)
    out["bid_replenishment_ratio_25bps"] = ba / br if br > 0 else (np.inf if ba > 0 else np.nan)
    for bp in (5, 10, 25):
        a = out.get(f"l2_start_imbalance_{bp}bps")
        b = out.get(f"l2_end_imbalance_{bp}bps")
        out[f"l2_imbalance_change_{bp}bps"] = b - a if np.isfinite(a) and np.isfinite(b) else np.nan
    return out


def trade_flow_features(rows: Iterable[dict[str, Any]], end: Any) -> dict[str, Any]:
    end_ts = _unix(end)
    rr = list(rows)
    out: dict[str, Any] = {"trade_count_total": len(rr)}
    for minutes, label in ((60, "60m"), (15, "15m"), (5, "5m"), (1, "60s")):
        start_ts = end_ts - minutes * 60
        q = [r for r in rr if start_ts <= int(_float(r.get("TIMESTAMP"), -1)) < end_ts]
        buy_q = sell_q = buy_quote = sell_quote = 0.0
        quotes: list[float] = []
        prices: list[float] = []
        liq_quote = 0.0
        liq_n = 0
        for r in q:
            side = str(r.get("SIDE", "UNKNOWN")).upper()
            qty = max(_float(r.get("QUANTITY"), 0.0), 0.0)
            price = _float(r.get("PRICE"))
            quote = _float(r.get("QUOTE_QUANTITY"), qty * price if np.isfinite(price) else 0.0)
            if np.isfinite(price):
                prices.append(price)
            quotes.append(max(quote, 0.0))
            if side == "BUY":
                buy_q += qty; buy_quote += max(quote, 0.0)
            elif side == "SELL":
                sell_q += qty; sell_quote += max(quote, 0.0)
            if str(r.get("LIQUIDATION", "")).upper() == "YES":
                liq_n += 1; liq_quote += max(quote, 0.0)
        total_quote = buy_quote + sell_quote
        signed_quote = buy_quote - sell_quote
        out[f"trade_count_{label}"] = len(q)
        out[f"buy_quote_{label}"] = buy_quote
        out[f"sell_quote_{label}"] = sell_quote
        out[f"signed_quote_{label}"] = signed_quote
        out[f"delta_ratio_{label}"] = signed_quote / total_quote if total_quote > 0 else np.nan
        out[f"buy_base_{label}"] = buy_q
        out[f"sell_base_{label}"] = sell_q
        out[f"liquidation_count_{label}"] = liq_n
        out[f"liquidation_quote_{label}"] = liq_quote
        if prices:
            ret = prices[-1] / prices[0] - 1.0 if prices[0] else np.nan
            out[f"trade_price_ret_{label}"] = ret
            out[f"price_per_delta_efficiency_{label}"] = ret / (abs(signed_quote) / total_quote) if total_quote > 0 and abs(signed_quote) > 0 else np.nan
        else:
            out[f"trade_price_ret_{label}"] = np.nan
            out[f"price_per_delta_efficiency_{label}"] = np.nan
        if quotes:
            a = np.asarray(quotes, dtype=float)
            k = max(1, int(math.ceil(0.05 * len(a))))
            out[f"top5pct_trade_quote_share_{label}"] = float(np.sort(a)[-k:].sum() / a.sum()) if a.sum() > 0 else np.nan
        else:
            out[f"top5pct_trade_quote_share_{label}"] = np.nan
    return out


def oi_features(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    q = [r for r in rows if isinstance(r, dict)]
    q.sort(key=lambda r: (int(_float(r.get("TIMESTAMP"), 0)), int(_float(r.get("TIMESTAMP_NS"), 0)), int(_float(r.get("CCSEQ"), 0))))
    if not q:
        return {"oi_updates": 0, "oi_settlement_change": np.nan, "oi_settlement_change_pct": np.nan, "oi_quote_change": np.nan, "oi_quote_change_pct": np.nan}
    a, b = q[0], q[-1]
    s0, s1 = _float(a.get("SETTLEMENT")), _float(b.get("SETTLEMENT"))
    q0, q1 = _float(a.get("QUOTE")), _float(b.get("QUOTE"))
    return {
        "oi_updates": len(q),
        "oi_start_settlement": s0,
        "oi_end_settlement": s1,
        "oi_settlement_change": s1 - s0 if np.isfinite(s0) and np.isfinite(s1) else np.nan,
        "oi_settlement_change_pct": s1 / s0 - 1.0 if np.isfinite(s0) and np.isfinite(s1) and s0 != 0 else np.nan,
        "oi_start_quote": q0,
        "oi_end_quote": q1,
        "oi_quote_change": q1 - q0 if np.isfinite(q0) and np.isfinite(q1) else np.nan,
        "oi_quote_change_pct": q1 / q0 - 1.0 if np.isfinite(q0) and np.isfinite(q1) and q0 != 0 else np.nan,
    }
