"""
Bot Telegram Interaktif Saham Indonesia (IDX / BEI)
Menerima dan merespons perintah langsung dari chat Telegram (Two-Way Interactive Bot):
- /start & /help: Menampilkan menu & tombol interaktif
- /scan: Memindai saham IDX dengan lonjakan volume & momentum
- /portfolio: Menampilkan ringkasan saldo & saham paper trading
- /buy <KODE> <LOT>: Membeli saham simulasi (misal: /buy BBCA 5)
- /sell <KODE> [LOT]: Menjual saham simulasi (misal: /sell BBCA 5)
- /price <KODE>: Mengecek harga terkini saham (misal: /price BMRI)
"""
import os
import sys
import time
import requests
from typing import Dict, Any, Optional

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import config
from config import format_idr
from data_provider import get_current_price, get_clean_symbol, get_ticker_summary
from screener import run_screener
from paper_trader import (
    load_portfolio, buy_stock, sell_stock, update_and_check_portfolio,
    display_portfolio_summary
)
from telegram_notifier import get_credentials, send_telegram_message

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

Bot ini siap membantu Anda memantau pasar saham, mendeteksi volume spike, dan mengelola simulasi paper trading.

📋 *Daftar Perintah:*
  • `/scan` - 🔍 Pindai saham IDX dengan momentum & lonjakan volume
  • `/portfolio` - 💼 Cek saldo & posisi saham virtual Anda
  • `/buy <KODE> <LOT>` - 🛒 Beli saham (contoh: `/buy BBCA 5`)
  • `/sell <KODE> [LOT]` - 💰 Jual saham (contoh: `/sell BBCA 5`)
  • `/price <KODE>` - 📈 Cek harga saham terkini (contoh: `/price BBRI`)
  • `/help` - ℹ️ Tampilkan panduan ini kembali

_Gunakan tombol di bawah untuk akses cepat:_
"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🔍 Scan Saham IDX", "callback_data": "btn_scan"},
                {"text": "💼 Cek Portofolio", "callback_data": "btn_portfolio"}
            ],
            [
                {"text": "📈 Cek BBCA", "callback_data": "btn_price_BBCA"},
                {"text": "📈 Cek BBRI", "callback_data": "btn_price_BBRI"},
                {"text": "📈 Cek BMRI", "callback_data": "btn_price_BMRI"}
            ]
        ]
    }
    send_reply(chat_id, welcome_msg.strip(), reply_markup=keyboard)

def handle_scan_cmd(chat_id: str):
    send_reply(chat_id, "⏳ *Sedang memindai saham-saham likuid IDX...*\n_Mohon tunggu sekitar 5-10 detik..._")
    results = run_screener(send_telegram=False, show_all=False)
    
    buy_signals = [r for r in results if r.get('has_signal', False)]
    
    if buy_signals:
        reply = "🎉 *HASIL SCREENER: DITEMUKAN SINYAL BUY!* 🚀\n━━━━━━━━━━━━━━━━━━━━\n"
        for sig in buy_signals:
            reply += f"""
📌 *{sig['symbol']}* ({sig['signal']})
💵 Harga: `{format_idr(sig['close'])}` ({sig['change_pct']:+.2f}%)
📊 RVol: `{sig['rvol']}x` | RSI: `{sig['rsi']}`
💰 Turnover: `{format_idr(sig['turnover'])}`
🎯 Target TP1: `{format_idr(sig['tp1'])}` | SL: `{format_idr(sig['sl'])}`
━━━━━━━━━━━━━━━━━━━━
"""
        reply += "_Gunakan `/buy KODE LOT` untuk membeli di paper trading._"
    else:
        # Tampilkan top 5 volume tertinggi jika tidak ada sinyal momentum ekstrem
        top_stocks = sorted(results, key=lambda x: x.get('rvol', 0), reverse=True)[:5]
        reply = "ℹ️ *Hasil Screener:* Belum ada sinyal breakout ekstrem saat ini.\n\n📊 *Top 5 Saham dengan Aktivitas Volume Tertinggi:* \n"
        for s in top_stocks:
            reply += f"• *{s['symbol']}*: `{format_idr(s['close'])}` ({s['change_pct']:+.2f}%) | RVol: `{s['rvol']:.2f}x` | RSI: `{s['rsi']}`\n"
        reply += "\n_Pasar akan terus dipantau secara berkala._"
        
    send_reply(chat_id, reply.strip())

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
        pos_lines.append(f"{pnl_badge} *{sym}*: {pos['lots']} Lot @ `{format_idr(pos['avg_price'])}`\n   Now: `{format_idr(curr_price)}` | PnL: `{format_idr(unrealized)}` ({pnl_pct:+.2f}%)")
        
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
        msg += "\n".join(pos_lines)
    else:
        msg += "_(Tidak ada posisi saham aktif. 100% Kas Tunai)_"
        
    send_reply(chat_id, msg.strip())

