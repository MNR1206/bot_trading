"""
Modul Pengambil Data Saham IDX (Yahoo Finance)
"""
import time
import pandas as pd
import yfinance as yf
from typing import Optional, Dict, Any, Tuple

# In-memory cache sederhana untuk mencegah request berulang ke Yahoo Finance
_DATA_CACHE: Dict[str, Tuple[float, pd.DataFrame]] = {}
CACHE_EXPIRY_SECONDS = 300  # 5 menit

def normalize_ticker(ticker: str) -> str:
    """
    Memastikan ticker berakhiran .JK untuk Bursa Efek Indonesia.
    Contoh: 'BBCA' -> 'BBCA.JK', 'bbri.jk' -> 'BBRI.JK'
    """
    ticker = ticker.strip().upper()
    if not ticker.endswith(".JK"):
        ticker += ".JK"
    return ticker

def get_clean_symbol(ticker: str) -> str:
    """Menghilangkan suffix .JK untuk tampilan antarmuka (misal: 'BBCA.JK' -> 'BBCA')"""
    return ticker.strip().upper().replace(".JK", "")

def get_stock_data(ticker: str, period: str = "6mo", interval: str = "1d", force_refresh: bool = False) -> pd.DataFrame:
    """
    Mengambil data riwayat harga (OHLCV) saham dari Yahoo Finance.
    
    Args:
        ticker: Simbol saham (contoh: 'BBCA' atau 'BBCA.JK')
        period: Rentang waktu ('1mo', '3mo', '6mo', '1y', '2y')
        interval: Interval candle ('1d', '1wk', '1h', '15m')
        force_refresh: Jika True, lewati cache
        
    Returns:
        pd.DataFrame dengan kolom: ['Open', 'High', 'Low', 'Close', 'Volume']
    """
    symbol = normalize_ticker(ticker)
    cache_key = f"{symbol}_{period}_{interval}"
    now = time.time()
    
    if not force_refresh and cache_key in _DATA_CACHE:
        cached_time, cached_df = _DATA_CACHE[cache_key]
        if now - cached_time < CACHE_EXPIRY_SECONDS:
            return cached_df.copy()
            
    try:
        t = yf.Ticker(symbol)
        df = t.history(period=period, interval=interval, auto_adjust=True)
        
        if df.empty or len(df) < 5:
            return pd.DataFrame()
            
        # Standardisasi kolom
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
        
        # Konversi tipe data
        for col in ['Open', 'High', 'Low', 'Close']:
            df[col] = df[col].astype(float)
        df['Volume'] = df['Volume'].astype(float)
        
        _DATA_CACHE[cache_key] = (now, df)
        return df.copy()
    except Exception as e:
        # Fallback jika terjadi error
        return pd.DataFrame()

def get_current_price(ticker: str) -> Optional[float]:
    """
    Mengambil harga terkini (penutupan terakhir) saham.
    """
    df = get_stock_data(ticker, period="5d")
    if df.empty:
        return None
    return float(df['Close'].iloc[-1])

def get_ticker_summary(ticker: str) -> Dict[str, Any]:
    """
    Mengambil ringkasan data emiten (harga terkini, volume, perubahan %, dll)
    """
    symbol = normalize_ticker(ticker)
    df = get_stock_data(symbol, period="1mo")
    
    if df.empty or len(df) < 2:
        return {
            "symbol": get_clean_symbol(symbol),
            "ticker": symbol,
            "valid": False,
            "error": "Data historis tidak tersedia"
        }
        
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    close_price = float(last_row['Close'])
    prev_close = float(prev_row['Close'])
    change_pt = close_price - prev_close
    change_pct = (change_pt / prev_close) * 100 if prev_close else 0.0
    volume = float(last_row['Volume'])
    turnover = close_price * volume
    
    return {
        "symbol": get_clean_symbol(symbol),
        "ticker": symbol,
        "valid": True,
        "last_price": close_price,
        "prev_close": prev_close,
        "change_pt": change_pt,
        "change_pct": round(change_pct, 2),
        "volume": int(volume),
        "turnover": turnover,
        "high": float(last_row['High']),
        "low": float(last_row['Low']),
        "open": float(last_row['Open']),
        "date": str(df.index[-1].date())
    }
