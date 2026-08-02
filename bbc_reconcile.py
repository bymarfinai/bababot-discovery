"""
Post-restart trade reconciliation helper for BBC Live.
Fetches exchange trade history and logs any unrecorded trades to D1.

Usage: Called after phantom detection in bbc_live.py warmup sequence.
"""

from datetime import datetime, timezone, timedelta
from baret_live import _log, _send_telegram
from bbc_trade_logger import _log_trade_to_d1


def reconcile_missed_trades(client, symbols, phantom_symbols, timeframe, prefix, acct_name):
    """Check exchange trade history for trades that happened during downtime.
    
    For each symbol (especially phantoms), fetch recent fills from Binance,
    identify entry/exit pairs, and log unrecorded trades to D1.
    
    Args:
        client: ExchangeClient instance
        symbols: list of all trading symbols
        phantom_symbols: list of symbols where phantom positions were detected
        timeframe: e.g. "1h"
        prefix: log prefix string
        acct_name: account name for D1 logging
    
    Returns: number of trades reconciled
    """
    if not phantom_symbols:
        _log(f"{prefix}  ✅ No phantoms — skipping reconciliation")
        return 0
    
    _log(f"{prefix}  🔄 RECONCILIATION: checking exchange history for {len(phantom_symbols)} phantom symbol(s)...")
    
    reconciled = 0
    lookback_ms = 12 * 60 * 60 * 1000  # 12 hours
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    
    for symbol in phantom_symbols:
        try:
            # Fetch recent trades from Binance
            trades = client.api_get("/fapi/v1/userTrades", {
                "symbol": symbol,
                "startTime": now_ms - lookback_ms,
                "limit": 100,
            }, signed=True)
            
            if not isinstance(trades, list) or not trades:
                _log(f"{prefix}  📋 {symbol}: no exchange trades in last 12h")
                continue
            
            # Group trades by position: find entry fills and exit fills
            # Binance userTrades has: side, price, qty, realizedPnl, time, buyer/maker
            # realizedPnl != 0 means it's a closing trade
            
            entry_fills = []
            exit_fills = []
            
            for t in trades:
                rpnl = float(t.get("realizedPnl", 0))
                if abs(rpnl) > 0.0001:
                    exit_fills.append(t)
                else:
                    entry_fills.append(t)
            
            if not exit_fills:
                _log(f"{prefix}  📋 {symbol}: {len(trades)} fills but no exits — position may still be open elsewhere")
                continue
            
            # Reconstruct trades from fills
            # Group exit fills by time proximity (within 1 second = same exit event)
            exit_groups = []
            current_group = [exit_fills[0]]
            for i in range(1, len(exit_fills)):
                if exit_fills[i]["time"] - exit_fills[i-1]["time"] < 1000:
                    current_group.append(exit_fills[i])
                else:
                    exit_groups.append(current_group)
                    current_group = [exit_fills[i]]
            exit_groups.append(current_group)
            
            for group in exit_groups:
                # Calculate exit details
                total_qty = sum(float(t["qty"]) for t in group)
                total_rpnl = sum(float(t["realizedPnl"]) for t in group)
                avg_exit_price = sum(float(t["price"]) * float(t["qty"]) for t in group) / total_qty if total_qty > 0 else 0
                exit_time_ms = group[-1]["time"]
                exit_time = datetime.fromtimestamp(exit_time_ms / 1000, tz=timezone.utc).isoformat()
                
                # The exit side tells us the position side (exit BUY = was SHORT, exit SELL = was LONG)
                exit_side = group[0]["side"]  # BUY or SELL
                position_side = "SHORT" if exit_side == "BUY" else "LONG"
                
                # Find matching entry fills (opposite side, before exit time)
                matching_entries = [t for t in entry_fills 
                                   if t["side"] != exit_side and t["time"] < exit_time_ms]
                
                if matching_entries:
                    # Use most recent entry fills that match the quantity
                    matching_entries.sort(key=lambda t: t["time"], reverse=True)
                    entry_qty = 0
                    entry_price_sum = 0
                    entry_time_ms = matching_entries[0]["time"]
                    for t in matching_entries:
                        q = float(t["qty"])
                        entry_qty += q
                        entry_price_sum += float(t["price"]) * q
                        entry_time_ms = min(entry_time_ms, t["time"])
                        if entry_qty >= total_qty * 0.95:
                            break
                    avg_entry_price = entry_price_sum / entry_qty if entry_qty > 0 else avg_exit_price
                    entry_time = datetime.fromtimestamp(entry_time_ms / 1000, tz=timezone.utc).isoformat()
                else:
                    avg_entry_price = avg_exit_price  # fallback
                    entry_time = exit_time
                
                # Calculate PnL
                if avg_entry_price > 0:
                    if position_side == "LONG":
                        pnl_pct = (avg_exit_price - avg_entry_price) / avg_entry_price * 100
                    else:
                        pnl_pct = (avg_entry_price - avg_exit_price) / avg_entry_price * 100
                else:
                    pnl_pct = 0
                
                exit_reason = "TP" if total_rpnl > 0 else "SL"
                commission = sum(float(t.get("commission", 0)) for t in group)
                net_pnl = total_rpnl - commission
                
                emoji = "🎯" if exit_reason == "TP" else "🛑"
                
                _log(f"{prefix}  {emoji} RECONCILED: {symbol} {position_side} {exit_reason}")
                _log(f"{prefix}     Entry: ${avg_entry_price:.4f} → Exit: ${avg_exit_price:.4f} | PnL: {pnl_pct:+.2f}% (${net_pnl:+.4f})")
                _log(f"{prefix}     Exit time: {exit_time}")
                
                # Log to D1
                _log_trade_to_d1(
                    symbol, timeframe, position_side,
                    avg_entry_price, avg_exit_price,
                    entry_time, exit_time,
                    0, 0,  # sl_pct, tp_pct unknown for reconciled trades
                    net_pnl, pnl_pct,
                    f"{exit_reason}_RECONCILED", acct_name
                )
                
                _send_telegram(
                    f"{emoji} *RECONCILED TRADE*\n"
                    f"{symbol} {position_side} {exit_reason}\n"
                    f"Entry: ${avg_entry_price:.4f}\n"
                    f"Exit: ${avg_exit_price:.4f}\n"
                    f"PnL: {pnl_pct:+.2f}% (${net_pnl:+.4f})\n"
                    f"⚠️ Logged during restart — was missed during downtime"
                )
                
                reconciled += 1
        
        except Exception as e:
            _log(f"{prefix}  ⚠️ Reconciliation error {symbol}: {e}")
    
    if reconciled > 0:
        _log(f"{prefix}  🔄 RECONCILIATION COMPLETE: {reconciled} trade(s) recovered and logged to D1")
    else:
        _log(f"{prefix}  ✅ Reconciliation: no missed trades found")
    
    return reconciled
