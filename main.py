import time
import os
import json
import urllib.request
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# خواندن متغیرها از بخش Environment Variables سایت (یا جایگزینی مستقیم در صورت تمایل)
TELEGRAM_BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("CHAT_ID", "")

LOG_INTERVAL = 60               # ثبت در لاگ کنسول: هر ۶۰ ثانیه (۱ دقیقه)
REPORT_INTERVAL = 12 * 3600     # ارسال گزارش تلگرام: هر ۱۲ ساعت
PING_URL = "https://api.telegram.org"

current_status_text = "Bot is running..."

class DummyHandler(BaseHTTPRequestHandler):
    """وب‌سرور سبک برای باز نگه داشتن پورت در هاست‌های ابری"""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(current_status_text.encode("utf-8"))
    
    def log_message(self, format, *args):
        return

def start_web_server():
    port = int(os.environ.get("PORT", 8080))
    try:
        server = HTTPServer(("0.0.0.0", port), DummyHandler)
        print(f"[🌐] پورت وب {port} باز شد.", flush=True)
        server.serve_forever()
    except Exception as e:
        print(f"[!] خطا در پورت وب: {e}", flush=True)

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[!] خطا در ارسال به تلگرام: {e}", flush=True)

def format_duration(seconds):
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days} روز")
    if hours > 0:
        parts.append(f"{hours} ساعت")
    if minutes > 0:
        parts.append(f"{minutes} دقیقه")
    if secs > 0 or not parts:
        parts.append(f"{secs} ثانیه")
    return " و ".join(parts)

def check_network():
    start = time.time()
    try:
        req = urllib.request.Request(PING_URL, headers={"User-Agent": "Mozilla/5.0"})
        urllib.request.urlopen(req, timeout=10)
        latency = int((time.time() - start) * 1000)
        return True, latency
    except Exception as e:
        return False, str(e)

def main():
    global current_status_text
    
    # اجرای پورت وب در پس‌زمینه
    threading.Thread(target=start_web_server, daemon=True).start()

    start_time = time.time()
    start_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    last_telegram_report = start_time
    net_drops = 0

    # پیام استارت (هر بار که سرور از اول ران یا ری‌استارت بشه این پیام میاد)
    start_msg = (
        f"🚀 <b>سرور استارت خورد GITHUB!</b>\n\n"
        f"🕒 زمان شروع به کار: <code>{start_str}</code>\n"
        f"<i>(اگر قبلاً روشن بوده و دوباره این پیام رو می‌بینی، یعنی سرور یه بار ری‌استارت شده)</i>"
    )
    print(f"=== Server Started at {start_str} ===", flush=True)
    send_telegram(start_msg)

    while True:
        current_time = time.time()
        uptime = current_time - start_time
        
        net_ok, ping_info = check_network()
        if not net_ok:
            net_drops += 1
            net_status = f"❌ قطع ({ping_info})"
        else:
            net_status = f"🟢 {ping_info}ms"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # ۱. چاپ هر ۱ دقیقه در لاگ سایت
        log_line = (
            f"[{timestamp}] آپ‌تایم یکسره: {format_duration(uptime)} | "
            f"پینگ: {net_status} | "
            f"تعداد قطعی اینترنت: {net_drops}"
        )
        print(log_line, flush=True)
        current_status_text = log_line

        # ۲. گزارش ۱۲ ساعته در تلگرام
        if current_time - last_telegram_report >= REPORT_INTERVAL:
            report_msg = (
                f"📊 <b>گزارش ۱۲ ساعته وضعیت Github</b>\n\n"
                f"🟢 آپ‌تایم یکسره (بدون ری‌استارت): <b>{format_duration(uptime)}</b>\n"
                f"🕒 روشن از تاریخ: <code>{start_str}</code>\n"
                f"⚡ تعداد قطعی‌های لحظه‌ای شبکه: <b>{net_drops} بار</b>\n"
                f"🌐 پینگ فعلی سرور: <code>{net_status}</code>"
            )
            send_telegram(report_msg)
            last_telegram_report = current_time

        time.sleep(LOG_INTERVAL)

if __name__ == "__main__":
    main()
