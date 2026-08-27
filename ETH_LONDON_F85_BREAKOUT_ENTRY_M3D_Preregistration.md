# ETH London F85 — Breakout Entry Trading Test M3D

**Status: PREREGISTERED before result-bearing execution.**

## Tujuan
Mengubah hasil struktur M3B/M3C menjadi satu uji trading yang bisa menghasilkan WR aktual tanpa optimasi parameter.

Cohort hanya ETH London F85 yang pada M3B mempunyai confirmed breakout High dengan close 5 menit di atas High.

## Frozen setup
- Pair: ETHUSDT perpetual.
- Reference: London 08:00-13:30 UTC.
- Execution: New York 13:30-20:00 UTC.
- F85 setup identity harus berasal dari corrected M2.
- Confirmed breakout identity harus sama persis dengan M3B.
- Major partitions: external, development, reference_validation.

## Entry
- Entry pada OPEN candle 5 menit berikutnya setelah confirmed breakout.
- Jika open entry sudah >= E20, trade dilewati karena target sudah berada di bawah/di harga entry.
- Tidak ada limit-order hindsight, tidak ada entry pada harga breakout close.

## Target dan invalidasi
- High = H reference yang sama.
- Range = H-L.
- Target E20 = H + 0.20*Range.
- Batas invalidasi F35 = L + 0.35*Range.
- Setelah entry, E20 tercapai bila high candle >= E20.
- Invalidasi terjadi bila completed 5m close < F35; exit pada close candle tersebut.
- Bila E20 dan close < F35 terjadi pada candle yang sama, E20 diprioritaskan agar konsisten dengan baseline BTC fixed-E20 lineage.
- Bila belum selesai sampai execution end, exit pada first available 5m open at/after execution end.

## Economics
- Illustrative notional: $500 per trade.
- Round-trip fee: $0.40.
- Baseline tanpa slippage.
- Satu sensitivitas tambahan: 5 bps adverse slippage pada entry dan exit/target.
- Tidak ada leverage dependency.

## Output
Per periode dan pooled major:
- jumlah trade;
- win / loss;
- WR;
- profit factor;
- net PnL;
- expectancy per trade;
- max consecutive loss;
- breakdown exit target / invalidasi / akhir sesi;
- 5 bps sensitivity.

## Guardrails
- Tidak ada parameter sweep.
- Tidak ada pemilihan stop/target baru setelah melihat hasil.
- Tidak ada clock/filter/entry redesign.
- Tidak ada perubahan live BBC.
- Raw 5m coverage >=99.5%.
- Stop setelah hasil M3D dipersist; jangan lanjut milestone berikut otomatis.
