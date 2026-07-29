                        # Skip SIDEWAYS entries — proven unprofitable
                        if tool == "SIDEWAYS":
                            _log(f"{prefix}  ⏩ {symbol}: SKIP SIDEWAYS entry ({side})")
                            # v2.2: cancel position WITHOUT state change (match backtest behavior)
                            # _close_position would trigger state transition — WRONG
                            ps.switcher.position = None
                            continue