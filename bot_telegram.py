"""
Bot Telegram Interaktif Super Lengkap Saham Indonesia (IDX / BEI)
Fitur-Fitur Lengkap:
- /start & /help: Menampilkan menu & tombol navigasi interaktif
- /scan: Memindai saham IDX dengan lonjakan volume & momentum
- /plan <KODE>: Trading Plan lengkap (Area Beli, Stop Loss, Target TP1/TP2, Risk:Reward)
- /chart <KODE>: 📊 Mengirim gambar grafik candlestick dengan MA, TP, SL langsung ke chat Telegram!
- /alert <KODE> <HARGA>: 🚨 Memasang alarm pengingat harga otomatis
- /alerts & /delalert <ID>: Melihat dan menghapus alarm harga aktif
- /flow <KODE> atau /bandar <KODE>: 🌐 Analisis arus dana asing / Bandarmology & Money Flow (CMF & OBV)
- /watch <KODE> & /unwatch <KODE>: ⭐ Mengelola daftar saham pantauan favorit pribadi
- /watchlist atau /mywatch: Memindai khusus saham-saham pilihan pribadi Anda
- /calc <KODE> <RISIKO_RP>: 🧮 Kalkulator Money Management & ukuran lot ideal sesuai toleransi risiko
- /buy <KODE> <LOT> [TP%] [SL%]: Membeli saham simulasi (Paper Trading)
- /sell <KODE> [LOT]: Menjual saham simulasi
- /portfolio: Menampilkan ringkasan saldo & posisi saham virtual
- Background Scheduler:
  1. Memantau alarm harga setiap 30 detik (notifikasi instan saat harga menyentuh target)
  2. Otomatis kirim update ke Telegram setiap jam bursa dibuka (09:05 WIB & 13:35/14:05 WIB) & tutup (16:05 WIB)!
"""
import os
import sys
import time
import threading
from datetime import datetime, timezone, timedelta
import requests
from typing import Dict, Any, Optional, List

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import config
from config import format_idr, DEFAULT_TP2_PCT, DEFAULT_SL_PCT
from data_provider import get_current_price, get_clean_symbol, get_ticker_summary
from screener import run_screener
from strategy import get_trading_plan
from paper_trader import (
    load_portfolio, buy_stock, sell_stock, update_and_check_portfolio,
    display_portfolio_summary
)
from telegram_notifier import get_credentials, send_telegram_message, send_telegram_photo
from chart_generator import generate_candlestick_chart
from alert_manager import add_price_alert, get_user_alerts, delete_price_alert, check_all_alerts
from bandarmology import analyze_bandarmology
from watchlist_manager import add_to_watchlist, remove_from_watchlist, get_user_watchlist

# Timezone WIB (UTC + 7)
WIB = timezone(timedelta(hours=7))

def get_now_wib() -> datetime:
    return datetime.now(WIB)

def send_reply(chat_id: str, text: str, reply_markup: Optional[Dict[str, Any]] = None):
    token, _ = get_credentials()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        print(f"Error send_reply: {e}")

def handle_start(chat_id: str, first_name: str):
    welcome_msg = f"""
👋 *Halo {first_name}!* 
Selamat datang di *Bot Trading Saham Indonesia (IDX / BEI) Super Lengkap* 🤖📈

Bot ini dilengkapi kecerdasan analisis kuantitatif, grafis visual, alarm harga, dan deteksi arus dana besar (Bandarmology).

📋 *Menu Perintah Lengkap:*
  • `/scan` - 🔍 Pindai saham IDX dengan lonjakan volume & momentum
  • `/plan <KODE>` - 🎯 Trading Plan lengkap (Area Beli, Stop Loss & TP)
  • `/chart <KODE>` - 📊 Kirim gambar grafik Candlestick + MA + TP/SL
  • `/alert <KODE> <HARGA>` - 🚨 Pasang alarm pengingat harga (contoh: `/alert BBCA 6000`)
  • `/alerts` - 📋 Lihat daftar alarm harga aktif
  • `/flow <KODE>` - 🌐 Cek arus dana asing & Bandarmology (contoh: `/flow BBRI`)
  • `/calc <KODE> <RISIKO>` - 🧮 Kalkulator Lot Ideal (contoh: `/calc BBCA 500000`)
  • `/watch <KODE>` - ⭐ Tambah saham ke pantauan favorit Anda
  • `/watchlist` - 🌟 Pantau khusus saham-saham favorit Anda
  • `/buy <KODE> <LOT> [TP%] [SL%]` - 🛒 Beli saham di akun simulasi
  • `/sell <KODE> [LOT]` - 💰 Jual saham di akun simulasi
  • `/portfolio` - 💼 Cek saldo & posisi saham virtual
  • `/update` - 🔔 Paksa kirim update pasar bursa saat ini
  • `/help` - ℹ️ Tampilkan panduan ini kembali

⏰ *Update Otomatis Jam Bursa:* 09:05 WIB | 13:35 WIB | 16:05 WIB

_Klik tombol cepat di bawah untuk mencoba fitur favorit:_
"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🔍 Scan Saham & SL/TP", "callback_data": "btn_scan"},
                {"text": "💼 Cek Portofolio", "callback_data": "btn_portfolio"}
            ],
            [
                {"text": "📊 Chart BBCA", "callback_data": "btn_chart_BBCA"},
                {"text": "📊 Chart BBRI", "callback_data": "btn_chart_BBRI"},
                {"text": "🌐 Flow BMRI", "callback_data": "btn_flow_BMRI"}
            ],
            [
                {"text": "🎯 Plan BBCA", "callback_data": "btn_plan_BBCA"},
                {"text": "⭐ Watchlist Saya", "callback_data": "btn_watchlist"},
                {"text": "🔔 Update Pasar", "callback_data": "btn_update_now"}
            ]
        ]
    }
    send_reply(chat_id, welcome_msg.strip(), reply_markup=keyboard)

def handle_chart_cmd(chat_id: str, symbol: str):
    """
    Menghasilkan dan mengirimkan gambar grafik candlestick langsung ke chat Telegram
    """
    sym = get_clean_symbol(symbol)
    send_reply(chat_id, f"⏳ *Sedang merender chart candlestick untuk {sym}...*")
    
    chart_file = generate_candlestick_chart(sym)
    if not chart_file or not os.path.exists(chart_file):
        send_reply(chat_id, f"❌ Gagal membuat chart untuk `{sym}`. Pastikan simbol saham benar.")
        return
        
    plan = get_trading_plan(sym)
    caption = f"""
