/**
 * BabaBot AI Strategy Discovery — Step 3: Discovery Orchestrator
 * Cloudflare Workers Cron Job
 * 
 * Flow:
 * 1. Load knowledge base dari D1
 * 2. Call Claude API → generate hipotesis batch baru
 * 3. Call Railway /backtest untuk setiap config
 * 4. Simpan hasil ke D1 archive
 * 5. Update knowledge base
 * 6. Kalau ada kandidat → notif Telegram
 */

import { Hono } from "hono";

// ============================================================
// TYPES
// ============================================================

interface DiscoveryEnv {
  DB: D1Database;
  ANTHROPIC_API_KEY: string;
  TELEGRAM_BOT_TOKEN: string;
  BACKTEST_API_URL: string;      // https://web-production-b6a05.up.railway.app
  BACKTEST_API_TOKEN: string;    // Optional auth token
  ADMIN_TELEGRAM_ID: string;     // 888366328
}

interface BacktestConfig {
  symbol: string;
  timeframe: string;
  entry_logic: string;
  indicators: Record<string, number>;
  sl_pct: number;
  tp_pct: number;
  days: number;
  direction: string;
  use_atr_sl_tp?: boolean;
  sl_atr_mult?: number;
  tp_atr_mult?: number;
  trend_filter?: string | null;
  volatility_filter?: string | null;
  volume_filter?: string | null;
  regime_filter?: string | null;
  session_filter?: string | null;
}

interface BacktestResult {
  symbol: string;
  timeframe: string;
  entry_logic: string;
  total_trades: number;
  win_rate: number;
  profit_per_day: number;
  net_profit: number;
  max_drawdown: number;
  sharpe_ratio: number;
  profit_factor: number;
  avg_win: number;
  avg_loss: number;
  oos_win_rate: number;
  oos_profit_per_day: number;
  oos_trades: number;
  status: string;
  meets_criteria: boolean;
  data_days: number;
}

interface KnowledgeBase {
  category: string;
  summary: string;
  best_config: string;
  best_win_rate: number;
  best_profit_per_day: number;
  experiments_count: number;
  do_not_explore: string;
}

// ============================================================
// HELPERS
// ============================================================

