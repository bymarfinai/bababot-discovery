import { Hono } from "hono";
import { cors } from "../helpers/cors";

const route = new Hono<{ Bindings: Env }>();

// CORS middleware
route.use("/*", cors);


route.post("/save-events", async (c) => {
  try {
    const { events } = await c.req.json();
    if (!events || !events.length) return c.json({ ok: false, error: "no events" });

    const db = c.env.DB;
    let saved = 0;

    for (const e of events) {
      try {
        await db.prepare(`
          INSERT OR REPLACE INTO tick_events (
            symbol, timeframe, candle_time, candle_hour_utc, candle_dow,
            pred_high, pred_low, pred_close,
            first_extreme, first_extreme_min,
            min_pred_high, min_pred_low,
            min_entry_long, min_entry_short,
            min_tp_long, min_tp_short,
            min_sl_long, min_sl_short,
            min_entry_long_L2, min_entry_short_L2,
            sequence, prev_direction, prev_range_pct,
            window, buffer_pct, buffer2_pct, tp_pct, sl_pct
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `).bind(
          e.symbol, e.timeframe, e.candle_time, e.candle_hour_utc, e.candle_dow,
          e.pred_high, e.pred_low, e.pred_close,
          e.first_extreme, e.first_extreme_min,
          e.min_pred_high, e.min_pred_low,
          e.min_entry_long, e.min_entry_short,
          e.min_tp_long, e.min_tp_short,
          e.min_sl_long, e.min_sl_short,
          e.min_entry_long_L2, e.min_entry_short_L2,
          e.sequence, e.prev_direction, e.prev_range_pct,
          e.window, e.buffer_pct, e.buffer2_pct, e.tp_pct, e.sl_pct,
        ).run();
        saved++;
      } catch (err) {
        // Skip duplicates silently
      }
    }

    return c.json({ ok: true, saved, total: events.length });
  } catch (e: any) { return c.json({ ok: false, error: e.message }); }
});

// ── Save stats summary (optional caching) ──
route.post("/save-stats", async (c) => {
  try {
    const { symbol, timeframe, stats } = await c.req.json();
    // Stats are large — store as JSON in a simple KV-like table or just acknowledge
    return c.json({ ok: true });
  } catch (e: any) { return c.json({ ok: false, error: e.message }); }
});

// ── Get tick events from D1 ──
route.get("/events", async (c) => {
  try {
    const symbol = c.req.query("symbol") || "BTCUSDT";
    const timeframe = c.req.query("timeframe") || "4h";
    const hour_utc = c.req.query("hour_utc");
    const limit = parseInt(c.req.query("limit") || "100");

    let query = "SELECT * FROM tick_events WHERE symbol = ? AND timeframe = ?";
    const params: any[] = [symbol, timeframe];

    if (hour_utc !== undefined && hour_utc !== null && hour_utc !== "") {
      query += " AND candle_hour_utc = ?";
      params.push(parseInt(hour_utc));
    }

    query += " ORDER BY candle_time DESC LIMIT ?";
    params.push(limit);

    const db = c.env.DB;
    const { results } = await db.prepare(query).bind(...params).all();

    return c.json({ ok: true, results, count: results.length });
  } catch (e: any) { return c.json({ ok: false, error: e.message }); }
});

