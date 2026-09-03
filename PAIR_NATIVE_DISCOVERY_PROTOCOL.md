# Pair-Native Strategy Discovery Protocol

## Purpose

Dokumen ini adalah **protokol riset reusable untuk menemukan strategi native setiap pair**.

Tujuannya **bukan** membuat ETH, SOL, BNB, atau pair lain meniru parameter BTC/SOL secara plek-ketiplek. Yang boleh diwariskan antar-pair adalah **cara berpikir, urutan eksperimen, definisi causal, quality gates, dan bentuk pertanyaan riset**. Angka seperti reference length, jam, visit number, entry location, stop, target, dan lifecycle **harus ditemukan ulang dari data pair tersebut**.

Prinsip inti:

> **Copy the discovery grammar, never copy the coordinates.**

Dengan kata lain, pair lain boleh meniru proses SOL dalam menemukan karakteristiknya, tetapi tidak boleh mengasumsikan bahwa SOL R240 / 18:00 / H1 / resting-H / E40 / H2 recovery juga benar untuk pair tersebut.

---

# 1. Apa yang Boleh dan Tidak Boleh Ditiru Antar-Pair

| Komponen | Boleh diwariskan? | Penjelasan |
|---|---|---|
| Strict causality | YA | Semua signal hanya memakai data yang sudah selesai tersedia pada saat keputusan dibuat. |
| Development / OOS partition | YA | Struktur validasi boleh sama. Tanggal menyesuaikan ketersediaan pair. |
| Normalisasi dengan `R = H-L` | YA | Membuat geometri dapat dibandingkan antar-regime dan antar-pair. |
| Visit grammar H1/H2/H3 atau L1/L2/L3 | YA | Definisi event boleh diwariskan. Visit dominan harus ditemukan ulang. |
| Leave / re-arm requirement | YA | Harus ada agar candle berdekatan tidak dihitung sebagai visit baru. Threshold-nya jangan otomatis disalin. |
| Reference length | TIDAK | Harus dikalibrasi dari pair. |
| Execution clock / zona waktu | TIDAK | Harus ditemukan dari pair. |
| H1 sebagai breakout utama | TIDAK | Pair lain mungkin H2/H3 atau tidak punya visit-order edge. |
| Resting entry di H | TIDAK | Pair lain mungkin lebih baik pullback, confirmed break, atau retest. |
| Target E40 | TIDAK | Target harus diturunkan dari extension distribution pair sendiri. |
| Stop / invalidation | TIDAK | Harus berasal dari loss anatomy pair sendiri. |
| H2 recovery | TIDAK | H2 hanya valid bila loss-recovery anatomy pair mendukungnya. |
| BTC/SOL WR/PF sebagai parameter | TIDAK | Hanya benchmark kualitas, bukan aturan konstruksi setup. |

---

# 2. Research Architecture dan Hygiene

## 2.1 Satu pair = satu research lineage

Setiap pair harus memiliki branch riset sendiri, misalnya:

- `research/btc-...`
- `research/eth-...`
- `research/sol-...`
- `research/bnb-...`

`main` tidak dipakai untuk eksplorasi aktif. `main` hanya menyimpan baseline yang bersih, metodologi yang sudah disepakati, atau setup yang memang sudah dipromosikan.

## 2.2 Preregistration sebelum result-bearing run

Sebelum eksperimen yang dapat menghasilkan keputusan:

1. tulis pertanyaan riset;
2. definisikan cohort/data;
3. definisikan event secara causal;
4. tentukan grid kecil yang memang diperlukan;
5. tentukan metric selection;
6. tentukan gate kelulusan;
7. baru jalankan data.

Jangan melihat OOS lalu menggeser threshold 5–10% untuk menyelamatkan hasil.

## 2.3 Pisahkan discovery dari validation

Default partition:

- **External**: data lama sebelum Development;
- **Development**: satu-satunya area untuk discovery/selection;
- **Reference Validation**: data lebih baru, dibuka hanya setelah candidate dibekukan;
- telemetry terbaru: observasi saja jika belum cukup matang sebagai validation cohort.

Jika pair baru listing belakangan, partition boleh disesuaikan tetapi fungsi masing-masing partition tidak boleh dicampur.

---

