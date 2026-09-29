# 🤖 Bot Trading Saham Indonesia (IDX / BEI)

Aplikasi bot trading kuantitatif modular untuk Bursa Efek Indonesia (IDX) yang berfokus pada strategi **Momentum & Volume Spike Scanner**. Dilengkapi dengan fitur **Screener Otomatis**, **Backtesting Engine Historis**, **Simulasi Akun Paper Trading (Virtual Rupiah)**, dan integrasi **Notifikasi Telegram Bot**.

---

## 🌟 Fitur Utama

1. **🔍 Screener Saham IDX Real-Time / EOD**:
   - Pemindaian multi-threaded super cepat pada puluhan hingga ratusan saham likuid (LQ45, IDX30, Kompas100).
   - Deteksi lonjakan volume akumulasi (**Relative Volume / RVol $\ge 1.5\times$** rata-rata 20 hari).
   - Konfirmasi momentum harga positif ($\ge +1.5\%$), tren di atas MA20, dan breakout resistance 20 hari.
   - Filter likuiditas ketat (Turnover transaksi harian $\ge$ Rp 2 Miliar) untuk menghindari saham tidak likuid atau "gorengan" berisiko tinggi.

2. **📊 Mesin Backtesting Realistis**:
   - Simulasi strategi pada data historis saham IDX (1 bulan hingga 2 tahun).
   - Memperhitungkan aturan bursa nyata: satuan **1 Lot = 100 Lembar**, biaya beli sekuritas (0.15%), dan biaya jual + PPh Final (0.25%).
   - Metrik finansial komprehensif: **Win Rate (%)**, **Net Profit (Rp & %)**, **Profit Factor**, **Maximum Drawdown (%)**, dan log transaksi detail.

3. **💼 Paper Trading Portfolio (Simulasi Akun Virtual)**:
   - Modal awal virtual: **Rp 50.000.000** (dapat diubah sesuai preferensi).
   - Manajemen posisi terbuka (Open Positions) dan riwayat transaksi (Trade History) yang tersimpan permanen di `portfolio.json`.
   - Pengawalan otomatis dengan **Target Take Profit (+5%)**, **Stop Loss (-3%)**, dan **Trailing Stop dinamis (2%)**.

4. **📱 Notifikasi Telegram Interaktif**:
   - Kirim alert langsung ke smartphone saat sinyal beli (BUY/STRONG BUY) terdeteksi.
   - Notifikasi eksekusi order beli dan jual paper trading lengkap dengan detail harga, lot, dan realized PnL.

---

## 📁 Struktur Direktori

```
bot_trading/
├── config.py             # Konfigurasi parameter strategi, watchlist IDX, fee bursa, & token Telegram
├── data_provider.py      # Pengambil data harga saham IDX (Yahoo Finance) dengan in-memory caching
├── strategy.py           # Algoritma perhitungan indikator (RVol, MA, RSI, ATR) & sinyal Momentum
├── screener.py           # Pemindai saham paralel multi-threading & tabel hasil
├── backtester.py         # Mesin simulasi historis & evaluasi performa strategi
├── paper_trader.py       # Manajer portofolio virtual (Beli, Jual, Auto-update TP/SL, Saldo Rupiah)
├── telegram_notifier.py  # Modul pengiriman notifikasi via Telegram Bot API
├── main.py               # Antarmuka CLI interaktif & pemantau otomatis (Monitoring Loop)
├── portfolio.json        # Database lokal portofolio virtual (dibuat otomatis)
├── requirements.txt      # Daftar dependensi Python
├── .env.example          # Contoh template konfigurasi token Telegram
└── README.md             # Dokumentasi panduan lengkap
```

---

## 🚀 Cara Menjalankan

### 1. Instalasi Dependensi
Pastikan Python 3.10+ sudah terinstal di komputer Anda, lalu jalankan:
```bash
pip install -r requirements.txt
```

