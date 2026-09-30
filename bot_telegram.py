"""
Bot Telegram Interaktif Saham Indonesia (IDX / BEI)
Menerima dan merespons perintah langsung dari chat Telegram (Two-Way Interactive Bot):
- /start & /help: Menampilkan menu & tombol interaktif
- /scan: Memindai saham IDX dengan lonjakan volume & momentum (lengkap dengan Area Beli & Stop Loss)
- /plan <KODE>: Menampilkan Trading Plan lengkap (Area Beli, Stop Loss, Target TP1/TP2, Risk:Reward)
- /price <KODE>: Info harga saham terkini + Trading Plan + Tombol Beli Cepat
- /buy <KODE> <LOT> [TP%] [SL%]: Membeli saham simulasi dengan SL & TP kustom
- /sell <KODE> [LOT]: Menjual saham simulasi
- /portfolio: Menampilkan ringkasan saldo & saham paper trading
- Background Scheduler: Otomatis kirim update ke Telegram setiap jam bursa dibuka (09:05 WIB & 13:35/14:05 WIB)!
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
from telegram_notifier import get_credentials, send_telegram_message

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
Selamat datang di *Bot Trading Saham Indonesia (IDX / BEI)* 🤖📈

Bot ini otomatis memantau pasar saham, memberikan rekomendasi **Area Beli (Entry)**, **Stop Loss (SL)**, dan **Target Profit (TP)**, serta mengirimkan **update otomatis setiap jam bursa dibuka**.

📋 *Daftar Perintah:*
  • `/scan` - 🔍 Pindai saham IDX (lengkap dengan Area Beli & SL)
  • `/plan <KODE>` - 🎯 Buat Trading Plan saham (contoh: `/plan BBCA`)
  • `/price <KODE>` - 📈 Cek harga saham + rekomendasi Buy & SL
  • `/buy <KODE> <LOT> [TP%] [SL%]` - 🛒 Beli saham (contoh: `/buy BBCA 5` atau `/buy BBCA 5 5 3`)
  • `/sell <KODE> [LOT]` - 💰 Jual saham (contoh: `/sell BBCA 5`)
  • `/portfolio` - 💼 Cek saldo & posisi saham virtual Anda
  • `/update` - 🔔 Paksa kirim update pasar bursa sekarang
  • `/help` - ℹ️ Tampilkan panduan ini kembali

⏰ *Jadwal Update Otomatis:*
  • *Sesi 1 Buka:* 09:05 WIB
  • *Sesi 2 Buka:* 13:35 WIB (Jumat: 14:05 WIB)
  • *Pasar Tutup:* 16:05 WIB

_Gunakan tombol di bawah untuk akses cepat:_
"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🔍 Scan Saham & SL/TP", "callback_data": "btn_scan"},
                {"text": "💼 Cek Portofolio", "callback_data": "btn_portfolio"}
            ],
            [
                {"text": "🎯 Plan BBCA", "callback_data": "btn_plan_BBCA"},
                {"text": "🎯 Plan BBRI", "callback_data": "btn_plan_BBRI"},
                {"text": "🎯 Plan BMRI", "callback_data": "btn_plan_BMRI"}
            ],
            [
                {"text": "🔔 Update Pasar Sekarang", "callback_data": "btn_update_now"}
            ]
        ]
    }
    send_reply(chat_id, welcome_msg.strip(), reply_markup=keyboard)

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
  • *Target TP 2* : `{format_idr(plan['tp2'])}` (+{plan['sl_pct'] + 2.0:.1f}%)
  • *Target TP 3* : `{format_idr(plan['tp3'])}` (+8.0%)

⚖️ *Risk to Reward Ratio:* `1 : {plan['rrr']}`
🧱 *Support Terdekat:* `{format_idr(plan['support'])}`
🏢 *Resistance:* `{format_idr(plan['resistance'])}`
━━━━━━━━━━━━━━━━━━━━
_Klik tombol di bawah untuk langsung mengeksekusi pembelian di akun simulasi:_
"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": f"🛒 Beli 1 Lot {plan['symbol']}", "callback_data": f"btn_buy_{plan['symbol']}_1"},
                {"text": f"🛒 Beli 5 Lot {plan['symbol']}", "callback_data": f"btn_buy_{plan['symbol']}_5"}
            ],
            [
                {"text": f"🛒 Beli 10 Lot {plan['symbol']}", "callback_data": f"btn_buy_{plan['symbol']}_10"},
                {"text": "🔍 Scan Saham Lain", "callback_data": "btn_scan"}
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
        reply += "💡 _Gunakan `/plan <KODE>` untuk analisa detail atau `/buy <KODE> <LOT>` untuk membeli._"
    else:
        # Tampilkan top 4 volume tertinggi dengan Trading Plan lengkap
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
        reply += "💡 _Ketik `/plan <KODE>` untuk Trading Plan lengkap atau `/buy <KODE> <LOT>` untuk membeli._"
        
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
            f"🛑 *Stop Loss (SL) Aktif:* `{format_idr(res['tp_price'] * 0 + res['sl_price'])}` (-{sl_pct:.1f}%)\n"
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
    elif data.startswith("btn_plan_"):
        sym = data.replace("btn_plan_", "")
        handle_plan_cmd(chat_id, sym)
    elif data.startswith("btn_price_"):
        sym = data.replace("btn_price_", "")
        handle_price_cmd(chat_id, sym)
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
# BACKGROUND SCHEDULER: UPDATE OTOMATIS SETIAP JAM BURSA DIBUKA
# ==============================================================================
def market_hours_scheduler():
    """
    Thread latar belakang yang berjalan terus-menerus:
    Otomatis mengirimkan update screener, Area Beli, dan Stop Loss ke Telegram
    setiap kali sesi jam perdagangan Bursa Efek Indonesia (IDX) dibuka!
    
    Jadwal IDX (Senin - Jumat):
      - Sesi 1 Buka: 09:05 WIB
      - Sesi 2 Buka: 13:35 WIB (Jumat: 14:05 WIB)
      - Pasar Tutup : 16:05 WIB
    """
    token, chat_id = get_credentials()
    if not token or not chat_id:
        return
        
    print("⏰ [SCHEDULER] Background scheduler jam bursa aktif. Memantau jadwal buka bursa...")
    last_triggered_key = ""
    
    while True:
        try:
            now = get_now_wib()
            weekday = now.weekday() # 0 = Senin, 4 = Jumat, 5-6 = Sabtu-Minggu
            hour = now.hour
            minute = now.minute
            
            # Hanya berjalan di hari bursa (Senin - Jumat)
            if weekday < 5:
                # 1. Buka Sesi 1: 09:05 WIB
                if hour == 9 and 5 <= minute <= 10:
                    slot_key = f"{now.date()}_sesi1_open"
                    if last_triggered_key != slot_key:
                        last_triggered_key = slot_key
                        print(f"🔔 [{now.strftime('%H:%M:%S')} WIB] Memicu Update Sesi 1 Buka!")
                        header = f"🔔 *[UPDATE BURSA IDX: SESI 1 RESMI DIBUKA - {now.strftime('%H:%M')} WIB]* 🚀\n_Pasar saham baru saja dimulai. Berikut pantauan saham momentum, Area Beli, dan batas Stop Loss:_"
                        handle_scan_cmd(chat_id, header_prefix=header)

                # 2. Buka Sesi 2: 
                # - Senin s/d Kamis: 13:35 WIB
                # - Jumat: 14:05 WIB
                is_sesi2_open = (weekday < 4 and hour == 13 and 35 <= minute <= 40) or (weekday == 4 and hour == 14 and 5 <= minute <= 10)
                if is_sesi2_open:
                    slot_key = f"{now.date()}_sesi2_open"
                    if last_triggered_key != slot_key:
                        last_triggered_key = slot_key
                        print(f"🔔 [{now.strftime('%H:%M:%S')} WIB] Memicu Update Sesi 2 Buka!")
                        header = f"🔔 *[UPDATE BURSA IDX: SESI 2 RESMI DIBUKA - {now.strftime('%H:%M')} WIB]* 📈\n_Perdagangan sesi siang dimulai. Berikut saham dengan akumulasi volume terbesar:_"
                        handle_scan_cmd(chat_id, header_prefix=header)

                # 3. Penutupan Pasar: 16:05 WIB
                if hour == 16 and 5 <= minute <= 10:
                    slot_key = f"{now.date()}_market_close"
                    if last_triggered_key != slot_key:
                        last_triggered_key = slot_key
                        print(f"🔔 [{now.strftime('%H:%M:%S')} WIB] Memicu Update Penutupan Pasar (EOD)!")
                        header = f"🔔 *[EOD: PENUTUPAN BURSA EFEK INDONESIA - {now.strftime('%H:%M')} WIB]* 🏁\n_Ringkasan penutupan pasar hari ini & saham terbaik untuk watchlist besok:_"
                        handle_scan_cmd(chat_id, header_prefix=header)
                        
            # Cek setiap 30 detik
            time.sleep(30)
        except Exception as e:
            print(f"⚠️ Error scheduler: {e}")
            time.sleep(30)

def start_interactive_listener():
    """
    Menjalankan background long-polling untuk merespons pesan Telegram secara realtime,
    sekaligus mengaktifkan auto-scheduler jam buka bursa.
    """
    token, chat_id = get_credentials()
    if not token or not chat_id:
        print("❌ Token Telegram atau Chat ID belum dikonfigurasi.")
        return

    # Mulai thread scheduler jam bursa di latar belakang
    sched_thread = threading.Thread(target=market_hours_scheduler, daemon=True)
    sched_thread.start()

    print(f"🤖 Bot Telegram @bilnabil_bot sedang aktif mendengarkan perintah...")
    print("⏰ Update otomatis jam buka bursa (09:05 & 13:35 WIB) telah DIAKTIFKAN.")
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
                elif cmd.startswith("/plan"):
                    sym = cmd_args[0] if cmd_args else "BBCA"
                    handle_plan_cmd(sender_chat_id, sym)
                elif cmd.startswith("/price"):
                    sym = cmd_args[0] if cmd_args else "BBCA"
                    handle_price_cmd(sender_chat_id, sym)
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