# 3. Stage 0 — Data Integrity dan Native Coordinate System

Sebelum mencari setup, pastikan datanya layak.

Minimum audit:

- timeframe coverage;
- missing bars;
- duplicate timestamp;
- timezone convention;
- listing start;
- extreme gaps / exchange anomalies;
- apakah OHLC yang dipakai futures/spot sesuai tujuan strategi.

Untuk struktur range, gunakan coordinate system native:

```text
Reference range = [L, H]
R = H - L
```

Semua displacement sebaiknya dinyatakan sebagai kelipatan `R`:

```text
+0.10R
-0.25R
+0.40R
```

Bukan langsung angka dollar/percentage tetap dari pair lain.

Alasannya: volatilitas SOL, BTC, ETH, BNB, dan regime 2022 vs 2026 berbeda.

---

# 4. Stage 1 — Cari Habitat / Karakteristik Pair

## Pertanyaan utama

> **Di lingkungan waktu dan reference seperti apa pair ini menghasilkan pressure/continuation yang repeatable?**

Jangan mulai dari entry.

Cari dulu habitatnya dengan controlled grid kecil seperti:

- beberapa reference length;
- beberapa clock/session;
- LONG dan SHORT dipisahkan;
- lifecycle yang cukup untuk mengamati event.

Contoh reference candidates boleh berupa 60m, 120m, 180m, 240m, dst., tetapi angka tersebut hanya search grid. Tidak boleh dianggap semua pair harus memakai angka yang sama.

### Metrics Stage 1

Untuk setiap `(reference length, clock)`:

- jumlah opportunity;
- reference range distribution;
- first pressure/touch frequency;
- visit count distribution;
- opposite-boundary failure rate;
- breakout / breakdown incidence;
- post-break extension distribution;
- stability per 6-month/year block.

### Yang dicari

Bukan parameter dengan satu metric paling tinggi, melainkan **habitat yang cukup sering, stabil, dan mempunyai continuation structure**.

Avoid:

> pilih R240 karena BTC/SOL pakai R240.

Correct:

> R240 dipilih hanya jika pair tersebut sendiri menunjukkan topology support dan behavior yang konsisten.

---

# 5. Stage 2 — Visit / Break Anatomy

Ini tahap untuk mengetahui **kapan resistance/support benar-benar berubah menjadi breakout/breakdown**.

## LONG terminology

```text
Reference -> H1 -> leave/retrace -> H2 -> leave/retrace -> H3 -> ...
```

## SHORT terminology

```text
Reference -> L1 -> leave/retrace -> L2 -> leave/retrace -> L3 -> ...
```

Jangan memakai label `H2` generik untuk SHORT jika event sebenarnya adalah return ke Low. Side-specific terminology menghindari objective bias.

## Distinct visit wajib causal

Beberapa candle berturut-turut menyentuh H tidak boleh dianggap H1, H2, H3.

Sebuah visit baru harus membutuhkan **leave / re-arm state** setelah visit sebelumnya. Definisi leave dapat menggunakan:

- retreat depth normalized by R;
- state transition tertentu;
- atau sensitivity family kecil yang sudah preregistered.

Tujuannya bukan memilih threshold ajaib, tetapi memastikan topology visit stabil.

## Metrics per visit `Hk` / `Lk`

- N mencapai visit k;
- first-break-at-visit-k count;
- first-break share;
- conditional break rate setelah mencapai visit k;
- false-break/reclaim rate;
- breakout latency;
- post-break extension Q25/Q50/Q75;
- E05/E10/E20/E30/E40/E50 hit rate;
- time-to-extension;
- stability per block;
- sample attrition.

## Metric yang harus dibedakan

**Conditional conversion**:

> jika sudah survive H1 dan sampai H2, berapa % H2 break?

berbeda dengan:

**Modal first-break visit**:

> dari seluruh first breakout, paling sering pecah di H1/H2/H3 mana?

Pair-native expansion point harus ditentukan dari **first-break anatomy**, bukan survivor denominator saja.

### Decision Stage 2

Freeze salah satu dari berikut:

- H1 breakout pair;
- H2 breakout pair;
- H3 breakout pair;
- multi-modal / unstable;
- no stable visit-order edge.

