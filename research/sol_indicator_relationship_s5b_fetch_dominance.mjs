import { TradingviewAPI } from "tradingviewapi";
import fs from "node:fs";

const symbols = [["CRYPTOCAP:BTC.D","btcd"],["CRYPTOCAP:USDT.D","usdtd"]];
const api = new TradingviewAPI({ save_session: false });
const startSec = Date.parse("2022-12-15T00:00:00Z") / 1000;
const endSec = Date.parse("2026-09-26T00:00:00Z") / 1000;
const series = {};

try {
  for (const [symbol, key] of symbols) {
    const history = await api.history(symbol, {
      interval: "60",
      bars: 40000,
      chunkSize: 5000,
    });
    const bars = (history?.bars || [])
      .filter((b) => Number.isFinite(Number(b.time)) && Number(b.time) >= startSec && Number(b.time) < endSec)
      .map((b) => ({ts:Number(b.time), close:Number(b.close)}))
      .filter((b) => Number.isFinite(b.close))
      .sort((a,b) => a.ts-b.ts);
    if (!bars.length) throw new Error("No bars returned for " + symbol);
    series[key] = bars;
    console.log(symbol, "accepted", bars.length, "range", new Date(bars[0].ts*1000).toISOString(), new Date(bars[bars.length-1].ts*1000).toISOString());
  }

  const byTs = new Map();
  for (const [key, bars] of Object.entries(series)) {
    for (const b of bars) {
      const row = byTs.get(b.ts) || {ts:b.ts};
      row[key] = b.close;
      byTs.set(b.ts,row);
    }
  }
  const rows = [...byTs.values()].sort((a,b)=>a.ts-b.ts);
  const out = ["ts,btcd_close,usdtd_close"];
  for (const r of rows) {
    out.push(new Date(r.ts*1000).toISOString()+","+(r.btcd ?? "")+","+(r.usdtd ?? ""));
  }
  fs.writeFileSync("research/_stage5b_dominance_1h.csv", out.join("\n")+"\n");
  fs.writeFileSync("research/_stage5b_dominance_fetch_meta.json", JSON.stringify({
    fetched_at: new Date().toISOString(),
    btc_rows: series.btcd.length,
    usdt_rows: series.usdtd.length,
    btc_first: new Date(series.btcd[0].ts*1000).toISOString(),
    btc_last: new Date(series.btcd[series.btcd.length-1].ts*1000).toISOString(),
    usdt_first: new Date(series.usdtd[0].ts*1000).toISOString(),
    usdt_last: new Date(series.usdtd[series.usdtd.length-1].ts*1000).toISOString()
  }, null, 2));
} finally {
  api.close();
}
