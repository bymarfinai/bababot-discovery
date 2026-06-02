# BabaBot AI Strategy Discovery — Backtesting Engine

## Step 1A: Data Fetcher ✅

Tarik historical klines dari Binance Futures (data.binance.vision) ke SQLite lokal.

### Quick Start

```bash
pip install requests
python data_fetcher.py              # Fetch semua pair & TF, 90 hari
python data_fetcher.py --days 180   # 6 bulan data
python data_fetcher.py --pair BTCUSDT --tf 5m --days 30   # Spesifik
python data_fetcher.py --check      # Cek isi database
```

### Pairs & Timeframes

- **Pairs:** BTCUSDT, ETHUSDT, XRPUSDT, YFIUSDT
- **Timeframes:** 1m, 3m, 5m, 15m, 1h

### Database

SQLite file `market_data.db` — portable, tinggal copy.

Schema: `klines` table dengan OHLCV + volume + trade count per candle.

### Deploy di Railway

1. Push ke GitHub repo
2. Bisa di-run sebagai cron job untuk daily update
3. Atau di-call dari backtesting engine nanti

### Next Steps

- **Step 1B:** Backtesting Core — engine yang simulate trading di atas data ini
- **Step 1C:** API Endpoint — `/backtest` endpoint yang bisa di-call Claude