Jika tidak ada visit yang stabil, jangan paksa memilih. Kembali ke Stage 1 dan revisi habitat/reference grammar.

---

# 6. Stage 3 — Entry Anatomy Setelah Expansion Point Diketahui

Baru setelah expansion point dibekukan, tanyakan:

> **Di mana posisi masuk terbaik untuk memonetisasi expansion tersebut?**

Misalnya bila pair ternyata natural break di H3, entry candidates dapat mencakup:

1. setelah H1 leave;
2. retracement H1->H2;
3. setelah H2 rejection/turn;
4. H2->H3 pullback;
5. resting order di H sebelum H3;
6. next-open setelah confirmed H3 break;
7. post-break retest/reclaim.

Jika pair ternyata break di H1, candidates naturally berubah menjadi:

1. pre-H1 resting order;
2. H1 touch next-open;
3. confirmed H1 breakout next-open;
4. post-H1 retest/reclaim.

**Entry grid harus mengikuti karakter Stage 2, bukan template fixed.**

---

# 7. Stage 4 — Native Target Derivation

Jangan copy TP dari pair lain.

Ambil distribusi post-break extension dari pair sendiri:

```text
Q25 extension
Q35 extension
Q50 extension
Q65 extension
Q75 extension
```

Lalu map ke candidate target R yang sederhana dan preregistered.

Contoh konsep:

```text
median extension ~0.22R -> candidate E20
upper-mid extension ~0.43R -> candidate E40
```

Target dipilih berdasarkan **actual trade economics**, bukan extension hit-rate saja.

### Economics minimum

Untuk tiap entry × target:

- N;
- WR;
- gross profit;
- gross loss;
- PF;
- expectancy/trade;
- net PnL;
- max loss streak;
- frequency/week;
- adverse execution stress;
- block stability.

Penting:

> WR tinggi tidak otomatis bagus.

Target kecil dapat menghasilkan WR 80%+ tetapi tetap PF <1 karena loser terlalu besar.

---

# 8. Stage 5 — Freeze Parent Setup

Setelah Development memilih candidate yang lolos economics:

1. freeze reference;
2. freeze clock;
3. freeze visit structure;
4. freeze entry;
5. freeze target;
6. freeze lifecycle;
7. buka External + Reference Validation tanpa retuning.

Candidate hanya disebut **supported parent**, belum champion.

Contoh SOL saat dokumen ini dibuat hanyalah contoh penerapan:

```text
SOL menemukan habitat sendiri
-> first-break anatomy menunjukkan H1 dominan
-> entry economics menunjukkan pre-H1 resting-at-H lebih baik daripada menunggu confirmation
-> target diturunkan dari extension SOL sendiri
```

Pair lain tidak boleh mengambil kesimpulan `H1 + resting H` hanya karena SOL menemukan itu.

---

# 9. Stage 6 — Loss Anatomy

Setelah ada profitable parent setup, **jangan langsung optimize filter**.

Pertama bedah semua loser.

## Tujuan

> **Loss sebenarnya berbentuk apa, dan kelas mana yang menyumbang loss dollars terbesar?**

Taxonomy dapat mencakup:

- touch tetapi never-break;
- reference invalidation;
- time loss;
- break lalu fail <=5m;
- fail <=10m;
- fail <=30m;
- late failed-break;
- target near-miss;
- regime-specific failure.

### Metric yang wajib

Per loss class:

- N;
- share losers;
- **share gross-loss dollars**;
- median loss;
- median MFE;
- median MAE;
- median hold;
- time-to-break;
- time-to-failure;
- OOS replication.

Kenapa gross-loss share penting:

100 small losses dapat lebih tidak berbahaya daripada 20 tail losses yang menyumbang 60% total damage.

---

# 10. Stage 7 — Fixed Causal Snapshots

Untuk membedakan winner vs loser tanpa leakage, ambil snapshots setelah entry pada waktu yang sudah ditetapkan, misalnya:

```text
+5m
+10m
+15m
+30m
+60m
```

Ukur hanya informasi yang sudah tersedia saat snapshot:

- close vs H/L dalam R;
- running MFE;
- running MAE;
- breakout confirmed atau belum;
- jumlah closes di luar boundary;
- reclaim state;
- elapsed time.

