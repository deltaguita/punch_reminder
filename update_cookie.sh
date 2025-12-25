#!/bin/bash
# 更新 104 Cookie 到樹莓派
# 使用方式：./update_cookie.sh "你的cookie字串"

if [ -z "$1" ]; then
    echo "使用方式："
    echo "1. 登入 https://pro.104.com.tw/psc2"
    echo "2. F12 → Network → 找任意請求 → 複製 Cookie header 的值"
    echo "3. 執行: ./update_cookie.sh \"cookie內容\""
    exit 1
fi

COOKIE="$1"
PI_HOST="deltaguita@wellspi.local"
ENV_FILE="~/punch_reminder/.env"

# 更新樹莓派上的 .env
ssh $PI_HOST "sed -i 's|^COOKIES_104=.*|COOKIES_104=$COOKIE|' $ENV_FILE"

# 重啟服務
ssh $PI_HOST "sudo systemctl restart punch-reminder.service"

echo "✅ Cookie 已更新並重啟服務"

# 測試
ssh $PI_HOST "cd ~/punch_reminder && source venv/bin/activate && python -c \"from bot import checker; r=checker.get_today_punch(); print('測試結果:', r)\""
