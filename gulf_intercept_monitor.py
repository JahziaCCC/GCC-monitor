import os
import re
import html
import json
import hashlib
import feedparser
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

# =========================
# إعدادات
# =========================
START_DATE = datetime(2026, 2, 28, tzinfo=timezone.utc)
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
INTERCEPT = [
    "intercept", "intercepted", "shot down", "destroyed", "downed",
    "air defenses intercepted", "air defences intercepted",
    "tam اعتراض",  # لن تُستخدم غالبًا لكنها لا تضر
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
    "https://news.google.com/rss/search?q=اعتراض+صواريخ+مسيرات+الخليج"
]

# =========================
# أدوات
# =========================
def send(msg: str):
    if not BOT or not CHAT:
        print(msg)
        return
    r = requests.post(
        f"https://api.telegram.org/bot{BOT}/sendMessage",
        json={"chat_id": CHAT, "text": msg},
        timeout=30
    )
    print("Status:", r.status_code)
    print("Response:", r.text)

def clean(t: str) -> str:
    t = html.unescape(t or "")
    t = re.sub(r"<.*?>", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def detect_country(t: str):
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

def extract(t: str):
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

def parse_published(entry):
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    return None

def load():
    if not Path(STATE_FILE).exists():
        return []
    try:
        return json.loads(Path(STATE_FILE).read_text(encoding="utf-8"))
    except Exception:
        return []

def save(data):
    Path(STATE_FILE).write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

def has_intercept(text: str) -> bool:
    tl = text.lower()
    return any(k in tl for k in INTERCEPT)

def has_exclude(text: str) -> bool:
    tl = text.lower()
    if has_intercept(text):
        return False
    return any(k in tl for k in EXCLUDE)

# =========================
# تشغيل
# =========================
db = load()
keys = set(x["key"] for x in db)

now = datetime.now(timezone.utc)
daily_cut = now - timedelta(hours=24)

for url in RSS:
    feed = feedparser.parse(url)

    for e in feed.entries:
        title = clean(getattr(e, "title", ""))
        summary = clean(getattr(e, "summary", ""))
        text = f"{title} {summary}".strip()

        if not has_intercept(text):
            continue

        if has_exclude(text):
            continue

        c = detect_country(text)
        if not c:
            continue

        m, d = extract(text)
        if m == 0 and d == 0:
            continue

        pub = parse_published(e)
        if pub is None:
            # إذا ما فيه تاريخ نشر واضح، نتجاوزه حتى لا يخرّب اليومي
            continue

        # لا نأخذ أي شيء قبل 2026-02-28
        if pub < START_DATE:
            continue

        # بصمة أقوى قليلًا
        key_base = f"{c}|{title[:200]}|{pub.date().isoformat()}|{m}|{d}"
        key = hashlib.md5(key_base.encode("utf-8")).hexdigest()

        if key in keys:
            continue
        keys.add(key)

        db.append({
            "key": key,
            "country": c,
            "m": m,
            "d": d,
            "time": pub.isoformat(),
            "title": title
        })

# =========================
# حساب
# =========================
daily = {k: {"m": 0, "d": 0, "events": 0} for k in GULF}
total = {k: {"m": 0, "d": 0, "events": 0} for k in GULF}

for e in db:
    t = datetime.fromisoformat(e["time"])
    c = e["country"]

    if t >= daily_cut:
        daily[c]["m"] += e["m"]
        daily[c]["d"] += e["d"]
        daily[c]["events"] += 1

    if START_DATE <= t <= now:
        total[c]["m"] += e["m"]
        total[c]["d"] += e["d"]
        total[c]["events"] += 1

save(db)

# =========================
# تقرير
# =========================
def block(title, stats):
    lines = [title, f"🕒 {now.strftime('%Y-%m-%d')}", ""]
    total_m = total_d = total_e = 0

    for k, n in GULF.items():
        m = stats[k]["m"]
        d = stats[k]["d"]
        ev = stats[k]["events"]
        total_m += m
        total_d += d
        total_e += ev

        lines.append(n)
        lines.append(f"• 🚀 الصواريخ: {m}")
        lines.append(f"• 🛸 المسيّرات: {d}")
        lines.append(f"• 📰 عدد الأحداث: {ev}")
        lines.append("")

    lines.append("════════════════════")
    lines.append("📊 الإجمالي")
    lines.append(f"• 🚀 الصواريخ: {total_m}")
    lines.append(f"• 🛸 المسيّرات: {total_d}")
    lines.append(f"• 📰 عدد الأحداث: {total_e}")
    return "\n".join(lines)

msg = (
    block("📊 التقرير اليومي", daily)
    + "\n\n"
    + block("📊 منذ بداية الحرب (2026-02-28 حتى الآن)", total)
)

send(msg)
