# ETH London F85 — Post-Breakout Retest Audit M3C — Result

Raw ETH 5-minute coverage: **100.0000%**.
Kasus yang diaudit: **48** — semuanya adalah breakout yang kemudian kembali tutup di bawah High sebelum E20 pada M3B.

## Apakah setelah balik masuk range masih bisa lanjut?

| Hasil setelah kembali di bawah High | Jumlah | Persentase |
|---|---:|---:|
| Akhirnya tetap mencapai E20 | 29 | 60.4% |
| Tidak mencapai E20 sampai sesi selesai | 19 | 39.6% |

Median waktu dari retest terkonfirmasi sampai E20, untuk yang recover: **50 menit**.

## Jalurnya setelah retest

| Jalur | Jumlah | % dari 48 kasus |
|---|---:|---:|
| Breakout lagi dengan close 5 menit, lalu mencapai E20 | 29 | 60.4% |
| E20 tersentuh tanpa sempat close 5 menit breakout lagi | 0 | 0.0% |
| Sempat breakout lagi, tapi tetap tidak mencapai E20 | 9 | 18.8% |
| Tidak pernah breakout lagi dan tidak mencapai E20 | 10 | 20.8% |

## Seberapa dalam retest-nya?

| Kedalaman turun dari High | Jumlah kasus | Yang akhirnya mencapai E20 | Peluang recover |
|---|---:|---:|---:|
| 0-5% dari range di bawah High | 0 | 0 | - |
| 5-10% dari range di bawah High | 4 | 4 | 100.0% |
| 10-15% dari range di bawah High | 7 | 3 | 42.9% |
| >15% dari range di bawah High | 37 | 22 | 59.5% |

## Konsistensi per periode

| Periode | Kasus balik masuk range | Akhirnya E20 | Persentase |
|---|---:|---:|---:|
| 2020-2021 | 16 | 9 | 56.2% |
| 2022-2024 | 20 | 12 | 60.0% |
| 2025-Jul 2026 | 12 | 8 | 66.7% |
| Semua periode utama | 48 | 29 | 60.4% |

Catatan konservatif: **3** kasus sempat menyentuh E20 pada candle yang sama saat pertama kali close kembali di bawah High. Touch tersebut tidak dihitung sebagai recovery, karena urutan intrabar tidak diketahui; recovery baru dihitung mulai candle berikutnya.

**Status: ETH_LONDON_F85_POST_BREAKOUT_RETEST_M3C_COMPLETED**

Audit struktur saja. Tidak ada perubahan live, entry, stop, target, filter, atau parameter trading. Stop setelah M3C.