Jangan membuat classifier dari future maximum/target outcome lalu menyebutnya causal.

---

# 11. Stage 8 — Convert Loss to Win: Recovery Anatomy

Setelah loss taxonomy diketahui, jangan menganggap semua loser adalah dead setup.

Pertanyaan berikutnya:

> **Trade yang sekarang loss ini benar-benar salah arah, atau hanya attempt pertamanya terlalu dini?**

Untuk setiap loss, setelah original trade sudah exit:

1. lanjutkan observasi secara causal;
2. cek apakah original target akhirnya tercapai;
3. catat visit mana yang menghasilkan recovery (`H2`, `H3`, `H4`, dst.);
4. ukur waktu recovery;
5. ukur apakah later visit entry tersedia **setelah original exit**;
6. simulasi recovery trade dengan rule yang sama-sama causal.

### Dua level recovery

**Latent recovery**

> harga akhirnya mencapai target.

Ini hanya anatomy, belum strategy.

**Economic rescue**

> `original loss + recovery trade PnL > 0`

Hanya economic rescue yang benar-benar mengubah loss episode menjadi WIN.

### Metrics

- recovery N;
- recovery WR;
- recovery PF;
- recovery expectancy;
- recovery net;
- rescue rate;
- 5bps PF;
- overlay PF/net;
- block stability;
- OOS replication.

### Guardrail

Recovery bukan martingale.

- maksimum jumlah retry harus terbatas;
- tidak boleh averaging overlapping positions tanpa prereg;
- jika H2 works tetapi H3/H4 decay, stop di H2;
- recovery lane harus profitable standalone atau setidaknya jelas meningkatkan episode economics secara robust.

---

# 12. Stage 9 — Separate Recoverable Loss from True Failure

Setelah recovery anatomy, loss dibagi dua:

## A. Recoverable failure

Contoh generic:

```text
H1 break -> failed break kecil -> H2 datang -> continuation
```

Treatment:

> exit attempt pertama, lalu re-arm pada native recovery visit yang terbukti.

## B. True failure

Contoh generic:

```text
H1 touch -> tidak establish breakout -> terus menjauh -> structure mati
```

Treatment:

> cari early invalidation, bukan terus retry.

Ini penting: objective bukan memaksa 100% loss menjadi winner.

Objective yang benar:

> **ubah sebanyak mungkin recoverable loser menjadi winner, dan ubah true failure dari big loss menjadi small loss.**

---

# 13. Stage 10 — Failure Boundary / Early Invalidation

Untuk true failures, cari **point of no return yang causal**.

Candidates harus berasal dari anatomy, misalnya kombinasi:

- elapsed time sejak touch;
- depth below/above boundary dalam R;
- belum pernah confirmed break;
- reclaim failure;
- repeated closes inside range;
- adverse excursion threshold;
- failure to re-attack within native latency.

Jangan langsung scan ratusan threshold.

Mulai dari quantile winner vs true-failure paths, lalu preregister family kecil.

### Goal

Bukan sekadar meningkatkan WR.

Gate intervention:

- preserved winners;
- gross loss reduction;
- PF improvement;
- expectancy improvement;
- OOS positive;
- 5bps positive;
- no catastrophic frequency collapse.

---

# 14. Stage 11 — Exit Efficiency / WR Improvement

Setelah entry + recovery + invalidation sudah matang, baru optimasi exit.

Pertanyaan:

> apakah sebagian near-winner bisa direalisasikan tanpa membunuh continuation payoff?

Candidates:

- E20 vs E40;
- partial E20 + runner E40;
- break-even transition setelah extension tertentu;
- trailing structure setelah breakout;
- time-based profit protection.

Jangan menurunkan target hanya untuk membuat WR terlihat tinggi.

Sebuah perubahan exit harus dinilai dengan:

```text
WR + PF + expectancy + net + OOS + stress
```

bukan WR sendirian.

---

# 15. Stage 12 — Multi-Clock / Multi-Zone Expansion

Setelah satu clock memiliki setup yang matang, baru cari zona waktu lain.

Tujuan:

> meningkatkan jumlah trade tanpa mengorbankan kualitas.

Tetapi setiap clock baru harus menjalani discovery mini-cycle:

