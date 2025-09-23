import os
import json
from flask import Flask, request, abort
import telebot  # pyTelegramBotAPI

# ===== إعدادات من المتغيرات البيئية =====
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")               # حط التوكن في Render > Environment
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "webhook")   # اسم مسار الويبهوك (اختاره بنفسك)
APP_URL = os.getenv("APP_URL", "https://qiyas-bot.onrender.com")  # رابط خدمتك على Render

# مسار بنك الأسئلة:
# لو تستخدم Secret Files في Render سمِّ الملف مثلا data.json (بدون مسار)
# بيتركب أوتوماتيك في: /etc/secrets/data.json
DATA_PATH = os.getenv("DATA_PATH", "/etc/secrets/data.json")  # غيّره إلى data/data.json لو الملف داخل الريبو

# ===== تهيئة البوت و Flask =====
if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN غير موجود")

bot = telebot.TeleBot(BOT_TOKEN, threaded=False, num_threads=1)
app = Flask(__name__)

# ===== بنك الأسئلة (اختياري) =====
def load_questions():
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] فشل قراءة بنك الأسئلة: {e}")
        return []

QUESTIONS = load_questions()

# ===== هاندلرز بسيطة للاختبار =====
@bot.message_handler(commands=["start", "help"])
def handle_start(m):
    bot.reply_to(m, "مرحبًا 👋\nالبوت شغّال ✅\nأرسل كلمة: اختبار")

@bot.message_handler(func=lambda m: m.text and m.text.strip() == "اختبار")
def handle_test(m):
    if not QUESTIONS:
        bot.reply_to(m, "بنك الأسئلة فاضي أو ما انقرأ. تأكد من DATA_PATH/Secret File.")
        return
    q = QUESTIONS[0]
    text = f"{q['question']}\n" + "\n".join(f"{i+1}) {c}" for i, c in enumerate(q["choices"]))
    bot.reply_to(m, text)

# ===== مسارات الويب =====
@app.get("/")
def index():
    return "البوت شغّال ✅", 200

# مهم: هذا المسار لازم يطابق اللي بتحطه في setWebhook
@app.post(f"/{WEBHOOK_SECRET}/{BOT_TOKEN}")
def telegram_webhook():
    if request.headers.get("content-type") != "application/json":
        return abort(403)
    update = request.get_data().decode("utf-8")
    bot.process_new_updates([telebot.types.Update.de_json(update)])
    return "ok", 200
