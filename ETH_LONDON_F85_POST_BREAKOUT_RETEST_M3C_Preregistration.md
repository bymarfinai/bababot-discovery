# ETH London F85 — Post-Breakout Retest Audit M3C

**Status: PREREGISTERED before result-bearing execution.**

## Tujuan
Lanjutkan tepat dari hasil M3B dan audit hanya kasus ETH London F85 yang sudah:
1. breakout High dengan close 5 menit di atas High;
2. belum mencapai E20;
3. lalu kembali close di bawah High sebelum E20.

Pertanyaan M3C hanya:
- dari kasus tersebut, berapa yang akhirnya tetap mencapai E20 sebelum sesi berakhir;
- seberapa dalam retest setelah kembali masuk ke bawah High;
- dari yang tidak mencapai E20, berapa yang sempat breakout lagi dan berapa yang tidak pernah breakout lagi.

## Frozen cohort
Input wajib dari `ETH_LONDON_F85_BREAKOUT_SEQUENCE_M3B_Cases.csv`.
Hanya major partitions (`external`, `development`, `reference_validation`) dan hanya `post_breakout_path == BACK_IN_RANGE_BEFORE_E20`.
Expected pooled cohort dari M3B = 48 kasus. Identitas kasus tidak boleh ditambah/dikurangi berdasarkan outcome M3C.

## Frozen levels
- High = H reference yang sama dari corrected M2/M3B.
- Range = H-L.
- E20 = H + 0.20*Range.

## Chronology
Untuk setiap kasus:
1. mulai dari candle breakout M3B;
2. cari candle pertama setelah breakout yang close < High sebelum E20; ini adalah titik `back_in_range`;
3. mulai dari candle itu sampai execution end, observasi path tanpa mengubah cohort;
4. `eventual_E20 = True` jika high menyentuh E20 pada candle mana pun setelah `back_in_range` dan sebelum execution end;
5. `confirmed_rebreak = True` jika ada close > High setelah `back_in_range` sebelum/equal candle E20 atau sebelum execution end bila E20 tidak pernah tercapai.

## Kedalaman retest
Untuk tiap kasus hitung minimum low dari candle `back_in_range` sampai:
- candle E20 inclusive jika eventual E20;
- execution end jika tidak eventual E20.

Ubah ke fraction range `(low-L)/(H-L)` dan kelompokkan sederhana:
- `0-5% below High`: minimum >= 0.95;
- `5-10% below High`: 0.90 <= minimum < 0.95;
- `10-15% below High`: 0.85 <= minimum < 0.90;
- `>15% below High`: minimum < 0.85.

## Outputs
Persist one-row-per-case audit plus summary:
- total cohort;
- eventual E20 count/rate;
- median minutes from back-in-range to eventual E20;
- eventual E20 by retest-depth bucket;
- among non-E20 cases: confirmed rebreak but still no E20 vs never confirmed rebreak;
- period stability for external/development/reference_validation.

## Guardrails
- descriptive structural audit only;
- no new clock, entry, stop, filter, fee, PnL, leverage, or live change;
- no redefinition of breakout or E20;
- same-bar E20 touch is counted as E20 touch regardless of close because this milestone studies eventual structural reach, not executable entry/exit ordering;
- raw 5m coverage >=99.5%;
- stop after M3C result persistence; no automatic next milestone.
