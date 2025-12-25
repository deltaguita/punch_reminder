#!/usr/bin/env python3
"""104 打卡提醒 Bot"""

import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TZ = timezone(timedelta(hours=8))
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))

# 今日狀態
today_status = {
    "skip_clock_in": False,
    "skip_clock_out": False,
    "date": None
}


def reset_daily_status():
    """重置每日狀態"""
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    if today_status["date"] != today:
        today_status["skip_clock_in"] = False
        today_status["skip_clock_out"] = False
        today_status["date"] = today


class PunchChecker:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://pro.104.com.tw"
        self._setup_session()
    
    def _setup_session(self):
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Request": "JSON",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://pro.104.com.tw/psc2"
        })
        cookies_str = os.getenv("COOKIES_104", "")
        for item in cookies_str.split("; "):
            if "=" in item:
                key, value = item.split("=", 1)
                self.session.cookies.set(key, value)
    
    def get_today_punch(self):
        now = datetime.now(TZ)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            end_of_month = now.replace(year=now.year+1, month=1, day=1) - timedelta(seconds=1)
        else:
            end_of_month = now.replace(month=now.month+1, day=1) - timedelta(seconds=1)
        
        start_ts = int(start_of_month.timestamp() * 1000)
        end_ts = int(end_of_month.timestamp() * 1000)
        url = f"{self.base_url}/psc2/api/home/newCalendar/{start_ts}/{end_ts}"
        
        try:
            resp = self.session.get(url, timeout=30)
            data = resp.json()
            if data.get("code") != 200:
                return {"error": data.get("message", "API 錯誤")}
            
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_ts = int(today_start.timestamp() * 1000)
            
            for record in data.get("data", []):
                if record.get("date") == today_ts:
                    return self._parse_record(record)
            return {"error": "找不到今天的紀錄"}
        except Exception as e:
            return {"error": str(e)}
    
    def _parse_record(self, record):
        result = {
            "date": datetime.fromtimestamp(record["date"] / 1000, TZ).strftime("%Y-%m-%d"),
            "is_holiday": False,
            "clock_in": None,
            "clock_out": None,
        }
        for event in record.get("events", []):
            if event.get("type") == 2:
                result["is_holiday"] = True
                result["holiday_name"] = event.get("title")
                break
        clock_in = record.get("clockIn", {})
        if clock_in.get("start"):
            result["clock_in"] = datetime.fromtimestamp(clock_in["start"] / 1000, TZ).strftime("%H:%M")
        if clock_in.get("end"):
            result["clock_out"] = datetime.fromtimestamp(clock_in["end"] / 1000, TZ).strftime("%H:%M")
        return result


checker = PunchChecker()


async def check_clock_in(context: ContextTypes.DEFAULT_TYPE):
    """檢查上班打卡（10:20-12:00）"""
    now = datetime.now(TZ)
    if not (10 * 60 + 20 <= now.hour * 60 + now.minute <= 12 * 60):
        return
    
    reset_daily_status()
    if today_status["skip_clock_in"]:
        return
    
    result = checker.get_today_punch()
    if "error" in result:
        logger.error(f"檢查失敗: {result['error']}")
        return
    if result.get("is_holiday"):
        return
    if result.get("clock_in"):
        return
    
    keyboard = [[InlineKeyboardButton("✅ 今天請假/已處理", callback_data="skip_in")]]
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=f"⏰ 上班打卡提醒\n\n📅 {result['date']}\n❌ 你還沒打上班卡！",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def check_clock_out(context: ContextTypes.DEFAULT_TYPE):
    """檢查下班打卡（19:20-22:00）"""
    now = datetime.now(TZ)
    if not (19 * 60 + 20 <= now.hour * 60 + now.minute <= 22 * 60):
        return
    
    reset_daily_status()
    if today_status["skip_clock_out"]:
        return
    
    result = checker.get_today_punch()
    if "error" in result:
        logger.error(f"檢查失敗: {result['error']}")
        return
    if result.get("is_holiday"):
        return
    if result.get("clock_out"):
        return
    
    keyboard = [[InlineKeyboardButton("✅ 今天請假/已處理", callback_data="skip_out")]]
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=f"⏰ 下班打卡提醒\n\n📅 {result['date']}\n❌ 你還沒打下班卡！",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """處理按鈕回調"""
    query = update.callback_query
    await query.answer()
    
    reset_daily_status()
    if query.data == "skip_in":
        today_status["skip_clock_in"] = True
        await query.edit_message_text("✅ 已停止今日上班打卡提醒")
    elif query.data == "skip_out":
        today_status["skip_clock_out"] = True
        await query.edit_message_text("✅ 已停止今日下班打卡提醒")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看打卡狀態"""
    result = checker.get_today_punch()
    if "error" in result:
        await update.message.reply_text(f"❌ 查詢失敗: {result['error']}")
        return
    
    if result.get("is_holiday"):
        text = f"📅 {result['date']}\n🎉 今天是 {result.get('holiday_name', '假日')}，不用打卡"
    else:
        text = f"📅 {result['date']}\n"
        text += f"上班: {'✅ ' + result['clock_in'] if result.get('clock_in') else '❌ 未打卡'}\n"
        text += f"下班: {'✅ ' + result['clock_out'] if result.get('clock_out') else '❌ 未打卡'}"
    
    await update.message.reply_text(text)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕐 104 打卡提醒 Bot\n\n"
        "指令：\n"
        "/status - 查看今日打卡狀態\n\n"
        "自動提醒時間：\n"
        "• 上班：10:20 起每分鐘\n"
        "• 下班：19:20 起每分鐘"
    )


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    app = Application.builder().token(token).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    job_queue = app.job_queue
    # 上班提醒：10:20-12:00 每分鐘
    job_queue.run_repeating(check_clock_in, interval=60, first=10, 
                            job_kwargs={"id": "clock_in"})
    # 下班提醒：19:20-22:00 每分鐘  
    job_queue.run_repeating(check_clock_out, interval=60, first=10,
                            job_kwargs={"id": "clock_out"})
    
    logger.info("Bot 啟動中...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