function generateSessionId(): string {
  return `sess_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

async function sendTelegramMessage(token: string, chatId: string, text: string): Promise<void> {
  await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chatId, text, parse_mode: "HTML" }),
  });
}

async function runBacktest(config: BacktestConfig, apiUrl: string, apiToken: string): Promise<BacktestResult | null> {
  try {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (apiToken) headers["Authorization"] = `Bearer ${apiToken}`;
    
    const resp = await fetch(`${apiUrl}/backtest`, {
      method: "POST",
      headers,
      body: JSON.stringify(config),
      signal: AbortSignal.timeout(60000), // 60s timeout
    });
    
    if (!resp.ok) return null;
    return await resp.json() as BacktestResult;
  } catch {
    return null;
  }
}

// ============================================================
// LOAD KNOWLEDGE BASE
// ============================================================

async function loadKnowledgeBase(db: D1Database): Promise<KnowledgeBase[]> {
  const result = await db.prepare(
    "SELECT * FROM discovery_knowledge_base ORDER BY last_updated DESC LIMIT 20"
  ).all<KnowledgeBase>();
  return result.results || [];
}

async function loadRecentArchive(db: D1Database, limit: number = 50): Promise<BacktestResult[]> {
  const result = await db.prepare(`
    SELECT symbol, timeframe, entry_logic, win_rate, profit_per_day, 
           max_drawdown, total_trades, meets_criteria, status
    FROM discovery_archive 
    ORDER BY tested_at DESC 
    LIMIT ?
  `).bind(limit).all();
  return (result.results || []) as unknown as BacktestResult[];
}

// ============================================================
// CLAUDE: GENERATE HYPOTHESIS
// ============================================================

async function generateHypothesis(
  apiKey: string,
  knowledgeBase: KnowledgeBase[],
  recentResults: BacktestResult[],
  sessionId: string,
  batchNumber: number
): Promise<BacktestConfig[]> {
  
  const kbSummary = knowledgeBase.length > 0
    ? knowledgeBase.map(kb => 
        `[${kb.category}] ${kb.summary} | Best WR: ${kb.best_win_rate}% | Best P/day: $${kb.best_profit_per_day} | Tested: ${kb.experiments_count}`
      ).join("\n")
    : "No exploration history yet — start fresh.";
  
  const recentSummary = recentResults.length > 0
    ? recentResults.slice(0, 10).map(r =>
        `${r.symbol} ${r.timeframe} ${r.entry_logic}: WR=${r.win_rate}% P/day=$${r.profit_per_day} DD=${r.max_drawdown}% trades=${r.total_trades} ${r.meets_criteria ? "✅CANDIDATE" : "❌"}`
      ).join("\n")
    : "No recent results.";

  const systemPrompt = `You are an expert quantitative trading strategist AI for BabaBot — a crypto futures trading bot.

Your job is to discover profitable trading strategies through systematic backtesting on Binance Futures data.

TARGET CRITERIA (strategy must meet ALL):
- Net profit ≥ $10/day (after 0.08% fee roundtrip)
- Max drawdown ≤ 5%
- Win rate ≥ 55%
- Minimum 30 trades
- OOS (out-of-sample) win rate ≥ 50% and profit > 0

AVAILABLE PAIRS: BTCUSDT, ETHUSDT, XRPUSDT, YFIUSDT
AVAILABLE TIMEFRAMES: 1m, 3m, 5m, 15m, 1h

AVAILABLE ENTRY LOGICS:
Crossover: ema_cross, ema_cross_rsi, ema_cross_volume, ema_trend_pullback, sma_cross, macd_cross, macd_zero, macd_histogram_momentum, stoch_cross, stoch_ob_os, supertrend_flip, sar_flip, ichimoku_cross, vwap_cross
Breakout: donchian_breakout, bb_breakout, keltner_breakout
Mean Reversion: rsi_ob_os, bb_bounce, cci_ob_os
Momentum: adx_momentum
Divergence: rsi_divergence, obv_divergence
Volume: volume_spike_momentum

AVAILABLE FILTERS (optional, max 2):
- trend_filter: ema200_long, ema200_short, adx_direction
- volatility_filter: atr_min, atr_max, bb_squeeze
- volume_filter: volume_spike, taker_buy
- regime_filter: trending, ranging
- session_filter: asia, london, ny, london_ny

INDICATOR PARAMETERS:
- ema_fast/slow: 5,8,9,13,21,50,100
- rsi_period: 7,14,21 | rsi_oversold: 20-35 | rsi_overbought: 65-80
- macd: fast 8-15, slow 21-30, signal 5-12
- stoch_k: 5-21 | stoch_oversold: 15-25 | stoch_overbought: 75-85
- bb_period: 14,20 | bb_std: 1.5,2.0,2.5
- donchian_period: 10,20,50
- sl_pct: 0.1-2.0 | tp_pct: 0.2-4.0
- use_atr_sl_tp: true/false | sl_atr_mult: 1.0-3.0 | tp_atr_mult: 2.0-5.0

STRATEGY: Be systematic. Don't re-explore what's already been tested. Build on what worked. Avoid what didn't.

Respond ONLY with a valid JSON array of 5-8 BacktestConfig objects. No explanation, no markdown, just the JSON array.`;

  const userPrompt = `Session: ${sessionId} | Batch: ${batchNumber}

KNOWLEDGE BASE (what we know so far):
${kbSummary}

RECENT RESULTS (last 10):
${recentSummary}

Generate 5-8 strategy configs to test next. Be strategic — build on insights from knowledge base, avoid combinations marked as do_not_explore. Focus on finding strategies that meet the target criteria.

Return ONLY a JSON array. Example format:
[
  {
    "symbol": "BTCUSDT",
    "timeframe": "5m",
    "entry_logic": "ema_cross_rsi",
    "indicators": {"ema_fast": 8, "ema_slow": 21, "rsi_period": 14, "rsi_oversold": 35, "rsi_overbought": 65},
    "sl_pct": 0.25,
    "tp_pct": 0.75,
    "days": 90,
    "direction": "long",
    "trend_filter": "ema200_long",
    "session_filter": "london_ny"
  }
]`;

  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model: "claude-sonnet-4-20250514",
      max_tokens: 2000,
      system: systemPrompt,
      messages: [{ role: "user", content: userPrompt }],
    }),
  });

  if (!response.ok) {
    throw new Error(`Claude API error: ${response.status}`);
  }

  const data = await response.json() as { content: Array<{ type: string; text: string }> };
  const text = data.content[0]?.text || "[]";
  
  // Parse JSON — strip any markdown if present
  const clean = text.replace(/```json|```/g, "").trim();
  const configs = JSON.parse(clean) as BacktestConfig[];
  
  // Ensure days=90 for all
  return configs.map(c => ({ ...c, days: 90 }));
}

// ============================================================
// SAVE RESULTS TO D1
// ============================================================

async function saveResults(
  db: D1Database,
  sessionId: string,
  batchNumber: number,
  results: Array<{ config: BacktestConfig; result: BacktestResult }>
): Promise<void> {
  for (const { config, result } of results) {
    if (result.status !== "ok") continue;
    
    await db.prepare(`
      INSERT INTO discovery_archive 
      (session_id, batch_number, symbol, timeframe, entry_logic, config,
       total_trades, win_rate, profit_per_day, net_profit, max_drawdown,
       sharpe_ratio, profit_factor, avg_win, avg_loss,
       oos_win_rate, oos_profit_per_day, oos_trades,
       status, meets_criteria, data_days)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).bind(
      sessionId, batchNumber,
      result.symbol, result.timeframe, result.entry_logic,
      JSON.stringify(config),
      result.total_trades, result.win_rate, result.profit_per_day,
      result.net_profit, result.max_drawdown, result.sharpe_ratio,
      result.profit_factor, result.avg_win, result.avg_loss,
      result.oos_win_rate, result.oos_profit_per_day, result.oos_trades,
      result.status, result.meets_criteria ? 1 : 0, result.data_days
    ).run();
  }
}

