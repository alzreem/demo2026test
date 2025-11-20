# ===============================================
#  shadow_hunter_batch_fast.py   (Pydroid-3 ready)
#  نسخة مُسرّعة — جمع روابط فقط (بدون فحص SQL)
# ===============================================
import requests, re, time
from urllib.parse import quote_plus, urlparse
from telebot import TeleBot
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

# ---------- Telegram ----------
TOKEN   = "8054578360:AAE4-PAEetO-XSSU3-7cTCEEsGZ0MUOp78w"
CHAT_ID = "7856736153"
bot = TeleBot(TOKEN, threaded=False)

# ---------- search engines (10) ----------
ENGINES = {
    "bing"      : "https://www.bing.com/search?q={q}&first={start}",
    "brave"     : "https://search.brave.com/search?q={q}&offset={start}",
    "startpage" : "https://www.startpage.com/sp/search?query={q}&page={page}",
    "mojeek"    : "https://www.mojeek.com/search?q={q}&s={start}",
    "qwant"     : "https://www.qwant.com/?q={q}&start={start}",
    "ecosia"    : "https://www.ecosia.org/search?q={q}&p={page}",
    "searx_be"  : "https://searx.be/search?q={q}&p={page}",
    "searx_tie" : "https://searx.tiekoetter.com/search?q={q}&p={page}",
    "swisscows" : "https://swisscows.com/web?query={q}&page={page}",
    "ask"       : "https://www.ask.com/web?q={q}&page={page}"
}

# ---------- tuning (عدل القيم هنا حسب حاجتك) ----------
THREADS = 300          # عدد الخيوط المتوازية (وحشي)
PAGES_PER_ENGINE = 2   # كم صفحة لكل محرك لكل dork (ابدأ صغير ثم زيد لو تريد)
REQUEST_TIMEOUT = 8
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_2)",
    "Mozilla/5.0 (Android 11; Mobile)",
]

# ---------- banned lists (تبقى كما تريد) ----------
BANNED_DOMAINS = {
    'google','youtube','facebook','linkedin','instagram','microsoft','mozilla',
    'wikipedia','amazon','apple','bing','yahoo','baidu','duckduckgo','tumblr',
    'reddit','netflix','adobe','whatsapp','pinterest','yandex','cloudflare',
    'dropbox','paypal','tiktok','weebly','wix','webnode','github','gitlab',
    'sourceforge','opera','vimeo','blogspot','wordpress','blogger','live.com',
    'msn.com','doubleclick','bbc','cnn','aljazeera','sky.com','forbes','nytimes',
    'reuters','huffpost','stackoverflow','slack.com','zendesk','skype','office.com',
    'zoom','webex','archive.org','tripadvisor','booking.com','airbnb','uber','lyft',
    'spotify','deezer','soundcloud','naver','vk.com','mail.ru','ask.com','aol.com',
    'myspace','quora','slideshare','trello','bitbucket','telegram','discord',
    'notion.so','canva.com','figma.com','coursera','edx.org','udemy','khanacademy',
    'udacity','openai','icloud.com','fast.com','norton','kaspersky','virustotal',
    'gstatic','edge.microsoft.com'
}

BANNED_KEYWORDS = {
    'login','logout','signin','signup','account','profile','register','auth',
    'watch','video','playlist','search','ads','utm_','gclid','fbclid','redirect',
    'rss','feed','comment','sort','filter','json','xml','api','static','assets',
    'cache','blog','tag','category','wordpress','preview','help','support',
    'privacy','terms','contact','about','news','press','careers','jobs','status',
    'feedback','donate','sitemap','cookie','robots'
}

BANNED_EXTS = (
    '.jpg','.jpeg','.png','.svg','.gif','.ico',
    '.css','.js','.woff','.ttf','.eot',
    '.pdf','.doc','.xls','.zip','.rar','.exe',
    '.mp4','.mp3','.avi','.mov'
)

