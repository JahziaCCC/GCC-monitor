import os
import re
import html
import hashlib
import feedparser
import requests
from datetime import datetime

BOT = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")

def send(msg):
    if not BOT or not CHAT:
        print(msg)
        return

    url = f"https://api.telegram.org/bot{BOT}/sendMessage"
    payload = {
        "chat_id": CHAT,
        "text": msg
    }
    r = requests.post(url, json=payload, timeout=30)
    print("Status:", r.status_code)
    print("Response:", r.text)

GULF = {
    "saudi": "🇸🇦 السعودية",
    "uae": "🇦🇪 الإمارات",
    "qatar": "🇶🇦 قطر",
    "kuwait": "🇰🇼 الكويت",
    "bahrain": "🇧🇭 البحرين",
    "oman": "🇴🇲 عمان"
}

INTERCEPT = [
    "intercept", "intercepted", "shot down", "destroyed", "downed",
    "air defenses intercepted", "air defences intercepted",
    "تم اعتراض", "اعترضت", "تم إسقاط", "اسقطت", "تم تدمير", "صد", "تم صد"
]

EXCLUDE = [
    "launched", "fired", "detected", "tracked",
    "أطلقت", "إطلاق", "رصد", "تم رصد"
]

MISSILE = [
    r'(\d+)\s+missiles?',
    r'(\d+)\s+ballistic\s+missiles?',
    r'(\d+)\s+rockets?',
    r'(\d+)\s+صواريخ?',
    r'(\d+)\s+صاروخ'
]

DRONE = [
    r'(\d+)\s+drones?',
    r'(\d+)\s+uavs?',
    r'(\d+)\s+مسيّرات?',
    r'(\d+)\s+مسيرات?',
    r'(\d+)\s+طائرات?\s+مسيّرة',
    r'(\d+)\s+طائرات?\s+مسيرة'
]

RSS = [
    "https://news.google.com/rss/search?q=missiles+drones+intercept+gulf",
    "https://news.google.com/rss/search?q=%D8%A7%D8%B9%D8%AA%D8%B1%D8%A7%D8%B6+%D8%B5%D9%88%D8%A7%D8%B1%D9%8A%D8%AE+%D9%85%D8%B3%D9%8A%D8%B1%D8%A7%D8%AA+%D8%A7%D9%84%D8%AE%D9%84%D9%8A%D8%AC"
]

def clean(t):
    t = html.unescape(t or "")
    t = re.sub(r"<.*?>", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def has_intercept(t):
    t = t.lower()
    return any(k in t for k in INTERCEPT)

def is_bad(t):
    t = t.lower()
    if has_intercept(t):
        return False
    return any(k in t for k in EXCLUDE)

def country(t):
    t = t.lower()
    if "saudi" in t or "السعودية" in t:
        return "saudi"
    if "uae" in t or "emirates" in t or "الإمارات" in t or "الامارات" in t or "dubai" in t or "abu dhabi" in t:
        return "uae"
    if "qatar" in t or "قطر" in t:
        return "qatar"
    if "kuwait" in t or "الكويت" in t:
        return "kuwait"
    if "bahrain" in t or "البحرين" in t:
        return "bahrain"
    if "oman" in t or "عمان" in t:
        return "oman"
    return None

def extract(t):
    t = t.lower()
    m = 0
    d = 0

    for p in MISSILE:
        vals = re.findall(p, t)
        m += sum(int(x) for x in vals if str(x).isdigit())

    for p in DRONE:
        vals = re.findall(p, t)
        d += sum(int(x) for x in vals if str(x).isdigit())

    return m, d

stats = {k: {"m": 0, "d": 0} for k in GULF}
seen = set()

for url in RSS:
    feed = feedparser.parse(url)

    for e in feed.entries:
        text = clean(getattr(e, "title", "") + " " + getattr(e, "summary", ""))

        if not has_intercept(text):
            continue

        if is_bad(text):
            continue

        c = country(text)
        if not c:
            continue

        m, d = extract(text)
        if m == 0 and d == 0:
            continue

        key = hashlib.md5((c + "|" + text[:300]).encode("utf-8")).hexdigest()
        if key in seen:
            continue
        seen.add(key)

        stats[c]["m"] += m
        stats[c]["d"] += d

today = datetime.now().strftime("%Y-%m-%d")

msg = f"""📊 اعتراض وصد الصواريخ والمسيّرات
🕒 {today}

"""

total_m = 0
total_d = 0

for k, name in GULF.items():
    m = stats[k]["m"]
    d = stats[k]["d"]

    total_m += m
    total_d += d

    msg += f"""{name}
• الصواريخ: {m}
• المسيّرات: {d}

"""

msg += f"""════════════════════
📊 الإجمالي
• الصواريخ: {total_m}
• المسيّرات: {total_d}
"""

send(msg)