```text
habitat -> visit anatomy -> entry -> economics -> loss anatomy -> validation
```

Jangan sekadar copy clock +1h / -1h dari setup utama.

Nearby clock boleh digunakan sebagai **topology support**, tetapi tidak otomatis menjadi second trading window.

Jika ingin Asia, London, NY, atau overlap session masing-masing menjadi production lane, masing-masing harus lulus gate sendiri.

---

# 16. Stage 13 — Robustness dan Stress

Sebelum promotion, minimal cek:

## Temporal

- External;
- Development;
- Reference Validation;
- 6-month/year blocks;
- regime changes.

## Topology

- nearby clock;
- nearby reference length;
- nearby non-magical geometry.

Tujuan topology test bukan mencari parameter baru yang lebih bagus, tetapi memastikan edge tidak hanya hidup pada satu titik koordinat yang rapuh.

## Economics stress

- 0bps primary;
- adverse execution/slippage stress;
- realistic round-trip fee;
- max losing streak;
- position sizing assumptions.

Jika edge hilang hanya karena perubahan sangat kecil, statusnya research-only.

---

# 17. Stage 14 — Promotion Gate

Sebuah pair setup baru boleh disebut candidate champion jika:

1. logic-nya causal;
2. Development profitable;
3. External profitable;
4. Reference Validation profitable;
5. major partitions PF > 1;
6. expectancy positive;
7. sample cukup;
8. frequency cukup;
9. stress masih masuk akal;
10. topology tidak runtuh;
11. loss behavior sudah dipahami;
12. tidak bergantung pada posthoc rescue;
13. live implementation belum dilakukan sampai research freeze selesai.

Benchmark pair lama boleh digunakan untuk menilai kualitas, tetapi tidak sebagai syarat agar geometri sama.

---

# 18. End-to-End Flow yang Harus Ditiru Pair Lain

```text
0. DATA AUDIT
   |
1. NATIVE HABITAT / CHARACTER
   |  reference length? clock? side?
   v
2. VISIT / BREAK ANATOMY
   |  H1/H2/H3...? L1/L2/L3...?
   v
3. FREEZE NATIVE EXPANSION POINT
   |
4. ENTRY ANATOMY
   |  before touch? pullback? confirmation? retest?
   v
5. NATIVE TARGET DERIVATION
   |
6. ACTUAL TRADE ECONOMICS
   |  WR / PF / expectancy / net / stress
   v
7. FREEZE PARENT SETUP
   |
8. OOS VALIDATION
   |
9. LOSS ANATOMY
   |  where do loss dollars come from?
   v
10. RECOVERY ANATOMY
    |  which losses can become wins?
    v
11. SELECTIVE RECOVERY
    |  H2/H3/etc only if pair supports it
    v
12. TRUE-FAILURE BOUNDARY
    |  big loss -> small loss
    v
13. EXIT EFFICIENCY
    |  improve WR without killing PF
    v
14. MULTI-CLOCK EXPANSION
    |  repeat mini-discovery per zone
    v
15. ROBUSTNESS / STRESS / PROMOTION
```

---

# 19. Standard Questions untuk Setiap Pair Baru

Gunakan urutan pertanyaan berikut.

## Character

1. Kapan pair paling sering membentuk pressure yang repeatable?
2. Reference range berapa lama yang paling coherent?
3. Apakah LONG dan SHORT memiliki karakter berbeda?
4. Apakah edge session-specific?

## Break structure

5. Break paling sering terjadi di visit ke berapa?
6. Apakah first-break visit stabil OOS?
7. Seberapa jauh extension setelah break?
8. Seberapa cepat reclaim/failure terjadi?

## Entry

9. Apakah entry terbaik sebelum attack, saat touch, setelah confirmation, atau retest?
10. Apakah menunggu confirmation justru membuat impulse sudah habis?

## Target

11. Berapa native continuation distribution pair?
12. Target mana yang menghasilkan PF/expectancy terbaik, bukan sekadar WR tertinggi?

## Loss

13. Loss paling banyak secara jumlah ada di mana?
14. Loss paling mahal secara dollars ada di mana?
15. Mana recoverable failure dan mana true failure?

## Recovery