// ============================================================
// UPDATE KNOWLEDGE BASE
// ============================================================

async function updateKnowledgeBase(
  db: D1Database,
  apiKey: string,
  results: Array<{ config: BacktestConfig; result: BacktestResult }>
): Promise<void> {
  // Group results by category
  const grouped: Record<string, Array<{ config: BacktestConfig; result: BacktestResult }>> = {};
  
  for (const item of results) {
    if (item.result.status !== "ok") continue;
    const category = `${item.result.entry_logic}_${item.result.symbol}_${item.result.timeframe}`;
    if (!grouped[category]) grouped[category] = [];
    grouped[category].push(item);
  }
  
  for (const [category, items] of Object.entries(grouped)) {
    // Find best result in this category
    const best = items.reduce((a, b) => 
      a.result.profit_per_day > b.result.profit_per_day ? a : b
    );
    
    // Get existing KB entry
    const existing = await db.prepare(
      "SELECT * FROM discovery_knowledge_base WHERE category = ?"
    ).bind(category).first<KnowledgeBase>();
    
    const totalExperiments = (existing?.experiments_count || 0) + items.length;
    const bestWinRate = Math.max(existing?.best_win_rate || 0, best.result.win_rate);
    const bestProfitPerDay = Math.max(existing?.best_profit_per_day || 0, best.result.profit_per_day);
    
    // Generate summary via Claude
    const summaryPrompt = `Summarize these backtest results for ${category} in max 100 words. Be concise and actionable. Focus on: what works, what doesn't, what to try next.

Results:
${items.map(i => `WR=${i.result.win_rate}% P/day=$${i.result.profit_per_day} DD=${i.result.max_drawdown}% trades=${i.result.total_trades} config=${JSON.stringify(i.config.indicators)}`).join("\n")}

Previous summary: ${existing?.summary || "None"}`;

    const summaryResp = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: "claude-haiku-4-5-20251001",
        max_tokens: 200,
        messages: [{ role: "user", content: summaryPrompt }],
      }),
    });
    
    let summary = existing?.summary || "No data yet.";
    if (summaryResp.ok) {
      const summaryData = await summaryResp.json() as { content: Array<{ text: string }> };
      summary = summaryData.content[0]?.text || summary;
    }
    
    await db.prepare(`
      INSERT INTO discovery_knowledge_base 
      (category, summary, best_config, best_win_rate, best_profit_per_day, experiments_count, last_updated)
      VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
      ON CONFLICT(category) DO UPDATE SET
        summary = excluded.summary,
        best_config = CASE WHEN excluded.best_profit_per_day > best_profit_per_day 
                          THEN excluded.best_config ELSE best_config END,
        best_win_rate = MAX(best_win_rate, excluded.best_win_rate),
        best_profit_per_day = MAX(best_profit_per_day, excluded.best_profit_per_day),
        experiments_count = excluded.experiments_count,
        last_updated = CURRENT_TIMESTAMP
    `).bind(
      category, summary, JSON.stringify(best.config),
      bestWinRate, bestProfitPerDay, totalExperiments
    ).run();
  }
}

