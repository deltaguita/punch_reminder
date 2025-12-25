#!/usr/bin/env python3
"""104 打卡提醒系統"""

import os
import time
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

TZ = timezone(timedelta(hours=8))

class PunchChecker:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://pro.104.com.tw"
        self._setup_session()
    
    def _setup_session(self):
        """設定 Session Headers 和 Cookies"""
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Request": "JSON",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://pro.104.com.tw/psc2"
        })
        
        # 從環境變數載入 Cookies
        cookies_str = os.getenv("COOKIES_104", "")
        if cookies_str:
            for item in cookies_str.split("; "):
                if "=" in item:
                    key, value = item.split("=", 1)
                    self.session.cookies.set(key, value)
    
    def get_today_punch(self):
        """取得今天的打卡紀錄"""
        now = datetime.now(TZ)
        
        # 計算本月的起訖時間戳（毫秒）
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
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("code") != 200:
                return {"error": f"API 錯誤: {data.get('message')}"}
            
            # 找今天的紀錄
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_ts = int(today_start.timestamp() * 1000)
            
            for record in data.get("data", []):
                if record.get("date") == today_ts:
                    return self._parse_record(record)
            
            return {"error": "找不到今天的紀錄"}
            
        except requests.exceptions.RequestException as e:
            return {"error": f"請求失敗: {e}"}
    
    def _parse_record(self, record):
        """解析打卡紀錄"""
        result = {
            "date": datetime.fromtimestamp(record["date"] / 1000, TZ).strftime("%Y-%m-%d"),
            "is_holiday": False,
            "holiday_name": None,
            "clock_in": None,
            "clock_out": None,
            "need_punch": True
        }
        
        # 檢查是否為假日
        events = record.get("events", [])
        for event in events:
            if event.get("type") == 2:  # 假日類型
                result["is_holiday"] = True
                result["holiday_name"] = event.get("title")
                result["need_punch"] = False
                break
        
        # 檢查打卡紀錄
        clock_in = record.get("clockIn", {})
        if clock_in.get("start"):
            result["clock_in"] = datetime.fromtimestamp(
                clock_in["start"] / 1000, TZ
            ).strftime("%H:%M:%S")
        
        if clock_in.get("end"):
            result["clock_out"] = datetime.fromtimestamp(
                clock_in["end"] / 1000, TZ
            ).strftime("%H:%M:%S")
        
        return result


def send_telegram_message(message):
    """發送 Telegram 訊息"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("❌ 未設定 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID")
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": message}
    
    try:
        resp = requests.post(url, json=data, timeout=10)
        return resp.status_code == 200
    except:
        return False


def check_and_notify():
    """檢查打卡狀態並通知"""
    checker = PunchChecker()
    result = checker.get_today_punch()
    
    if "error" in result:
        print(f"❌ {result['error']}")
        send_telegram_message(f"⚠️ 打卡檢查失敗\n{result['error']}")
        return
    
    print(f"📅 日期: {result['date']}")
    
    if result["is_holiday"]:
        print(f"🎉 今天是 {result['holiday_name']}，不用打卡")
        return
    
    if result["clock_in"]:
        print(f"✅ 已打上班卡: {result['clock_in']}")
        if result["clock_out"]:
            print(f"✅ 已打下班卡: {result['clock_out']}")
    else:
        print("❌ 尚未打卡！")
        send_telegram_message(
            f"⏰ 打卡提醒\n\n"
            f"📅 {result['date']}\n"
            f"❌ 你還沒打卡！\n\n"
            f"回覆「請假」可停止今日提醒"
        )


if __name__ == "__main__":
    check_and_notify()