// ── Get tick event stats (aggregated from D1) ──
route.get("/stats", async (c) => {
  try {
    const symbol = c.req.query("symbol") || "BTCUSDT";
    const timeframe = c.req.query("timeframe") || "4h";

    const db = c.env.DB;

    // Overall counts
    const total = await db.prepare(
      "SELECT COUNT(*) as cnt FROM tick_events WHERE symbol = ? AND timeframe = ?"
    ).bind(symbol, timeframe).first();

    // First extreme distribution
    const extremes = await db.prepare(`
      SELECT first_extreme, COUNT(*) as cnt
      FROM tick_events WHERE symbol = ? AND timeframe = ?
      GROUP BY first_extreme
    `).bind(symbol, timeframe).all();

    // Per hour breakdown
    const hourly = await db.prepare(`
      SELECT candle_hour_utc as hour,
        COUNT(*) as total,
        SUM(CASE WHEN first_extreme = 'HIGH' THEN 1 ELSE 0 END) as high_first,
        SUM(CASE WHEN first_extreme = 'LOW' THEN 1 ELSE 0 END) as low_first,
        SUM(CASE WHEN first_extreme = 'NONE' THEN 1 ELSE 0 END) as none_cnt
      FROM tick_events WHERE symbol = ? AND timeframe = ?
      GROUP BY candle_hour_utc ORDER BY candle_hour_utc
    `).bind(symbol, timeframe).all();

    return c.json({
      ok: true, symbol, timeframe,
      total: total?.cnt || 0,
      extremes: extremes.results,
      hourly: hourly.results,
    });
  } catch (e: any) { return c.json({ ok: false, error: e.message }); }
});

// CORS middleware for tick routes

// ── Proxy to Railway for tick discovery control ──
route.get("/start", async (c) => {
  try {
    const url = new URL(c.req.url);
    const resp = await fetch(`${c.env.BACKTEST_API_URL}/tick/start${url.search}`);
    return c.json(await resp.json());
  } catch (e: any) { return c.json({ ok: false, error: e.message }); }
});

route.get("/stop", async (c) => {
  try {
    const resp = await fetch(`${c.env.BACKTEST_API_URL}/tick/stop`);
    return c.json(await resp.json());
  } catch (e: any) { return c.json({ ok: false, error: e.message }); }
});

route.get("/status", async (c) => {
  try {
    const resp = await fetch(`${c.env.BACKTEST_API_URL}/tick/status`);
    return c.json(await resp.json());
  } catch (e: any) { return c.json({ ok: false, error: e.message }); }
});

route.get("/log", async (c) => {
  try {
    const limit = c.req.query("limit") || "200";
    const resp = await fetch(`${c.env.BACKTEST_API_URL}/tick/log?limit=${limit}`);
    return c.json(await resp.json());
  } catch (e: any) { return c.json({ ok: false, error: e.message }); }
});

route.get("/analyze", async (c) => {
  try {
    const url = new URL(c.req.url);
    const resp = await fetch(`${c.env.BACKTEST_API_URL}/tick/analyze${url.search}`);
    return c.json(await resp.json());
  } catch (e: any) { return c.json({ ok: false, error: e.message }); }
});

// ════════════════════════════════════════════════════════════
// PASTE DI index.ts SEBELUM "export default {"
// (setelah section tick endpoints yg sudah ada)
// ════════════════════════════════════════════════════════════