// ============================================================
// SAVE CANDIDATES & NOTIFY
// ============================================================

async function processCandidates(
  db: D1Database,
  sessionId: string,
  apiKey: string,
  botToken: string,
  adminId: string,
  results: Array<{ config: BacktestConfig; result: BacktestResult }>
): Promise<number> {
  const candidates = results.filter(r => r.result.meets_criteria);
  
  for (const { config, result } of candidates) {
    // Generate Claude reasoning
    const reasoningResp = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: "claude-haiku-4-5-20251001",
        max_tokens: 300,
        messages: [{
          role: "user",
          content: `Explain in 3-4 sentences why this trading strategy is promising and worth deploying live:
Config: ${JSON.stringify(config)}
Metrics: WR=${result.win_rate}% P/day=$${result.profit_per_day} DD=${result.max_drawdown}% Sharpe=${result.sharpe_ratio} PF=${result.profit_factor} Trades=${result.total_trades}
OOS: WR=${result.oos_win_rate}% P/day=$${result.oos_profit_per_day} Trades=${result.oos_trades}`
        }],
      }),
    });
    
    let reasoning = "Strong metrics across all criteria.";
    if (reasoningResp.ok) {
      const rd = await reasoningResp.json() as { content: Array<{ text: string }> };
      reasoning = rd.content[0]?.text || reasoning;
    }
    
    // Save to candidates table
    await db.prepare(`
      INSERT INTO discovery_candidates
      (session_id, symbol, timeframe, entry_logic, config,
       win_rate, profit_per_day, max_drawdown, sharpe_ratio, profit_factor,
       oos_win_rate, oos_profit_per_day, total_trades, data_days, claude_reasoning)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).bind(
      sessionId, result.symbol, result.timeframe, result.entry_logic,
      JSON.stringify(config),
      result.win_rate, result.profit_per_day, result.max_drawdown,
      result.sharpe_ratio, result.profit_factor,
      result.oos_win_rate, result.oos_profit_per_day,
      result.total_trades, result.data_days, reasoning
    ).run();
    
    // Notify Telegram
    const rr = (config.tp_pct / config.sl_pct).toFixed(2);
    const message = `🎯 <b>STRATEGI BARU DITEMUKAN!</b>
━━━━━━━━━━━━━━━━━
📊 <b>${result.symbol} ${result.timeframe} — ${result.entry_logic.toUpperCase()}</b>

💰 <b>Metrics:</b>
✅ Win Rate: ${result.win_rate}%
💵 Profit/day: $${result.profit_per_day}
📉 Max DD: ${result.max_drawdown}%
⚖️ Sharpe: ${result.sharpe_ratio}
🔢 Total trades: ${result.total_trades}
📊 RR: 1:${rr}

🧪 <b>OOS Validation:</b>
✅ WR: ${result.oos_win_rate}%
💵 P/day: $${result.oos_profit_per_day}
🔢 Trades: ${result.oos_trades}

⚙️ <b>Config:</b>
SL: ${config.sl_pct}% | TP: ${config.tp_pct}%
Direction: ${config.direction}
${config.trend_filter ? `Trend filter: ${config.trend_filter}` : ""}
${config.session_filter ? `Session: ${config.session_filter}` : ""}

🤖 <b>Claude:</b>
${reasoning}

━━━━━━━━━━━━━━━━━
Gunakan: /strat add ${result.entry_logic.toUpperCase()}_${result.symbol}_${result.timeframe} ${result.symbol} [QTY] ${config.sl_pct} ${config.tp_pct}`;

    await sendTelegramMessage(botToken, adminId, message);
    
    // Mark as notified
    await db.prepare(
      "UPDATE discovery_candidates SET telegram_notified = 1 WHERE session_id = ? AND symbol = ? AND entry_logic = ?"
    ).bind(sessionId, result.symbol, result.entry_logic).run();
  }
  
  return candidates.length;
}

// ============================================================
// MAIN ORCHESTRATOR
// ============================================================

async function runDiscovery(env: DiscoveryEnv): Promise<{ 
  session_id: string;
  batch: number;
  tested: number;
  candidates: number;
  error?: string;
}> {
  const sessionId = generateSessionId();
  
  // Get or create session
  const existingSession = await env.DB.prepare(
    "SELECT * FROM discovery_sessions WHERE status = 'running' ORDER BY last_active DESC LIMIT 1"
  ).first<{ session_id: string; total_experiments: number; candidates_found: number }>();
  
  const activeSessionId = existingSession?.session_id || sessionId;
  const batchNumber = existingSession 
    ? (await env.DB.prepare(
        "SELECT COUNT(*) as cnt FROM discovery_working_memory WHERE session_id = ?"
      ).bind(activeSessionId).first<{ cnt: number }>())?.cnt || 0
    : 0;
  
  // Create session if new
  if (!existingSession) {
    await env.DB.prepare(`
      INSERT INTO discovery_sessions (session_id, status, current_focus)
      VALUES (?, 'running', 'Initial exploration — testing baseline strategies')
    `).bind(activeSessionId).run();
  }
  
  try {
    // 1. Load knowledge base
    const kb = await loadKnowledgeBase(env.DB);
    const recentResults = await loadRecentArchive(env.DB, 50);
    
    // 2. Generate hypothesis via Claude
    const configs = await generateHypothesis(
      env.ANTHROPIC_API_KEY, kb, recentResults, activeSessionId, batchNumber + 1
    );
    
    // 3. Save working memory
    await env.DB.prepare(`
      INSERT INTO discovery_working_memory (session_id, batch_number, hypothesis, configs_to_test, status)
      VALUES (?, ?, ?, ?, 'running')
    `).bind(
      activeSessionId, batchNumber + 1,
      `Batch ${batchNumber + 1} hypothesis`,
      JSON.stringify(configs)
    ).run();
    
    // 4. Run backtests
    const results: Array<{ config: BacktestConfig; result: BacktestResult }> = [];
    
    for (const config of configs) {
      const result = await runBacktest(config, env.BACKTEST_API_URL, env.BACKTEST_API_TOKEN || "");
      if (result) {
        results.push({ config, result });
      }
      // Small delay between requests
      await new Promise(r => setTimeout(r, 500));
    }
    
    // 5. Save to archive
    await saveResults(env.DB, activeSessionId, batchNumber + 1, results);
    
    // 6. Update knowledge base
    await updateKnowledgeBase(env.DB, env.ANTHROPIC_API_KEY, results);
    
    // 7. Process candidates & notify
    const candidatesFound = await processCandidates(
      env.DB, activeSessionId, env.ANTHROPIC_API_KEY,
      env.TELEGRAM_BOT_TOKEN, env.ADMIN_TELEGRAM_ID, results
    );
    
    // 8. Update session
    await env.DB.prepare(`
      UPDATE discovery_sessions 
      SET total_experiments = total_experiments + ?,
          candidates_found = candidates_found + ?,
          last_active = CURRENT_TIMESTAMP,
          current_focus = ?
      WHERE session_id = ?
    `).bind(
      results.length, candidatesFound,
      `Batch ${batchNumber + 1} complete — tested ${results.length} configs`,
      activeSessionId
    ).run();
    
    // 9. Mark working memory done
    await env.DB.prepare(
      "UPDATE discovery_working_memory SET status = 'done', completed_at = CURRENT_TIMESTAMP WHERE session_id = ? AND batch_number = ?"
    ).bind(activeSessionId, batchNumber + 1).run();
    
    return {
      session_id: activeSessionId,
      batch: batchNumber + 1,
      tested: results.length,
      candidates: candidatesFound,
    };
    
  } catch (error) {
    const errMsg = error instanceof Error ? error.message : String(error);
    await env.DB.prepare(
      "UPDATE discovery_sessions SET claude_notes = ? WHERE session_id = ?"
    ).bind(`Error in batch ${batchNumber + 1}: ${errMsg}`, activeSessionId).run();
    
    return {
      session_id: activeSessionId,
      batch: batchNumber + 1,
      tested: 0,
      candidates: 0,
      error: errMsg,
    };
  }
}

// ============================================================
// HONO APP + CRON
// ============================================================

const app = new Hono<{ Bindings: DiscoveryEnv }>();

// Manual trigger endpoint
app.post("/discovery/run", async (c) => {
  const result = await runDiscovery(c.env);
  return c.json(result);
});

// Status endpoint
app.get("/discovery/status", async (c) => {
  const session = await c.env.DB.prepare(
    "SELECT * FROM discovery_sessions ORDER BY last_active DESC LIMIT 1"
  ).first();
  
  const totalArchive = await c.env.DB.prepare(
    "SELECT COUNT(*) as cnt FROM discovery_archive"
  ).first<{ cnt: number }>();
  
  const candidates = await c.env.DB.prepare(
    "SELECT * FROM discovery_candidates WHERE status = 'pending' ORDER BY profit_per_day DESC"
  ).all();
  
  const topResults = await c.env.DB.prepare(
    "SELECT symbol, timeframe, entry_logic, win_rate, profit_per_day, max_drawdown, meets_criteria FROM discovery_archive ORDER BY profit_per_day DESC LIMIT 10"
  ).all();
  
  return c.json({
    session,
    total_experiments: totalArchive?.cnt || 0,
    pending_candidates: candidates.results?.length || 0,
    candidates: candidates.results,
    top_results: topResults.results,
  });
});

// Reset session
app.post("/discovery/reset", async (c) => {
  await c.env.DB.prepare(
    "UPDATE discovery_sessions SET status = 'completed' WHERE status = 'running'"
  ).run();
  return c.json({ ok: true, message: "Session reset. Next run will start fresh session." });
});

// Cron handler — runs every 6 hours
export default {
  async fetch(request: Request, env: DiscoveryEnv): Promise<Response> {
    return app.fetch(request, env);
  },
  
  async scheduled(event: ScheduledEvent, env: DiscoveryEnv): Promise<void> {
    console.log("[Discovery] Cron triggered:", event.cron);
    const result = await runDiscovery(env);
    console.log("[Discovery] Result:", JSON.stringify(result));
  },
};