📊 *GRAFIK CANDLESTICK: {sym} (IDX)*
━━━━━━━━━━━━━━━━━━━━
💵 *Harga Now:* `{format_idr(plan['close'])}` ({plan['change_pct']:+.2f}%)
🛒 *Area Beli (Entry):* `{format_idr(plan['buy_min'])} - {format_idr(plan['buy_max'])}`
🛑 *Stop Loss (SL):* `{format_idr(plan['sl_price'])}` (-{plan['sl_pct']:.1f}%)
🎯 *Target TP 2:* `{format_idr(plan['tp2'])}` (+5.0%)
⚖️ *Risk/Reward:* `1 : {plan['rrr']}`
━━━━━━━━━━━━━━━━━━━━
"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": f"🛒 Beli 1 Lot {sym}", "callback_data": f"btn_buy_{sym}_1"},
                {"text": f"🛒 Beli 5 Lot {sym}", "callback_data": f"btn_buy_{sym}_5"},
                {"text": f"🛒 Beli 10 Lot {sym}", "callback_data": f"btn_buy_{sym}_10"}
            ],
            [
                {"text": f"🌐 Bandarmology {sym}", "callback_data": f"btn_flow_{sym}"},
                {"text": f"🎯 Plan Detail", "callback_data": f"btn_plan_{sym}"}
            ]
        ]
    }
    
    success = send_telegram_photo(chart_file, caption=caption.strip(), reply_markup=keyboard)
    if not success:
        send_reply(chat_id, "⚠️ Gagal mengirim file gambar ke Telegram. Coba ulangi beberapa saat lagi.")

