# 🤖 Bot Trading Saham Indonesia (IDX / BEI) - Edisi Pro

Aplikasi bot trading kuantitatif modular untuk Bursa Efek Indonesia (IDX) yang berfokus pada strategi **Momentum & Volume Spike Accumulation**. Dilengkapi dengan fitur **Screener Otomatis**, **Backtesting Engine Historis**, **Simulasi Akun Paper Trading (Virtual Rupiah)**, **Grafik Candlestick Visual**, **Price Alert**, **Deteksi Bandarmology**, dan integrasi **Bot Telegram Interaktif 2-Arah**.

---

## 🌟 Fitur-Fitur Unggulan

1. **📊 Grafik Candlestick Visual Otomatis (`/chart <KODE>`)**:
   - Menghasilkan dan mengirimkan gambar grafik candlestick berlatar gelap (*dark mode*) langsung ke Telegram.
   - Dilengkapi garis tren **MA20 & MA50**, garis **Entry**, batas hijau **Target TP (+5%)**, batas merah **Stop Loss (-3%)**, serta bar volume.

2. **🚨 Alarm Pengingat Harga / Price Alert (`/alert <KODE> <HARGA>`)**:
   - Pasang alarm harga untuk saham incaran (contoh: `/alert BBCA 6000`).
   - Bot otomatis memantau harga setiap 30 detik dan membunyikan alarm instan begitu target tersentuh!

3. **🌐 Analisis Arus Dana & Bandarmology (`/flow <KODE>`)**:
   - Mendeteksi aliran dana pemain besar (*Smart Money / Bandar*):
     - **Chaikin Money Flow (CMF 20)**: Mengukur tekanan akumulasi/distribusi.
     - **On-Balance Volume (OBV)** & arah tren akumulasi.
     - **Skor Akumulasi (0 - 100)**: Menentukan status *Akumulasi Masif*, *Netral*, atau *Distribusi/Dumping*.

4. **⭐ Watchlist Saham Favorit Pribadi (`/watch` & `/watchlist`)**:
   - Simpan saham-saham pilihan pribadi Anda secara persisten.
   - Ketik `/watchlist` untuk memindai hanya saham-saham favorit Anda.

5. **🧮 Kalkulator Money Management & Lot Sizing (`/calc <KODE> <RISIKO>`)**:
   - Hitung ukuran lot ideal berdasarkan risiko rupiah yang siap Anda tanggung (contoh: `/calc BBCA 500000`).
   - Bot otomatis menghitung jarak Stop Loss, merekomendasikan jumlah lot maksimal, total modal yang dibutuhkan, dan potensi profit di TP2.

6. **🎯 Rekomendasi Area Beli & Stop Loss (SL) yang Presisi**:
   - Menghitung rentang harga masuk ideal (*Entry Zone*), level ketat cut loss (*Stop Loss*), dan target cuan bertahap (*TP1, TP2, TP3*).

7. **⏰ Auto-Scheduler Jam Buka Bursa (WIB)**:
   - Bot otomatis menyaring saham dan mengirim update ke Telegram setiap sesi bursa IDX dibuka:
     - **Sesi 1 Pagi:** 09:05 WIB
     - **Sesi 2 Siang:** 13:35 WIB *(Jumat: 14:05 WIB)*
     - **Pasar Tutup:** 16:05 WIB

8. **💼 Paper Trading Virtual Account (Rp 50.000.000)**:
   - Simulasi jual beli saham dengan aturan resmi BEI (**1 Lot = 100 lembar**), fee beli 0.15%, fee jual 0.25%, dan pengawalan otomatis Trailing Stop 2%.

---

## 📱 Daftar Perintah Chat Telegram (@bilnabil_bot)

| Perintah | Fungsi | Contoh Penggunaan |
| :--- | :--- | :--- |
| **`/start`** / **`/help`** | Buka menu navigasi & tombol klik interaktif | `/start` |
| **`/scan`** | Pindai saham IDX dengan lonjakan volume & SL/TP | `/scan` |
| **`/plan <KODE>`** | Lihat Trading Plan lengkap (Buy, SL, TP, RRR) | `/plan BBCA` |
| **`/chart <KODE>`** | Kirim gambar grafik candlestick + MA + TP/SL | `/chart BBCA` |
| **`/alert <KODE> <HARGA>`**| Pasang alarm pengingat harga otomatis | `/alert BBCA 6000` |
| **`/alerts`** | Lihat daftar alarm harga yang sedang aktif | `/alerts` |
| **`/delalert <ID>`** | Hapus alarm harga tertentu | `/delalert 1` |
| **`/flow <KODE>`** | Analisis arus dana asing & Bandarmology | `/flow BMRI` |
| **`/calc <KODE> <RISIKO>`**| Kalkulator ukuran lot ideal sesuai batas rugi | `/calc BBCA 500000` |
| **`/watch <KODE>`** | Tambah saham ke watchlist favorit pribadi | `/watch ANTM` |
| **`/unwatch <KODE>`** | Hapus saham dari watchlist | `/unwatch ANTM` |
| **`/watchlist`** | Pantau khusus saham-saham favorit Anda | `/watchlist` |
| **`/buy <KODE> <LOT> [TP] [SL]`** | Beli saham simulasi (kustom TP/SL opsional) | `/buy BBCA 5 5 3` |
| **`/sell <KODE> [LOT]`**| Jual saham dari portofolio simulasi | `/sell BBCA 5` |
| **`/portfolio`** | Cek saldo kas tunai & floating PnL saham | `/portfolio` |
| **`/update`** | Paksa kirim update kondisi bursa saat ini | `/update` |

---

## 🚀 Cara Menjalankan

### Menjalankan Bot Telegram Interaktif:
```powershell
python bot_telegram.py
```
*Bot akan aktif mendengarkan perintah dari Telegram, mengecek alarm harga setiap 30 detik, dan otomatis mengirim laporan saat bursa dibuka (09:05 & 13:35 WIB).*

### Menjalankan CLI Interaktif di Laptop:
```powershell
python main.py
```

### Menjalankan Screener Manual:
```powershell
python main.py --scan
```
