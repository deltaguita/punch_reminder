# 104 打卡提醒 Bot

透過 Telegram Bot 自動提醒上下班打卡，避免忘記打卡。

## 功能

- ⏰ **上班提醒**：10:20-12:00 每分鐘檢查，未打卡則提醒
- ⏰ **下班提醒**：19:20-22:00 每分鐘檢查，未打卡則提醒
- 🎉 **假日跳過**：國定假日、休息日、例假日自動跳過
- ✅ **一鍵停止**：點擊按鈕停止當日提醒（請假/已處理）
- 🔔 **Cookie 檢查**：每天 21:00 檢查 Cookie 是否過期
- 📊 **狀態查詢**：`/status` 查看今日打卡狀態

## 安裝

```bash
git clone https://github.com/deltaguita/punch_reminder.git
cd punch_reminder
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install "python-telegram-bot[job-queue]"
```

## 設定

複製 `.env.example` 為 `.env` 並填入：

```bash
cp .env.example .env
```

```env
TELEGRAM_BOT_TOKEN=你的Bot_Token
TELEGRAM_CHAT_ID=你的Telegram_User_ID
COOKIES_104=從瀏覽器複製的Cookie
```

### 取得 Cookie

1. 登入 https://pro.104.com.tw/psc2
2. F12 → Network → 點任意請求
3. 複製 `Cookie:` 後面的值

## 執行

```bash
python bot.py
```

## 更新 Cookie

Cookie 過期時會收到提醒，執行以下指令更新：

```bash
./update_cookie.sh "新的cookie內容"
```

## 部署（systemd）

```bash
sudo cp punch-reminder.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable punch-reminder.service
sudo systemctl start punch-reminder.service
```

## 指令

| 指令 | 說明 |
|------|------|
| `/start` | 顯示說明 |
| `/status` | 查看今日打卡狀態 |

## License

MIT
