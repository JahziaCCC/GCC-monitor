import os
import re
import html
import json
import hashlib
import feedparser
import requests
from datetime import datetime, timedelta
from pathlib import Path

# =========================
# إعدادات
# =========================
START_DATE = datetime(2026, 2, 28)
STATE_FILE = "gcc_db.json"

BOT = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")

# =========================
# الدول
# =========================
GULF = {
    "saudi": "🇸🇦 السعودية",
    "uae": "🇦🇪 الإمارات",
    "qatar": "🇶🇦 قطر",
    "kuwait": "🇰🇼 الكويت",
    "bahrain": "🇧🇭 البحرين",
    "oman": "🇴🇲 عمان"
}

# =========================
# كلمات
# =========================
INTERCEPT = ["intercept","shot down","destroyed","تم اعتراض","تم إسقاط","تم صد"]
EXCLUDE = ["launched","detected","أطلقت","رصد"]

MISSILE = [r'(\d+)\s+missiles?', r'(\d+)\s+صواريخ?']
DRONE = [r'(\d+)\s+drones?', r'(\d+)\s+مسي']

RSS = [
    "https://news.google.com/rss/search?q=missiles+drones+intercept+gulf",
    "https://news.google.com/rss/search?q=اعتراض+صواريخ+مسيرات+الخليج"
]

# =========================
# أدوات
# =========================
def send(msg):
    if not BOT or not CHAT:
        print(msg)
        return
    requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage",
                  json={"chat_id": CHAT, "text": msg})

def clean(t):
    t = html.unescape(t or "")
    return re.sub(r"\s+"," ",re.sub(r"<.*?>"," ",t)).strip()

def detect_country(t):
    t = t.lower()
    if "saudi" in t or "السعودية" in t: return "saudi"
    if "uae" in t or "الإمارات" in t: return "uae"
    if "qatar" in t or "قطر" in t: return "qatar"
    if "kuwait" in t or "الكويت" in t: return "kuwait"
    if "bahrain" in t or "البحرين" in t: return "bahrain"
    if "oman" in t or "عمان" in t: return "oman"

def extract(t):
    t=t.lower()
    m=d=0
    for p in MISSILE: m+=sum(map(int,re.findall(p,t)))
    for p in DRONE: d+=sum(map(int,re.findall(p,t)))
    return m,d

def load():
    if not Path(STATE_FILE).exists():
        return []
    return json.loads(Path(STATE_FILE).read_text())

def save(data):
    Path(STATE_FILE).write_text(json.dumps(data,indent=2,ensure_ascii=False))

# =========================
# تشغيل
# =========================
db = load()
keys = set(x["key"] for x in db)

now = datetime.utcnow()
daily_cut = now - timedelta(hours=24)

for url in RSS:
    feed = feedparser.parse(url)

    for e in feed.entries:
        text = clean(e.title + " " + e.get("summary",""))

        if not any(k in text.lower() for k in INTERCEPT): continue
        if any(k in text.lower() for k in EXCLUDE): continue

        c = detect_country(text)
        if not c: continue

        m,d = extract(text)
        if m==0 and d==0: continue

        pub = datetime.utcnow()

        key = hashlib.md5(text.encode()).hexdigest()
        if key in keys: continue
        keys.add(key)

        db.append({
            "key": key,
            "country": c,
            "m": m,
            "d": d,
            "time": pub.isoformat()
        })

# =========================
# حساب
# =========================
daily = {k:{"m":0,"d":0} for k in GULF}
total = {k:{"m":0,"d":0} for k in GULF}

for e in db:
    t = datetime.fromisoformat(e["time"])
    c = e["country"]

    if t >= daily_cut:
        daily[c]["m"] += e["m"]
        daily[c]["d"] += e["d"]

    if t >= START_DATE:
        total[c]["m"] += e["m"]
        total[c]["d"] += e["d"]

save(db)

# =========================
# تقرير
# =========================
msg = f"📊 التقرير اليومي\n🕒 {now.date()}\n\n"

for k,n in GULF.items():
    msg += f"{n}\n• 🚀 {daily[k]['m']} | 🛸 {daily[k]['d']}\n\n"

msg += "════════════════════\n📊 منذ بداية الحرب\n\n"

for k,n in GULF.items():
    msg += f"{n}\n• 🚀 {total[k]['m']} | 🛸 {total[k]['d']}\n\n"

send(msg)