// ── Save strategy from sweep engine ──
route.post("/save-strategy", async (c) => {
  const body = await c.req.json() as any;
  const db = c.env.DB;

  try {
    await db.prepare(`
      INSERT INTO tick_strategies (
        symbol, timeframe, mode, direction, entry_level, exit_tp_level, exit_sl_level,
        window, buffer_pct, tp_pct, sl_pct,
        win_rate, total_trades, profit_per_day, max_drawdown, avg_pnl_per_trade,
        min_weekly_wr, worst_streak, consistency_pct,
        train_wr, test_wr, walk_forward_ratio,
        confidence_score, status
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).bind(
      body.symbol, body.timeframe, body.mode,
      body.direction || "BOTH", body.entry_level || "pred_low",
      body.exit_tp_level || "tp_long", body.exit_sl_level || "sl_long",
      body.window || 10, body.buffer_pct || 0, body.tp_pct, body.sl_pct,
      body.win_rate, body.total_trades, body.profit_per_day,
      body.max_drawdown || 0, body.avg_pnl_per_trade || 0,
      body.min_weekly_wr || 0, body.worst_streak || 0, body.consistency_pct || 0,
      body.train_wr || 0, body.test_wr || 0, body.walk_forward_ratio || 0,
      body.confidence_score || 0, body.status || "candidate"
    ).run();
    return c.json({ ok: true });
  } catch (e: any) {
    return c.json({ ok: false, error: e.message }, 500);
  }
});

// ── Get all strategies ──
route.get("/strategies", async (c) => {
  const db = c.env.DB;
  const url = new URL(c.req.url);
  const symbol = url.searchParams.get("symbol");
  const mode = url.searchParams.get("mode");
  const status = url.searchParams.get("status");
  const min_wr = url.searchParams.get("min_wr");
  const sort = url.searchParams.get("sort") || "confidence_score";

  let query = "SELECT * FROM tick_strategies WHERE 1=1";
  const params: any[] = [];

  if (symbol) { query += " AND symbol = ?"; params.push(symbol); }
  if (mode) { query += " AND mode = ?"; params.push(mode); }
  if (status) { query += " AND status = ?"; params.push(status); }
  if (min_wr) { query += " AND win_rate >= ?"; params.push(parseFloat(min_wr)); }

  const validSorts = ["confidence_score", "win_rate", "profit_per_day", "total_trades"];
  const sortCol = validSorts.includes(sort) ? sort : "confidence_score";
  query += ` ORDER BY ${sortCol} DESC LIMIT 200`;

  const results = await db.prepare(query).bind(...params).all();
  return c.json({ ok: true, strategies: results.results, count: results.results.length });
});

// ── Delete strategy ──
route.delete("/strategies/:id", async (c) => {
  const id = c.req.param("id");
  await c.env.DB.prepare("DELETE FROM tick_strategies WHERE id = ?").bind(id).run();
  return c.json({ ok: true });
});

// ── Proxy sweep control to Railway ──
route.get("/sweep", async (c) => {
  const url = new URL(c.req.url);
  const resp = await fetch(`${c.env.BACKTEST_API_URL}/tick/sweep${url.search}`);
  return c.json(await resp.json());
});

route.get("/sweep-stop", async (c) => {
  const resp = await fetch(`${c.env.BACKTEST_API_URL}/tick/sweep-stop`);
  return c.json(await resp.json());
});

route.get("/sweep-status", async (c) => {
  const resp = await fetch(`${c.env.BACKTEST_API_URL}/tick/sweep-status`);
  return c.json(await resp.json());
});

// ════════════════════════════════════════════════════════════
// PASTE THIS BLOCK at line 10430 in index.ts
// BEFORE the line: export default {
// ════════════════════════════════════════════════════════════

// ── Level Clustering: save results from Railway ──
route.post("/save-clustering", async (c) => {
  const body = await c.req.json();
  const { symbol, timeframe, entry_points, suggestions } = body;

  // Create tables if not exist
  await c.env.DB.prepare(`
    CREATE TABLE IF NOT EXISTS level_clustering (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      symbol TEXT NOT NULL,
      timeframe TEXT NOT NULL,
      entry_name TEXT NOT NULL,
      entry_side TEXT NOT NULL,
      entry_triggered_pct REAL,
      total_entries INTEGER,
      best_tp REAL,
      best_sl REAL,
      est_wr REAL,
      consistency_pct REAL,
      walk_forward_ratio REAL,
      worst_streak INTEGER,
      p5_weekly_wr REAL,
      levels_json TEXT,
      per_hour_json TEXT,
      sequence_json TEXT,
      created_at TEXT DEFAULT (datetime('now')),
      UNIQUE(symbol, timeframe, entry_name, entry_side)
    )
  `).run();

  await c.env.DB.prepare(`
    CREATE TABLE IF NOT EXISTS clustering_suggestions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      symbol TEXT NOT NULL,
      timeframe TEXT NOT NULL,
      rank INTEGER,
      entry_name TEXT NOT NULL,
      entry_side TEXT NOT NULL,
      tp REAL,
      sl REAL,
      est_wr REAL,
      trades INTEGER,
      consistency REAL,
      wf_ratio REAL,
      worst_streak INTEGER,
      score REAL,
      insight TEXT,
      created_at TEXT DEFAULT (datetime('now')),
      UNIQUE(symbol, timeframe, entry_name, entry_side)
    )
  `).run();

  // Delete old data for this pair×tf
  await c.env.DB.prepare(
    "DELETE FROM level_clustering WHERE symbol = ? AND timeframe = ?"
  ).bind(symbol, timeframe).run();

  await c.env.DB.prepare(
    "DELETE FROM clustering_suggestions WHERE symbol = ? AND timeframe = ?"
  ).bind(symbol, timeframe).run();

  // Insert entry points
  let saved = 0;
  for (const ep of (entry_points || [])) {
    const bc = ep.best_combo || {};
    const stab = ep.stability || {};
    try {
      await c.env.DB.prepare(`
        INSERT OR REPLACE INTO level_clustering (
          symbol, timeframe, entry_name, entry_side,
          entry_triggered_pct, total_entries,
          best_tp, best_sl, est_wr,
          consistency_pct, walk_forward_ratio, worst_streak, p5_weekly_wr,
          levels_json, per_hour_json, sequence_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `).bind(
        symbol, timeframe, ep.entry_name, ep.entry_side,
        ep.entry_triggered_pct, ep.total_entries,
        bc.tp || null, bc.sl || null, bc.est_wr || null,
        stab.consistency_pct || null, stab.walk_forward_ratio || null,
        stab.worst_streak || null, stab.p5_weekly_wr || null,
        ep.levels_json, ep.per_hour_json || null, ep.sequence_json || null
      ).run();
      saved++;
    } catch (e) {
      console.error("level_clustering insert error:", e);
    }
  }

  // Insert suggestions
  for (const s of (suggestions || [])) {
    try {
      await c.env.DB.prepare(`
        INSERT OR REPLACE INTO clustering_suggestions (
          symbol, timeframe, rank, entry_name, entry_side,
          tp, sl, est_wr, trades, consistency, wf_ratio, worst_streak, score, insight
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `).bind(
        symbol, timeframe, s.rank, s.entry_name, s.entry_side,
        s.tp, s.sl, s.est_wr, s.trades, s.consistency, s.wf_ratio,
        s.worst_streak, s.score, s.insight
      ).run();
    } catch (e) {
      console.error("suggestion insert error:", e);
    }
  }

  return c.json({ ok: true, saved, suggestions: (suggestions || []).length });
});

// ── Level Clustering: get results ──
route.get("/clustering-results", async (c) => {
  const url = new URL(c.req.url);
  const symbol = url.searchParams.get("symbol");
  const timeframe = url.searchParams.get("timeframe");

  let query = "SELECT * FROM level_clustering WHERE 1=1";
  const params: string[] = [];
  if (symbol) { query += " AND symbol = ?"; params.push(symbol); }
  if (timeframe) { query += " AND timeframe = ?"; params.push(timeframe); }
  query += " ORDER BY est_wr DESC NULLS LAST";

  const rows = await c.env.DB.prepare(query).bind(...params).all();

  let sugQuery = "SELECT * FROM clustering_suggestions WHERE 1=1";
  const sugParams: string[] = [];
  if (symbol) { sugQuery += " AND symbol = ?"; sugParams.push(symbol); }
  if (timeframe) { sugQuery += " AND timeframe = ?"; sugParams.push(timeframe); }
  sugQuery += " ORDER BY rank ASC";

  const suggestions = await c.env.DB.prepare(sugQuery).bind(...sugParams).all();

  return c.json({
    results: rows.results || [],
    suggestions: suggestions.results || [],
  });
});

// ── Level Clustering: proxy standalone run to Railway ──
route.get("/cluster", async (c) => {
  const url = new URL(c.req.url);
  const resp = await fetch(`${c.env.BACKTEST_API_URL}/tick/cluster${url.search}`);
  return c.json(await resp.json());
});

// ── Sweep pause/resume proxy ──
route.get("/sweep-pause", async (c) => {
  const resp = await fetch(`${c.env.BACKTEST_API_URL}/tick/sweep-pause`);
  return c.json(await resp.json());
});

route.get("/sweep-resume", async (c) => {
  const resp = await fetch(`${c.env.BACKTEST_API_URL}/tick/sweep-resume`);
  return c.json(await resp.json());
});

// ── Custom Backtest (MCP-triggered) ──
route.post("/custom-backtest", async (c) => {
  const body = await c.req.json();
  const resp = await fetch(`${c.env.BACKTEST_API_URL}/tick/custom-backtest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return c.json(await resp.json());
});

// ── Combo Sweep: save results ──
route.post("/save-combo-results", async (c) => {
  const body = await c.req.json();
  const { symbol, timeframe, results } = body;

  await c.env.DB.prepare(`
    CREATE TABLE IF NOT EXISTS combo_results (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      symbol TEXT NOT NULL,
      timeframe TEXT NOT NULL,
      entry_name TEXT NOT NULL,
      entry_side TEXT NOT NULL,
      tp_name TEXT NOT NULL,
      tp_type TEXT,
      tp_pct REAL,
      sl_pct REAL,
      dca REAL,
      hold TEXT,
      wr REAL,
      ev_per_trade REAL,
      ratio REAL,
      trades INTEGER,
      total_profit REAL,
      avg_daily REAL,
      consistency REAL,
      filter TEXT DEFAULT 'all',
      created_at TEXT DEFAULT (datetime('now')),
      UNIQUE(symbol, timeframe, entry_name, entry_side, tp_name, sl_pct, dca, hold, filter)
    )
  `).run();

  await c.env.DB.prepare(
    "DELETE FROM combo_results WHERE symbol = ? AND timeframe = ?"
  ).bind(symbol, timeframe).run();

  let saved = 0;
  for (const r of (results || [])) {
    try {
      await c.env.DB.prepare(`
        INSERT OR REPLACE INTO combo_results (
          symbol, timeframe, entry_name, entry_side,
          tp_name, tp_type, tp_pct, sl_pct, dca, hold,
          wr, ev_per_trade, ratio, trades, total_profit, avg_daily, consistency, filter
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `).bind(
        symbol, timeframe, r.entry, r.side,
        r.tp_name, r.tp_type || 'fixed', r.tp_pct, r.sl_pct, r.dca, r.hold,
        r.wr, r.ev, r.ratio, r.trades, r.total_profit, r.avg_daily, r.consistency,
        r.filter || 'all'
      ).run();
      saved++;
    } catch (e) { console.error("combo insert error:", e); }
  }
  return c.json({ ok: true, saved });
});

// ── Combo Sweep: get results ──
route.get("/combo-results", async (c) => {
  const url = new URL(c.req.url);
  const symbol = url.searchParams.get("symbol");
  const timeframe = url.searchParams.get("timeframe");
  const sort = url.searchParams.get("sort") || "total_profit";
  const limit = parseInt(url.searchParams.get("limit") || "50");

  let query = "SELECT * FROM combo_results WHERE 1=1";
  const params: string[] = [];
  if (symbol) { query += " AND symbol = ?"; params.push(symbol); }
  if (timeframe) { query += " AND timeframe = ?"; params.push(timeframe); }
  query += ` ORDER BY ${sort === 'ev' ? 'ev_per_trade' : sort === 'wr' ? 'wr' : sort === 'daily' ? 'avg_daily' : 'total_profit'} DESC LIMIT ${limit}`;

  const rows = await c.env.DB.prepare(query).bind(...params).all();
  return c.json({ results: rows.results || [] });
});

// ════════════════════════════════════════════════════════════
// END OF CLUSTERING ADDITIONS
// ════════════════════════════════════════════════════════════

export default route;
