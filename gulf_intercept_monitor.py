import os
import requests

BOT = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")

msg = "🔥 GCC Monitor شغال 100%"

if not BOT or not CHAT:
    print("❌ مشكلة في TELEGRAM_BOT_TOKEN أو TELEGRAM_CHAT_ID")
else:
    url = f"https://api.telegram.org/bot{BOT}/sendMessage"
    data = {
        "chat_id": CHAT,
        "text": msg
    }

    response = requests.post(url, json=data)

    print("Status:", response.status_code)
    print("Response:", response.text)