def handle_plan_cmd(chat_id: str, symbol: str):
    """
    Menampilkan Trading Plan lengkap: Area Beli, Stop Loss (SL), Target Profit (TP), dan Risk:Reward
    """
    sym = get_clean_symbol(symbol)
    send_reply(chat_id, f"⏳ *Menghitung Trading Plan untuk {sym}...*")
    
    plan = get_trading_plan(sym)
    if not plan.get("valid"):
        send_reply(chat_id, f"❌ Gagal memuat data `{sym}`: {plan.get('error', 'Saham tidak ditemukan')}")
        return
        
    signal_badge = "🔥 STRONG BUY" if plan['signal'] == 'STRONG BUY' else ("🟢 BUY" if plan['signal'] == 'BUY' else "⚪ NEUTRAL")
    chg_badge = "🟢" if plan['change_pct'] >= 0 else "🔴"
    
    msg = f"""
🎯 *TRADING PLAN SAHAM: {plan['symbol']}*
━━━━━━━━━━━━━━━━━━━━
📊 *Status Pasar:* {signal_badge}
💵 *Harga Terkini:* `{format_idr(plan['close'])}` ({chg_badge} {plan['change_pct']:+.2f}%)
📈 *RVol:* `{plan['rvol']}x` | *RSI:* `{plan['rsi']}`

🛒 *REKOMENDASI BELI (ENTRY ZONE):*
  • *Area Beli*  : `{format_idr(plan['buy_min'])} - {format_idr(plan['buy_max'])}`
  • *Ideal Entry*: `{format_idr(plan['buy_entry_ideal'])}`

🛑 *BATAS RISIKO (STOP LOSS):*
  • *Stop Loss (SL)*: `{format_idr(plan['sl_price'])}` (-{plan['sl_pct']:.1f}%)
  ⚠️ *Wajib Cut Loss jika harga tembus ke bawah `{format_idr(plan['sl_price'])}`*

🎯 *TARGET TAKE PROFIT (TP):*
  • *Target TP 1* : `{format_idr(plan['tp1'])}` (+3.0%)
  • *Target TP 2* : `{format_idr(plan['tp2'])}` (+5.0%)
  • *Target TP 3* : `{format_idr(plan['tp3'])}` (+8.0%)

⚖️ *Risk to Reward Ratio:* `1 : {plan['rrr']}`
🧱 *Support Terdekat:* `{format_idr(plan['support'])}`
🏢 *Resistance:* `{format_idr(plan['resistance'])}`
━━━━━━━━━━━━━━━━━━━━
"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": f"📊 Lihat Chart {plan['symbol']}", "callback_data": f"btn_chart_{plan['symbol']}"},
                {"text": f"🌐 Cek Bandar {plan['symbol']}", "callback_data": f"btn_flow_{plan['symbol']}"}
            ],
            [
                {"text": f"🛒 Beli 1 Lot {plan['symbol']}", "callback_data": f"btn_buy_{plan['symbol']}_1"},
                {"text": f"🛒 Beli 5 Lot {plan['symbol']}", "callback_data": f"btn_buy_{plan['symbol']}_5"},
                {"text": f"🛒 Beli 10 Lot {plan['symbol']}", "callback_data": f"btn_buy_{plan['symbol']}_10"}
            ]
        ]
    }
    send_reply(chat_id, msg.strip(), reply_markup=keyboard)

def handle_bandarmology_cmd(chat_id: str, symbol: str):
    """
    Menampilkan analisis arus dana besar / Bandarmology & Money Flow
    """
    sym = get_clean_symbol(symbol)
    send_reply(chat_id, f"⏳ *Menganalisis arus dana & akumulasi bandar {sym}...*")
    
    flow = analyze_bandarmology(sym)
    if not flow.get("valid"):
        send_reply(chat_id, f"❌ Gagal memuat data bandarmology untuk `{sym}`.")
        return
        
    obv_str = "🟢 Uptrend (Akumulasi Berjalan)" if flow['is_obv_uptrend'] else "🔴 Downtrend (Tekanan Jual)"
    cmf_str = f"+{flow['cmf']:.3f}" if flow['cmf'] >= 0 else f"{flow['cmf']:.3f}"
    
    msg = f"""
🌐 *ANALISIS ARUS DANA & BANDARMOLOGY: {flow['symbol']}*
━━━━━━━━━━━━━━━━━━━━
🏆 *Skor Akumulasi:* `{flow['score']}/100`
📊 *Status:* {flow['status']}
💡 *Sentimen:* _{flow['sentiment']}_

📈 *Indikator Aliran Dana:*
  • *Chaikin Money Flow (CMF):* `{cmf_str}`
    _(> +0.05 = Inflow Uang Besar | < -0.05 = Outflow)_
  • *Tren OBV (Volume Akumulasi):* {obv_str}
  • *Relative Volume (RVol):* `{flow['rvol']}x`
  • *Turnover Hari Ini:* `{format_idr(flow['turnover'])}`
  • *Performa 5 Hari:* `{flow['change_5d']:+.2f}%`
━━━━━━━━━━━━━━━━━━━━
"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": f"📊 Chart {sym}", "callback_data": f"btn_chart_{sym}"},
                {"text": f"🎯 Trading Plan {sym}", "callback_data": f"btn_plan_{sym}"}
            ]
        ]
    }
    send_reply(chat_id, msg.strip(), reply_markup=keyboard)

def handle_alert_cmd(chat_id: str, args: list):
    """
    Format: /alert <KODE> <HARGA>
    Contoh: /alert BBCA 6000
    """
    if len(args) < 2:
        send_reply(chat_id, "⚠️ *Format salah!*\nGunakan: `/alert <KODE> <HARGA_TARGET>`\nContoh: `/alert BBCA 6000` atau `/alert BBRI 3200`")
        return
        
    sym = args[0].upper()
    try:
        price = float(args[1].replace(".", "").replace(",", ""))
    except ValueError:
        send_reply(chat_id, "⚠️ Target harga harus berupa angka. Contoh: `/alert BBCA 6000`")
        return
        
    res = add_price_alert(sym, price, chat_id)
    send_reply(chat_id, res["message"])

def handle_alerts_list_cmd(chat_id: str):
    """Menampilkan daftar alarm harga yang sedang aktif"""
    alerts = get_user_alerts(chat_id)
    if not alerts:
        send_reply(chat_id, "ℹ️ Anda belum memiliki alarm harga yang aktif.\nPasang alarm dengan: `/alert <KODE> <HARGA>` (contoh: `/alert BBCA 6000`).")
        return
        
    msg = "🚨 *DAFTAR ALARM HARGA AKTIF:*\n━━━━━━━━━━━━━━━━━━━━\n"
    for a in alerts:
        cond_badge = "Naik ke ≥" if a["condition"] == "GTE" else "Turun ke ≤"
        msg += f"• *ID #{a['id']}* : `{a['symbol']}` {cond_badge} `{format_idr(a['target_price'])}`\n  _Dibuat di harga: {format_idr(a['created_price'])}_\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n_Untuk menghapus alarm, ketik: `/delalert <ID>` (contoh: `/delalert 1`)_"
    send_reply(chat_id, msg.strip())