16. Setelah loss, apakah target masih tercapai?
17. Recovery paling natural di visit ke berapa?
18. Apakah combined episode benar-benar berubah menjadi profit?
19. Kapan retry edge mulai decay?

## Invalidation

20. Pada titik apa probability continuation collapse secara causal?
21. Bisakah tail loss dipotong tanpa membunuh eventual winners?

## Validation

22. Apakah rule exact survive External?
23. Apakah survive recent Reference Validation?
24. Apakah survive fee/slippage stress?
25. Apakah nearby topology masih coherent?

---

# 20. Anti-Patterns yang Harus Dihindari

## Anti-pattern 1 — Copy BTC coordinates

Salah:

> BTC Rxxx bekerja, jadi SOL/ETH pakai Rxxx juga.

Benar:

> BTC membuktikan grammar tertentu bisa profitable; pair baru harus menemukan coordinate native-nya sendiri.

## Anti-pattern 2 — Optimize structural proxy instead of profit

Salah:

> pilih setup karena revisit H2/L2 rate paling tinggi.

Benar:

> revisit hanya diagnostics; promoted setup harus menghasilkan actual profitable continuation.

## Anti-pattern 3 — High WR worship

Salah:

> WR 85% berarti bagus.

Benar:

> cek PF, expectancy, gross loss, fee stress, dan tail loss.

## Anti-pattern 4 — Treat all losses equally

Salah:

> semua loss diberi stop lebih ketat atau semua loss di-retry.

Benar:

> bedakan recoverable failure vs true failure.

## Anti-pattern 5 — Infinite recovery

Salah:

> H1 gagal -> H2 -> H3 -> H4 terus sampai menang.

Benar:

> retry hanya pada visit yang mempunyai independently supported recovery economics.

## Anti-pattern 6 — OOS tuning

Salah:

> Reference Validation gagal sedikit, lalu ubah target dari 0.40R menjadi 0.37R.

Benar:

> freeze candidate, terima failure, buat experiment baru jika ada hypothesis baru.

---

# 21. Minimal Output Files per Stage

Suggested naming convention:

```text
PAIR_<SIDE>_<STAGE>_Preregistration.md
PAIR_<SIDE>_<STAGE>_Result.md
PAIR_<SIDE>_<STAGE>_TRADES.csv
PAIR_<SIDE>_<STAGE>_Status.txt
research/pair_<side>_<stage>.py
.github/workflows/pair-<side>-<stage>.yml
```

Setiap result harus mencatat:

- parent lineage;
- exact frozen rule;
- data coverage;
- Development result;
- OOS result;
- stress result;
- decision/status;
- apa yang **tidak** boleh disimpulkan dari eksperimen tersebut.

---

# 22. SOL sebagai Contoh Proses, Bukan Template Parameter

SOL LONG restarted lineage memperlihatkan bagaimana protocol ini bekerja:

```text
Visit anatomy
-> menemukan modal first-break H1

Entry economics
-> menemukan entry sebelum confirmation lebih efektif daripada post-break entry

Loss anatomy
-> menemukan mayoritas gross loss berasal dari never-break tail, bukan small false-break losses

Recovery anatomy
-> menemukan sebagian failed H1 masih mempunyai profitable second chance pada later visit

Next
-> pisahkan recoverable loss dan true failure
-> cari failure boundary
-> improve episode WR/PF
```

Pelajaran yang boleh dibawa ke pair lain adalah **urutan discovery tersebut**.

Yang tidak boleh dibawa:

```text
H1 pasti terbaik
resting-H pasti terbaik
E40 pasti terbaik
H2 recovery pasti terbaik
clock SOL pasti cocok
R SOL pasti cocok
```

Pair baru harus menghasilkan jawabannya sendiri dari data.

---

# 23. Core Research Objective

Semua stage akhirnya harus kembali ke objective berikut:

> **Temukan karakter pair secara causal, monetisasi expansion point native-nya, ubah recoverable losses menjadi winners, kecilkan true failures, dan pertahankan hasil tersebut di OOS serta execution stress.**

Bukan mencari chart pattern yang kelihatan rapi.

Bukan mencari H/WR tertinggi sebagai proxy.

Bukan memaksa satu formula universal.

Target akhirnya adalah **pair-specific profitable grammar dengan discovery process yang universal dan reproducible**.
