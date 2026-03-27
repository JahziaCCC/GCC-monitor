import os
import re
import requests
from datetime import datetime

BOT = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")

def send(msg):
    if not BOT or not CHAT:
        print(msg)
        return
    requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage",
                  json={"chat_id": CHAT, "text": msg})

# =========================
# مصادر رسمية فقط
# =========================
SOURCES = {
    "uae": "https://wam.ae/en/search?keyword=intercept",
    "qatar": "https://www.mofa.gov.qa/en/latest-articles",
    "kuwait": "https://www.kuna.net.kw/ArticleSearch.aspx",
    "bahrain": "https://www.bna.bh/en/search.aspx"
}

GULF = {
    "uae": "🇦🇪 الإمارات",
    "qatar": "🇶🇦 قطر",
    "kuwait": "🇰🇼 الكويت",
    "bahrain": "🇧🇭 البحرين",
    "saudi": "🇸🇦 السعودية",
    "oman": "🇴🇲 عمان"
}

MISSILE = [r'(\d+)\s+missiles?', r'(\d+)\s+صواريخ?']
DRONE = [r'(\d+)\s+drones?', r'(\d+)\s+مسي']

INTERCEPT = [
    "intercept","shot down","destroyed",
    "تم اعتراض","تم إسقاط","تم صد"
]

def extract(text):
    text = text.lower()
    m=d=0
    for p in MISSILE:
        m+=sum(map(int,re.findall(p,text)))
    for p in DRONE:
        d+=sum(map(int,re.findall(p,text)))
    return m,d

# =========================
# سحب البيانات
# =========================
stats = {k:{"m":0,"d":0,"found":False} for k in GULF}

for country, url in SOURCES.items():
    try:
        r = requests.get(url, timeout=10)
        text = r.text.lower()

        if not any(k in text for k in INTERCEPT):
            continue

        m,d = extract(text)

        if m>0 or d>0:
            stats[country]["m"] += m
            stats[country]["d"] += d
            stats[country]["found"] = True

    except:
        pass

# =========================
# التقرير
# =========================
today = datetime.now().strftime("%Y-%m-%d")

msg = f"📊 اعتراض وصد الصواريخ (مصادر رسمية فقط)\n🕒 {today}\n\n"

total_m = 0
total_d = 0

for k,name in GULF.items():
    m = stats[k]["m"]
    d = stats[k]["d"]

    total_m += m
    total_d += d

    if stats[k]["found"]:
        msg += f"{name}\n• 🚀 {m}\n• 🛸 {d}\n\n"
    else:
        msg += f"{name}\n• لا يوجد بيان رسمي اليوم\n\n"

msg += f"""════════════════════
📊 الإجمالي الرسمي
• 🚀 {total_m}
• 🛸 {total_d}
"""

send(msg)
