import os, json, requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# === إعدادات أساسية ===
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
API = f"https://api.telegram.org/bot{TOKEN}"
WEBHOOK_SECRET_PATH = f"/{TOKEN}"  # نفس المسار الذي يظهر في اللوقس
DATA_FILE = os.environ.get("DATA_FILE", "/etc/secrets/data.json")  # أو data.json داخل الريبو

# حمّل بنك الأسئلة مرة واحدة عند التشغيل
QUESTIONS = []
def load_data():
    global QUESTIONS
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            QUESTIONS = json.load(f)
    except Exception as e:
        print(f"[data] فشل تحميل {DATA_FILE}: {e}")
        QUESTIONS = []

load_data()

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(f"{API}/sendMessage", json=payload, timeout=10)
    except Exception as e:
        print(f"[tg] send_message error: {e}")

# === Health check ===
@app.get("/")
def root():
    return "البوت تشتغل!", 200

# === نقطة الويب هوك (لا تغيّر المسار) ===
@app.post(WEBHOOK_SECRET_PATH)
def webhook():
    update = request.get_json(silent=True) or {}
    msg = (update.get("message") or update.get("edited_message")) or {}
    chat = msg.get("chat", {})
    chat_id = chat.get("id")

    if not chat_id:
        return jsonify(ok=True)

    text = (msg.get("text") or "").strip()

    # أوامر بسيطة للاختبار
    if text.lower() in ("/start", "start", "ابدأ"):
        send_message(chat_id, "مرحبًا! أرسل أي رقم سؤال (id) وأنا أرجع لك السؤال.")
        return jsonify(ok=True)

    # لو أرسل رقم سؤال
    if text.isdigit():
        qid = int(text)
        q = next((q for q in QUESTIONS if q.get("id") == qid), None)
        if not q:
            send_message(chat_id, f"السؤال رقم {qid} غير موجود.")
            return jsonify(ok=True)

        # رسم الخيارات كأزرار اختيارية
        keyboard = [[{"text": c}] for c in q.get("choices", [])]
        reply_markup = {"keyboard": keyboard, "one_time_keyboard": True, "resize_keyboard": True}
        send_message(chat_id, f"{q['question']}", reply_markup=reply_markup)
        return jsonify(ok=True)

    # محاولة مطابقة إجابة لو أرسل اختيار
    # (منطق بسيط: ابحث عن آخر سؤال أرسلناه غير محفوظ بالجلسة – لأجل السرعة نجيب إجابة مباشرة إن كان النص يطابق أي اختيار)
    # في نسخة الإنتاج استخدم تخزين جلسات.
    try:
        # ابحث عن سؤال يملك هذا الاختيار نصًا
        q = next((q for q in QUESTIONS if text in q.get("choices", [])), None)
        if q:
            idx = q.get("answer_index", 0)
            correct = q.get("choices", [])[idx]
            if text == correct:
                send_message(chat_id, f"✅ إجابة صحيحة!\nالشرح: {q.get('explanation','')}")
            else:
                send_message(chat_id, f"❌ الإجابة الصحيحة: {correct}\nالشرح: {q.get('explanation','')}")
            return jsonify(ok=True)
    except Exception as e:
        print(f"[logic] match error: {e}")

    # رد افتراضي
    send_message(chat_id, "أرسل /start أو رقم سؤال (مثال: 10).")
    return jsonify(ok=True)

# === تعيين الويب هوك (استدعِه مرة واحدة يدويًا عبر المتصفح) ===
@app.get("/setwebhook")
def set_webhook():
    base_url = os.environ.get("PUBLIC_URL", "").rstrip("/")  # مثال: https://qiyas-bot.onrender.com
    if not (TOKEN and base_url):
        return "حدد TELEGRAM_BOT_TOKEN و PUBLIC_URL أولاً.", 400

    url = f"{base_url}{WEBHOOK_SECRET_PATH}"
    r = requests.get(f"{API}/setWebhook", params={"url": url}, timeout=15)
    return r.text, 200
