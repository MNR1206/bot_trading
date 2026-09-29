"""
Konfigurasi Bot Trading Saham Indonesia (IDX / BEI)
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Muat environment variables dari .env jika ada
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)


# ==============================================================================
# 1. ATURAN PASAR BURSA EFEK INDONESIA (IDX)
# ==============================================================================
LOT_SIZE = 100                  # 1 Lot = 100 Lembar saham
BUY_FEE_PCT = 0.0015            # Biaya Beli Sekuritas + IDX + PPN (~0.15%)
SELL_FEE_PCT = 0.0025           # Biaya Jual Sekuritas + IDX + PPh Final 0.1% (~0.25%)

# ==============================================================================
# 2. PARAMETER STRATEGI MOMENTUM & VOLUME SPIKE
# ==============================================================================
# Kriteria Volume Spike & Momentum
RVOL_THRESHOLD = 1.5            # Volume perdagangan minimal 1.5x rata-rata 20 hari
MIN_PRICE_CHANGE_PCT = 1.5      # Kenaikan harga minimal +1.5% pada hari sinyal
MIN_TURNOVER_IDR = 2_000_000_000 # Minimal nilai transaksi Rp 2 Miliar (filter saham tidak likuid)

# Parameter Moving Average & Indikator
MA_FAST = 10
MA_SLOW = 20
MA_TREND = 50
RSI_PERIOD = 14
RSI_OVERBOUGHT = 75
RSI_OVERSOLD = 35

# Target Profit & Stop Loss Default
DEFAULT_TP1_PCT = 3.0           # Target Profit 1: +3%
DEFAULT_TP2_PCT = 5.0           # Target Profit 2: +5%
DEFAULT_TP3_PCT = 8.0           # Target Profit 3: +8%
DEFAULT_SL_PCT = 3.0            # Stop Loss Default: -3%
TRAILING_STOP_PCT = 2.0         # Trailing Stop: 2% dari titik tertinggi setelah profit

# ==============================================================================
# 3. PENGATURAN PAPER TRADING (AKUN VIRTUAL)
# ==============================================================================
INITIAL_BALANCE = 50_000_000    # Saldo modal awal simulasi: Rp 50.000.000
MAX_ALLOCATION_PER_STOCK = 0.20 # Maksimal alokasi 20% modal per saham (diversifikasi)
PORTFOLIO_FILE = Path(__file__).resolve().parent / "portfolio.json"

# ==============================================================================
# 4. PENGATURAN NOTIFIKASI TELEGRAM
# ==============================================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
ENABLE_TELEGRAM = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)

# ==============================================================================
# 5. WATCHLIST SAHAM IDX (KOMPAS100 / LQ45 / SAHAM POPULER)
# ==============================================================================
# Saham likuid dengan volatilitas dan volume transaksi sehat di BEI
DEFAULT_WATCHLIST = [
    # Perbankan (Big Banks)
    "BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "BRIS.JK", "BBTN.JK", "ARTO.JK",
    # Komoditas, Energi & Tambang
    "ADRO.JK", "PTBA.JK", "ITMG.JK", "MEDC.JK", "PGAS.JK", "AKRA.JK", 
    "ANTM.JK", "INCO.JK", "MDKA.JK", "MBMA.JK", "HRUM.JK", "BUMI.JK", "DEWA.JK",
    # Konglomerasi & Industri
    "ASII.JK", "AMMN.JK", "BREN.JK", "TPIA.JK", "BRPT.JK", "UNTR.JK", "PANI.JK", "CUAN.JK",
    # Consumer Goods & Farmasi
    "ICBP.JK", "INDF.JK", "MYOR.JK", "KLBF.JK", "CPIN.JK", "JPFA.JK", "SIDO.JK", "UNVR.JK",
    # Telekomunikasi & Teknologi
    "TLKM.JK", "ISAT.JK", "EXCL.JK", "GOTO.JK", "BUKA.JK", "EMTK.JK",
    # Semen, Properti & Infrastruktur
    "SMGR.JK", "INTP.JK", "BSDE.JK", "CTRA.JK", "PWON.JK", "JSMR.JK",
    # Ritel & Kertas
    "ACES.JK", "ERAA.JK", "MAPI.JK", "MAPA.JK", "INKP.JK", "TKIM.JK"
]

def format_idr(amount: float) -> str:
    """Format angka menjadi representasi Rupiah (contoh: Rp 5.250)"""
    return f"Rp {amount:,.0f}".replace(",", ".")