def handle_delalert_cmd(chat_id: str, args: list):
    """Format: /delalert <ID>"""
    if not args or not args[0].isdigit():
        send_reply(chat_id, "⚠️ Masukkan ID alarm yang ingin dihapus. Contoh: `/delalert 1`\nKetik `/alerts` untuk melihat daftar ID.")
        return
    alert_id = int(args[0])
    res = delete_price_alert(alert_id, chat_id)
    send_reply(chat_id, res["message"])

def handle_watch_cmd(chat_id: str, symbol: str):
    """Format: /watch <KODE>"""
    if not symbol:
        send_reply(chat_id, "⚠️ Masukkan kode saham. Contoh: `/watch ANTM`")
        return
    res = add_to_watchlist(symbol, chat_id)
    send_reply(chat_id, res["message"])

def handle_unwatch_cmd(chat_id: str, symbol: str):
    """Format: /unwatch <KODE>"""
    if not symbol:
        send_reply(chat_id, "⚠️ Masukkan kode saham. Contoh: `/unwatch ANTM`")
        return
    res = remove_from_watchlist(symbol, chat_id)
    send_reply(chat_id, res["message"])

def handle_watchlist_cmd(chat_id: str):
    """Memindai saham-saham pilihan di watchlist pribadi user"""
    user_list = get_user_watchlist(chat_id)
    if not user_list:
        send_reply(chat_id, "ℹ️ Watchlist pribadi Anda masih kosong.\nTambahkan saham favorit dengan: `/watch <KODE>` (contoh: `/watch BBCA`).")
        return
        
    send_reply(chat_id, f"⭐ *Memindai {len(user_list)} saham favorit di Watchlist Anda...*")
    results = run_screener(watchlist=user_list, send_telegram=False, show_all=True)
    
    reply = f"⭐ *HASIL PANTAUAN WATCHLIST PRIBADI ANDA:*\n━━━━━━━━━━━━━━━━━━━━\n"
    for s in results:
        close = s['close']
        sl = round(close * 0.97)
        tp = round(close * 1.05)
        buy_min = round(close * 0.99)
        buy_max = round(close * 1.005)
        reply += f"""
📌 *{s['symbol']}* ({s['signal']})
💵 Harga Now: `{format_idr(close)}` ({s['change_pct']:+.2f}%) | RVol: `{s['rvol']:.2f}x`
🛒 *Area Beli* : `{format_idr(buy_min)} - {format_idr(buy_max)}`
🛑 *Stop Loss*  : `{format_idr(sl)}` (-3.0%)
🎯 *Target TP*  : `{format_idr(tp)}` (+5.0%)
────────────────────
"""
    reply += "_Ketik `/chart KODE` untuk grafik atau `/plan KODE` untuk detail._"
    send_reply(chat_id, reply.strip())