# ---------- helpers ----------
def is_valid(url:str) -> bool:
    """تأكد أن الرابط يمر الفلاتر (بُنيت على ما عندك)."""
    try:
        if "id=" not in url.lower(): 
            return False
        if any(url.lower().endswith(ext) for ext in BANNED_EXTS):
            return False
        if any(k in url.lower() for k in BANNED_KEYWORDS):
            return False
        net = urlparse(url).netloc.lower()
        if any(dom in net for dom in BANNED_DOMAINS):
            return False
        return True
    except:
        return False

def load_dorks(path:str="sqli_dorks.txt") -> list[str]:
    try:
        with open(path, encoding="utf-8") as f:
            items = [ln.strip() for ln in f if ln.strip()]
            print(f"[debug] load_dorks -> {len(items)} dorks")
            return items
    except FileNotFoundError:
        print(f"[debug] {path} غير موجود.")
        return []

# ---------- fast page fetch (session per thread) ----------
def fetch_url(session, url):
    try:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        r = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            return re.findall(r"https?://[^\s\"\'<>]+", r.text)
    except:
        pass
    return []

def search_dork(dork:str) -> list[str]:
    """يبني لائحة الروابط من محركات البحث (موازي على مستوى الصفحات)."""
    q = quote_plus(dork)
    targets = []
    for name, tmpl in ENGINES.items():
        for p in range(PAGES_PER_ENGINE):
            # بعض القوالب تستخدم start وبعضها page - نمرّر كلاهما
            targets.append(tmpl.format(q=q, start=p*10, page=p+1))

    results = []
    # نستخدم ThreadPoolExecutor لجلب الصفحات بسرعة
    with ThreadPoolExecutor(max_workers=min(THREADS, len(targets) or 1)) as ex:
        futures = []
        for t in targets:
            # كل ثريد ينشئ Session خاص به لتسريع المتعدد الاتصالات
            futures.append(ex.submit(lambda url: fetch_url(requests.Session(), url), t))

        for fut in as_completed(futures):
            try:
                links = fut.result()
                if links:
                    results.extend(links)
            except:
                pass

    # return raw links (التنظيف يتم لاحقاً)
    return list(set(results))


def send_batch_report(batch_id:int, scanned:int, links:list[str]):
    """يرسل ملخص للتيليغرام (روابط فقط — لا فحص)."""
    msg = f"📝 Batch #{batch_id}\nروابط مفحوصة: {scanned}\nروابط: {len(links)}"
    try:
        bot.send_message(CHAT_ID, msg)
    except:
        pass
    # يرسل أول 20 رابط فقط لتقليل الرسائل (عدل إذا تريد)
    try:
        for link in links[:20]:
            bot.send_message(CHAT_ID, link)
    except:
        pass

# ---------- main cycle (بدون أي فحص SQL) ----------
def run_cycle():
    dorks = load_dorks()
    if not dorks:
        return

    print("🚀 بدء الجمع السريع 300-THREAD …")

    # جمع كل الروابط من كل الدوركس بسرعة (موازي على مستوى الدوركس)
    collected = []

    # fast collection: لكل dork نطلق search_dork موازيّاً
    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        futures = {ex.submit(search_dork, d): d for d in dorks}
        for fut in as_completed(futures):
            try:
                res = fut.result()
                if res:
                    collected.extend(res)
            except:
                pass

    # تنظيف + فلترة + تجميع للـ batches
    seen = set()
    batch_id = 1
    current_batch = []

    for raw in collected:
        clean = raw.split("&")[0]
        if not is_valid(clean):
            continue
        if clean in seen:
            continue
        seen.add(clean)
        current_batch.append(clean)

        if len(current_batch) >= 30:
            send_batch_report(batch_id, len(current_batch), current_batch)
            batch_id += 1
            current_batch = []

    # بقايا
    if current_batch:
        send_batch_report(batch_id, len(current_batch), current_batch)

    try:
        bot.send_message(CHAT_ID, "✅ الدورة اكتملت (نسخة سريعة).")
    except:
        pass

# ---------- hourly loop ----------
if __name__ == "__main__":
    while True:
        print("\n⏰ تشغيل جديد …")
        run_cycle()
        print("🕒 نوم 1 ساعة …")
        time.sleep(3600)