def handle_price_cmd(chat_id: str, symbol: str):
    summary = get_ticker_summary(symbol)
    if not summary.get("valid"):
        send_reply(chat_id, f"❌ Data untuk saham `{symbol}` tidak ditemukan di IDX.")
        return
        
    chg_badge = "🟢" if summary['change_pct'] >= 0 else "🔴"
    msg = f"""
📈 *INFO HARGA SAHAM IDX*
━━━━━━━━━━━━━━━━━━━━
📌 *Emiten:* `{summary['symbol']}`
💵 *Harga Terkini:* `{format_idr(summary['last_price'])}` ({chg_badge} {summary['change_pct']:+.2f}%)
📊 *Volume:* `{summary['volume']:,}` lembar
💰 *Turnover:* `{format_idr(summary['turnover'])}`
📐 *Rentang Hari Ini:* `{format_idr(summary['low'])}` - `{format_idr(summary['high'])}`
📅 *Tanggal:* `{summary['date']}`
━━━━━━━━━━━━━━━━━━━━
"""
    send_reply(chat_id, msg.strip())

def handle_buy_cmd(chat_id: str, args: list):
    if len(args) < 2:
        send_reply(chat_id, "⚠️ Format salah. Gunakan: `/buy <KODE_SAHAM> <JUMLAH_LOT>`\nContoh: `/buy BBCA 5`")
        return
    sym = args[0].upper()
    try:
        lots = int(args[1])
    except ValueError:
        send_reply(chat_id, "⚠️ Jumlah lot harus berupa angka bulat.")
        return
        
    res = buy_stock(sym, lots=lots)
    if res["success"]:
        send_reply(chat_id, f"✅ *PEMBELIAN BERHASIL!*\n{res['message']}\n💰 Sisa Kas: `{format_idr(res['remaining_cash'])}`\n🎯 TP (+5%): `{format_idr(res['tp_price'])}` | SL (-3%): `{format_idr(res['sl_price'])}`")
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
        send_reply(chat_id, f"✅ *PENJUALAN BERHASIL!*\n{res['message']}\n💰 Sisa Kas: `{format_idr(res['remaining_cash'])}`")
    else:
        send_reply(chat_id, f"❌ Gagal: {res['message']}")

def process_callback_query(query: Dict[str, Any]):
    chat_id = str(query.get("message", {}).get("chat", {}).get("id"))
    data = query.get("data", "")
    
    # Jawab callback query agar loading di tombol hilang
    token, _ = get_credentials()
    try:
        requests.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery", json={"callback_query_id": query.get("id")}, timeout=5)
    except Exception:
        pass
        
    if data == "btn_scan":
        handle_scan_cmd(chat_id)
    elif data == "btn_portfolio":
        handle_portfolio_cmd(chat_id)
    elif data.startswith("btn_price_"):
        sym = data.replace("btn_price_", "")
        handle_price_cmd(chat_id, sym)

def start_interactive_listener():
    """
    Menjalankan background long-polling untuk merespons pesan Telegram secara realtime.
    """
    token, chat_id = get_credentials()
    if not token or not chat_id:
        print("❌ Token Telegram atau Chat ID belum dikonfigurasi.")
        return

    print(f"🤖 Bot Telegram @bilnabil_bot sedang aktif mendengarkan perintah...")
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
                
                # Cek jika ada klik tombol inline
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
                elif cmd == "/scan" or cmd == "scan":
                    handle_scan_cmd(sender_chat_id)
                elif cmd == "/portfolio" or cmd == "portfolio":
                    handle_portfolio_cmd(sender_chat_id)
                elif cmd.startswith("/price"):
                    sym = cmd_args[0] if cmd_args else "BBCA"
                    handle_price_cmd(sender_chat_id, sym)
                elif cmd.startswith("/buy"):
                    handle_buy_cmd(sender_chat_id, cmd_args)
                elif cmd.startswith("/sell"):
                    handle_sell_cmd(sender_chat_id, cmd_args)
                else:
                    send_reply(sender_chat_id, f"Perintah `{text}` tidak dikenali. Ketik `/help` untuk melihat menu.")
                    
        except KeyboardInterrupt:
            print("\n🛑 Bot listener dihentikan.")
            break
        except Exception as e:
            print(f"⚠️ Error loop: {e}")
            time.sleep(3)

if __name__ == "__main__":
    start_interactive_listener()