def handle_calc_cmd(chat_id: str, args: list):
    """
    Kalkulator Money Management:
    Format: /calc <KODE> <RISIKO_RUPIAH>
    Contoh: /calc BBCA 500000 (Siap rugi maksimal Rp 500.000 jika kena SL)
    """
    if len(args) < 2:
        send_reply(chat_id, "⚠️ *Format salah!*\nGunakan: `/calc <KODE> <MAX_RISIKO_RP>`\nContoh: `/calc BBCA 500000`\n_(Artinya Anda siap rugi maksimal Rp 500.000 jika terkena Stop Loss)_")
        return
        
    sym = args[0].upper()
    try:
        max_risk_rp = float(args[1].replace(".", "").replace(",", ""))
    except ValueError:
        send_reply(chat_id, "⚠️ Nominal risiko harus berupa angka. Contoh: `/calc BBCA 500000`")
        return
        
    plan = get_trading_plan(sym)
    if not plan.get("valid"):
        send_reply(chat_id, f"❌ Gagal memuat data `{sym}`.")
        return
        
    entry = plan["close"]
    sl = plan["sl_price"]
    tp2 = plan["tp2"]
    
    # Jarak risiko per lembar & per lot
    risk_per_share = max(entry - sl, 1)
    risk_per_lot = risk_per_share * 100 # 1 lot = 100 lembar
    
    # Hitung rekomendasi lot maksimal
    recommended_lots = max(int(max_risk_rp // risk_per_lot), 1)
    shares = recommended_lots * 100
    total_modal = shares * entry
    
    potential_loss = shares * risk_per_share
    potential_profit = shares * (tp2 - entry)
    
    msg = f"""
🧮 *KALKULATOR MONEY MANAGEMENT: {sym}*
━━━━━━━━━━━━━━━━━━━━
🎯 *Toleransi Risiko Anda:* `{format_idr(max_risk_rp)}`

📊 *Parameter Trading Plan:*
  • *Harga Beli (Entry):* `{format_idr(entry)}`
  • *Stop Loss (SL):* `{format_idr(sl)}` (-{plan['sl_pct']:.1f}%)
  • *Target TP 2:* `{format_idr(tp2)}` (+5.0%)
  • *Jarak Risiko per Lot:* `{format_idr(risk_per_lot)}` / lot

💡 *REKOMENDASI UKURAN POSISI (LOT SIZING):*
  📦 *Maksimal Beli:* `{recommended_lots} Lot` ({shares:,} lembar)
  💸 *Total Modal Masuk:* `{format_idr(total_modal)}`
  
  🛑 *Maksimal Kerugian (Jika kena SL):* `{format_idr(potential_loss)}`
  🟢 *Potensi Keuntungan (Jika kena TP2):* `+{format_idr(potential_profit)}`
  ⚖️ *Risk to Reward:* `1 : {plan['rrr']}`
━━━━━━━━━━━━━━━━━━━━
_Klik tombol di bawah untuk langsung membeli sesuai ukuran ideal di atas:_
"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": f"🛒 Beli {recommended_lots} Lot {sym}", "callback_data": f"btn_buy_{sym}_{recommended_lots}"},
                {"text": f"📊 Lihat Chart {sym}", "callback_data": f"btn_chart_{sym}"}
            ]
        ]
    }
    send_reply(chat_id, msg.strip(), reply_markup=keyboard)

def handle_scan_cmd(chat_id: str, header_prefix: str = ""):
    """
    Memindai saham IDX dan menampilkan hasil lengkap dengan Area Beli dan Stop Loss.
    """
    if not header_prefix:
        send_reply(chat_id, "⏳ *Sedang memindai saham-saham likuid IDX...*\n_Menghitung Area Beli, Target TP, dan Stop Loss..._")
        
    results = run_screener(send_telegram=False, show_all=False)
    buy_signals = [r for r in results if r.get('has_signal', False)]
    
    title = f"{header_prefix}\n" if header_prefix else ""
    
    if buy_signals:
        reply = f"{title}🎉 *HASIL SCREENER: DITEMUKAN SINYAL MOMENTUM BUY!* 🚀\n━━━━━━━━━━━━━━━━━━━━\n"
        for sig in buy_signals[:5]:
            buy_min = round(sig['close'] * 0.99)
            buy_max = round(sig['close'] * 1.005)
            reply += f"""
📌 *{sig['symbol']}* ({sig['signal']})
💵 Harga: `{format_idr(sig['close'])}` ({sig['change_pct']:+.2f}%) | RVol: `{sig['rvol']}x`
🛒 *Area Beli (Entry)*: `{format_idr(buy_min)} - {format_idr(buy_max)}`
🛑 *Stop Loss (SL)*   : `{format_idr(sig['sl'])}` (-3.0%)
🎯 *Target TP 1*       : `{format_idr(sig['tp1'])}` (+3.0%)
🎯 *Target TP 2*       : `{format_idr(sig['tp2'])}` (+5.0%)
⚖️ *Risk/Reward*      : `1 : {sig['rrr']}`
━━━━━━━━━━━━━━━━━━━━
"""
        reply += "💡 _Ketik `/chart KODE` untuk grafik atau `/buy KODE LOT` untuk membeli._"
    else:
        top_stocks = sorted(results, key=lambda x: x.get('rvol', 0), reverse=True)[:4]
        reply = f"{title}ℹ️ *PEMANTAUAN SAHAM LIKUID IDX TERAKTIF*\n_Belum ada breakout momentum agresif saat ini. Berikut panduan Buy & SL saham bervolume tinggi:_ \n━━━━━━━━━━━━━━━━━━━━\n"
        for s in top_stocks:
            close = s['close']
            sl = round(close * 0.97)
            tp = round(close * 1.05)
            buy_min = round(close * 0.99)
            buy_max = round(close * 1.005)
            reply += f"""
📌 *{s['symbol']}* (RVol: `{s['rvol']:.2f}x` | RSI: `{s['rsi']}`)
💵 Harga Now: `{format_idr(close)}` ({s['change_pct']:+.2f}%)
🛒 *Area Beli* : `{format_idr(buy_min)} - {format_idr(buy_max)}`
🛑 *Stop Loss*  : `{format_idr(sl)}` (-3.0%)
🎯 *Target TP*  : `{format_idr(tp)}` (+5.0%)
────────────────────
"""
        reply += "💡 _Ketik `/chart KODE` untuk grafik atau `/plan KODE` untuk detail._"
        
    send_reply(chat_id, reply.strip())

def handle_price_cmd(chat_id: str, symbol: str):
    handle_plan_cmd(chat_id, symbol)

def handle_portfolio_cmd(chat_id: str):
    portfolio = load_portfolio()
    cash = portfolio.get("cash_balance", 0.0)
    initial = portfolio.get("initial_balance", 50_000_000)
    positions = portfolio.get("positions", {})
    
    total_market_val = 0.0
    pos_lines = []
    
    for sym, pos in positions.items():
        curr_price = get_current_price(pos["ticker"]) or pos["avg_price"]
        shares = pos["shares"]
        val = shares * curr_price * 0.9975 # net sell
        unrealized = val - pos["total_cost"]
        pnl_pct = (unrealized / pos["total_cost"]) * 100 if pos["total_cost"] else 0
        total_market_val += val
        
        pnl_badge = "🟢" if unrealized >= 0 else "🔴"
        tp_price = pos.get('tp_price', round(pos['avg_price'] * 1.05))
        sl_price = pos.get('sl_price', round(pos['avg_price'] * 0.97))
        
        pos_lines.append(
            f"{pnl_badge} *{sym}*: {pos['lots']} Lot @ `{format_idr(pos['avg_price'])}`\n"
            f"   Now: `{format_idr(curr_price)}` | PnL: `{format_idr(unrealized)}` ({pnl_pct:+.2f}%)\n"
            f"   🎯 TP: `{format_idr(tp_price)}` | 🛑 SL: `{format_idr(sl_price)}`"
        )
        
    total_assets = cash + total_market_val
    overall_pnl = total_assets - initial
    overall_pct = (overall_pnl / initial) * 100
    
    msg = f"""
💼 *PORTOFOLIO PAPER TRADING IDX*
━━━━━━━━━━━━━━━━━━━━
💰 *Kas Tunai:* `{format_idr(cash)}`
📈 *Nilai Saham:* `{format_idr(total_market_val)}`
🏆 *Total Aset:* `{format_idr(total_assets)}`
📊 *Total Return:* `{format_idr(overall_pnl)}` ({overall_pct:+.2f}%)
━━━━━━━━━━━━━━━━━━━━
*Posisi Terbuka:*
"""
    if pos_lines:
        msg += "\n\n".join(pos_lines)
    else:
        msg += "_(Tidak ada posisi saham aktif. 100% Kas Tunai)_"
        
    send_reply(chat_id, msg.strip())

def handle_buy_cmd(chat_id: str, args: list):
    """
    Format: /buy <KODE> <LOT> [TP%] [SL%]
    Contoh: /buy BBCA 5
    Contoh: /buy BBCA 5 7 3
    """
    if len(args) < 2:
        send_reply(chat_id, "⚠️ *Format salah!*\nGunakan: `/buy <KODE> <LOT> [TP%] [SL%]`\n\n*Contoh:* \n• `/buy BBCA 5` (Default TP +5%, SL -3%)\n• `/buy BBCA 5 7 4` (Kustom TP +7%, SL -4%)")
        return
        
    sym = args[0].upper()
    try:
        lots = int(args[1])
    except ValueError:
        send_reply(chat_id, "⚠️ Jumlah lot harus berupa angka bulat.")
        return
        
    tp_pct = float(args[2]) if len(args) > 2 and args[2].replace('.', '', 1).isdigit() else DEFAULT_TP2_PCT
    sl_pct = float(args[3]) if len(args) > 3 and args[3].replace('.', '', 1).isdigit() else DEFAULT_SL_PCT
        
    res = buy_stock(sym, lots=lots, tp_pct=tp_pct, sl_pct=sl_pct)
    if res["success"]:
        send_reply(
            chat_id,
            f"✅ *ORDER BELI BERHASIL DIEKSEKUSI!*\n━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 *Saham:* `{res['symbol']}`\n"
            f"📦 *Jumlah:* `{res['lots']} Lot` ({res['shares']} lembar)\n"
            f"💵 *Harga Beli (Entry):* `{format_idr(res['price'])}`\n"
            f"💸 *Total Modal:* `{format_idr(res['total_cost'])}`\n\n"
            f"🛑 *Stop Loss (SL) Aktif:* `{format_idr(res['sl_price'])}` (-{sl_pct:.1f}%)\n"
            f"🎯 *Take Profit (TP) Aktif:* `{format_idr(res['tp_price'])}` (+{tp_pct:.1f}%)\n"
            f"🛡️ *Trailing Stop:* Aktif di 2.0%\n"
            f"💰 *Sisa Saldo Kas:* `{format_idr(res['remaining_cash'])}`\n━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        send_reply(chat_id, f"❌ Gagal: {res['message']}")

def handle_sell_cmd(chat_id: str, args: list):
    if len(args) < 1:
        send_reply(chat_id, "⚠️ Format salah. Gunakan: `/sell <KODE_SAHAM> [JUMLAH_LOT]`\nContoh: `/sell BBCA` (jual semua) atau `/sell BBCA 2`")
        return
    sym = args[0].upper()
    lots = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    
    res = sell_stock(sym, lots=lots)
    if res["success"]:
        pnl_badge = "🟢 PROFIT" if res.get('net_pnl', 0) >= 0 else "🔴 LOSS"
        send_reply(
            chat_id,
            f"✅ *ORDER JUAL BERHASIL DIEKSEKUSI! ({pnl_badge})*\n━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 *Saham:* `{res['symbol']}` ({res['lots']} Lot)\n"
            f"💵 *Harga Jual:* `{format_idr(res['sell_price'])}`\n"
            f"💸 *Total Diterima:* `{format_idr(res['net_revenue'])}`\n"
            f"📊 *Realized PnL:* `{format_idr(res['net_pnl'])}` ({res['pnl_pct']:+.2f}%)\n"
            f"💰 *Sisa Saldo Kas:* `{format_idr(res['remaining_cash'])}`\n━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        send_reply(chat_id, f"❌ Gagal: {res['message']}")

def process_callback_query(query: Dict[str, Any]):
    chat_id = str(query.get("message", {}).get("chat", {}).get("id"))
    data = query.get("data", "")
    
    token, _ = get_credentials()
    try:
        requests.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery", json={"callback_query_id": query.get("id")}, timeout=5)
    except Exception:
        pass
        
    if data == "btn_scan":
        handle_scan_cmd(chat_id)
    elif data == "btn_portfolio":
        handle_portfolio_cmd(chat_id)
    elif data == "btn_watchlist":
        handle_watchlist_cmd(chat_id)
    elif data.startswith("btn_plan_"):
        sym = data.replace("btn_plan_", "")
        handle_plan_cmd(chat_id, sym)
    elif data.startswith("btn_chart_"):
        sym = data.replace("btn_chart_", "")
        handle_chart_cmd(chat_id, sym)
    elif data.startswith("btn_flow_"):
        sym = data.replace("btn_flow_", "")
        handle_bandarmology_cmd(chat_id, sym)
    elif data.startswith("btn_buy_"):
        # Format: btn_buy_BBCA_5
        parts = data.split("_")
        if len(parts) >= 4:
            sym = parts[2]
            lots = int(parts[3])
            handle_buy_cmd(chat_id, [sym, str(lots)])
    elif data == "btn_update_now":
        handle_scan_cmd(chat_id, header_prefix="🔔 *UPDATE PASAR SAHAM IDX SAAT INI*")

# ==============================================================================
# BACKGROUND SCHEDULER: MONITOR HARGA, ALARM, DAN JAM BURSA
# ==============================================================================
def on_alert_triggered(alert: Dict[str, Any], current_price: float):
    cond_str = "telah naik melampaui" if alert["condition"] == "GTE" else "telah turun menyentuh"
    msg = f"""
🚨 *[PRICE ALERT TERPICU!]* ⏰
━━━━━━━━━━━━━━━━━━━━
📌 *Saham:* `{alert['symbol']}`
💵 *Target Harga:* `{format_idr(alert['target_price'])}`
⚡ *Kondisi:* {cond_str} level target!
📈 *Harga Terkini:* `{format_idr(current_price)}`
━━━━━━━━━━━━━━━━━━━━
_Ketik `/plan {alert['symbol']}` untuk melihat aksi trading plan atau `/buy {alert['symbol']} <LOT>`._
"""
    send_reply(alert["chat_id"], msg.strip())

def background_monitoring_loop():
    """
    Loop pemantau latar belakang:
    1. Memeriksa Price Alert setiap 30 detik
    2. Mengirim update otomatis setiap jam buka/tutup bursa IDX
    """
    token, chat_id = get_credentials()
    if not token or not chat_id:
        return
        
    print("⏰ [SCHEDULER] Background monitoring loop aktif (Alarm harga & Jam bursa)...")
    last_triggered_key = ""
    
    while True:
        try:
            # 1. Cek Alarm Harga
            check_all_alerts(on_alert_triggered)
            
            # 2. Cek Jadwal Jam Bursa (WIB)
            now = get_now_wib()
            weekday = now.weekday()
            hour = now.hour
            minute = now.minute
            
            if weekday < 5:
                # Sesi 1 Buka: 09:05 WIB
                if hour == 9 and 5 <= minute <= 10:
                    slot_key = f"{now.date()}_sesi1_open"
                    if last_triggered_key != slot_key:
                        last_triggered_key = slot_key
                        header = f"🔔 *[UPDATE BURSA IDX: SESI 1 RESMI DIBUKA - {now.strftime('%H:%M')} WIB]* 🚀\n_Pasar saham baru saja dimulai. Berikut pantauan saham momentum, Area Beli, dan batas Stop Loss:_"
                        handle_scan_cmd(chat_id, header_prefix=header)

                # Sesi 2 Buka: 13:35 WIB (Senin-Kamis) atau 14:05 WIB (Jumat)
                is_sesi2_open = (weekday < 4 and hour == 13 and 35 <= minute <= 40) or (weekday == 4 and hour == 14 and 5 <= minute <= 10)
                if is_sesi2_open:
                    slot_key = f"{now.date()}_sesi2_open"
                    if last_triggered_key != slot_key:
                        last_triggered_key = slot_key
                        header = f"🔔 *[UPDATE BURSA IDX: SESI 2 RESMI DIBUKA - {now.strftime('%H:%M')} WIB]* 📈\n_Perdagangan sesi siang dimulai. Berikut saham dengan akumulasi volume terbesar:_"
                        handle_scan_cmd(chat_id, header_prefix=header)

                # Penutupan Pasar: 16:05 WIB
                if hour == 16 and 5 <= minute <= 10:
                    slot_key = f"{now.date()}_market_close"
                    if last_triggered_key != slot_key:
                        last_triggered_key = slot_key
                        header = f"🔔 *[EOD: PENUTUPAN BURSA EFEK INDONESIA - {now.strftime('%H:%M')} WIB]* 🏁\n_Ringkasan penutupan pasar hari ini & saham terbaik untuk watchlist besok:_"
                        handle_scan_cmd(chat_id, header_prefix=header)
                        
            time.sleep(30)
        except Exception as e:
            print(f"⚠️ Error scheduler loop: {e}")
            time.sleep(30)

def start_interactive_listener():
    """
    Menjalankan background long-polling untuk merespons perintah Telegram secara realtime.
    """
    token, chat_id = get_credentials()
    if not token or not chat_id:
        print("❌ Token Telegram atau Chat ID belum dikonfigurasi.")
        return

    # Mulai thread scheduler & alarm di background
    sched_thread = threading.Thread(target=background_monitoring_loop, daemon=True)
    sched_thread.start()

    print(f"🤖 Bot Telegram @bilnabil_bot sedang aktif mendengarkan perintah...")
    print("⏰ Fitur Lengkap: Chart, Price Alert, Bandarmology, Watchlist, & Money Management aktif!")
    print("Tekan Ctrl+C untuk menghentikan.\n")
    
    offset = None
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates?timeout=20"
            if offset:
                url += f"&offset={offset}"
                
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                time.sleep(3)
                continue
                
            updates = resp.json().get("result", [])
            for u in updates:
                offset = u.get("update_id", 0) + 1
                
                if "callback_query" in u:
                    process_callback_query(u["callback_query"])
                    continue
                    
                msg = u.get("message", {})
                sender_chat_id = str(msg.get("chat", {}).get("id"))
                text = msg.get("text", "").strip()
                first_name = msg.get("from", {}).get("first_name", "Trader")
                
                if not text:
                    continue
                    
                parts = text.split()
                cmd = parts[0].lower()
                cmd_args = parts[1:]
                
                if cmd in ["/start", "/help", "start", "help", "menu"]:
                    handle_start(sender_chat_id, first_name)
                elif cmd in ["/scan", "scan"]:
                    handle_scan_cmd(sender_chat_id)
                elif cmd.startswith("/chart"):
                    sym = cmd_args[0] if cmd_args else "BBCA"
                    handle_chart_cmd(sender_chat_id, sym)
                elif cmd.startswith("/plan"):
                    sym = cmd_args[0] if cmd_args else "BBCA"
                    handle_plan_cmd(sender_chat_id, sym)
                elif cmd.startswith("/price"):
                    sym = cmd_args[0] if cmd_args else "BBCA"
                    handle_price_cmd(sender_chat_id, sym)
                elif cmd.startswith("/flow") or cmd.startswith("/bandar"):
                    sym = cmd_args[0] if cmd_args else "BBCA"
                    handle_bandarmology_cmd(sender_chat_id, sym)
                elif cmd.startswith("/calc"):
                    handle_calc_cmd(sender_chat_id, cmd_args)
                elif cmd.startswith("/alert") and not cmd.startswith("/alerts"):
                    handle_alert_cmd(sender_chat_id, cmd_args)
                elif cmd in ["/alerts", "alerts"]:
                    handle_alerts_list_cmd(sender_chat_id)
                elif cmd.startswith("/delalert"):
                    handle_delalert_cmd(sender_chat_id, cmd_args)
                elif cmd.startswith("/watch") and not cmd.startswith("/watchlist"):
                    sym = cmd_args[0] if cmd_args else ""
                    handle_watch_cmd(sender_chat_id, sym)
                elif cmd.startswith("/unwatch"):
                    sym = cmd_args[0] if cmd_args else ""
                    handle_unwatch_cmd(sender_chat_id, sym)
                elif cmd in ["/watchlist", "/mywatch", "watchlist", "mywatch"]:
                    handle_watchlist_cmd(sender_chat_id)
                elif cmd in ["/update", "update"]:
                    handle_scan_cmd(sender_chat_id, header_prefix="🔔 *UPDATE MANUAL PASAR SAHAM IDX*")
                elif cmd in ["/portfolio", "portfolio"]:
                    handle_portfolio_cmd(sender_chat_id)
                elif cmd.startswith("/buy"):
                    handle_buy_cmd(sender_chat_id, cmd_args)
                elif cmd.startswith("/sell"):
                    handle_sell_cmd(sender_chat_id, cmd_args)
                else:
                    send_reply(sender_chat_id, f"Perintah `{text}` tidak dikenali. Ketik `/help` untuk melihat panduan menu.")
                    
        except KeyboardInterrupt:
            print("\n🛑 Bot listener dihentikan.")
            break
        except Exception as e:
            print(f"⚠️ Error loop: {e}")
            time.sleep(3)

if __name__ == "__main__":
    start_interactive_listener()