### 2. Menjalankan Menu Interaktif (CLI Utama)
Jalankan file `main.py` untuk membuka menu navigasi lengkap:
```bash
python main.py
```

Tampilan menu utama:
```
╔═══════════════════════════════════════════════════════════════╗
║         🤖 BOT TRADING SAHAM INDONESIA (IDX / BEI)           ║
║       Strategi: Momentum & Volume Spike Accumulation          ║
║      Fitur: Screener + Backtest + Paper Trading + Telegram    ║
╚═══════════════════════════════════════════════════════════════╝

Silakan pilih menu:
  [1] 🔍 Jalankan Screener Saham Momentum & Volume Spike (LQ45 / Populer)
  [2] 📊 Backtest Strategi pada Saham Historis (Uji Win Rate & PnL)
  [3] 💼 Lihat Portofolio Paper Trading (Virtual Account)
  [4] 🛒 Beli Saham (Paper Trading Order)
  [5] 💰 Jual Saham (Paper Trading Order)
  [6] 🔄 Cek & Update TP / SL / Trailing Stop Posisi Terbuka
  [7] 🤖 Jalankan Auto-Monitoring Loop (Pemantau Otomatis Berkala)
  [8] 📱 Cek Status & Tes Notifikasi Telegram
  [9] ⚙️  Reset Saldo Portofolio Paper Trading
  [0] ❌ Keluar
```

---

## ⚡ Perintah Cepat (Direct CLI Flags)

Anda juga dapat menjalankan perintah bot secara langsung tanpa melalui menu interaktif:

* **Menjalankan Screener Saham:**
  ```bash
  python main.py --scan
  ```

* **Menjalankan Backtest Saham Tertentu (misal: BBCA, ANTM, BRIS, MEDC):**
  ```bash
  python main.py --backtest BBCA
  python main.py --backtest ANTM
  ```

* **Melihat Status Portofolio Paper Trading:**
  ```bash
  python main.py --portfolio
  ```

* **Menjalankan Pemantau Otomatis (Auto-Monitoring Loop setiap 60 detik):**
  ```bash
  python main.py --monitor --interval 60
  ```

---

## 📲 Panduan Konfigurasi Notifikasi Telegram

Untuk menerima alert sinyal di HP melalui Telegram:

1. Buka aplikasi Telegram dan cari bot **`@BotFather`**.
2. Ketik `/newbot`, ikuti petunjuk, lalu salin **HTTP API Token** yang diberikan.
3. Cari bot **`@userinfobot`** di Telegram untuk melihat **Chat ID** akun Anda.
4. Buat file baru bernama `.env` di dalam folder `bot_trading` (atau salin dari `.env.example`):
   ```env
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRstuVWXyz
   TELEGRAM_CHAT_ID=987654321
   ```
5. Buka `main.py` -> pilih menu **[8]** untuk menguji koneksi dan memastikan pesan tes masuk ke Telegram Anda.

---

## 📐 Aturan & Mekanisme Bursa Efek Indonesia (IDX)

Bot ini telah disesuaikan dengan regulasi perdagangan saham di Indonesia:
- **Satuan Lot**: 1 Lot = 100 Lembar saham. Pembelian harus berupa kelipatan 100 lembar.
- **Biaya Beli**: Disimulasikan 0.15% (Biaya broker + pungutan bursa/levy + PPN).
- **Biaya Jual**: Disimulasikan 0.25% (Biaya broker + levy + PPN + PPh Final 0.1%).
- **Ticker Yahoo Finance**: Simbol saham otomatis dikonversi dengan akhiran `.JK` (contoh: `BBCA` otomatis menjadi `BBCA.JK`).

---

## ⚠️ Disclaimer
Aplikasi ini ditujukan untuk analisis teknikal, edukasi kuantitatif, dan simulasi strategi trading. Segala keputusan transaksi investasi di pasar modal adalah tanggung jawab pribadi masing-masing (Do Your Own Research / DYOR).
