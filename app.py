import os
import json
import random
from flask import Flask, request
import requests

app = Flask(__name__)

# ===== إعدادات البيئة =====
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")

TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

# ===== تحميل بنك الأسئلة =====
QUESTIONS = []
try:
    with open("data/qiyas_questions.json", "r", encoding="utf-8") as f:
        QUESTIONS = json.load(f)
except Exception as e:
    print("⚠️ لم يتم تحميل بنك الأسئلة:", e)

# حالة الجلسات لكل محادثة (داخل الذاكرة)
SESSION = {}  # { chat_id: {"mode": "quiz"|"ai", "q": {..}, "awaiting": True, "correct": int, "total": int} }

def send_message(chat_id, text):
    if len(text) > 4096:
        text = text[:4090] + " ..."
    requests.post(f"{TELEGRAM_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def format_question(q):
    lines = [f"سؤال #{q.get('id')}: {q['question']}"]
    for i, ch in enumerate(q["choices"]):
        lines.append(ch)
    lines.append("\nأرسل حرف الاختيار: أ أو ب أو ج أو د")
    return "\n".join(lines)

def pick_question():
    return random.choice(QUESTIONS) if QUESTIONS else None

def letter_to_index(letter):
    letter = letter.strip().replace(" ", "")
    mapping = {"أ":0, "ا":0, "ب":1, "ج":2, "د":3, "A":0, "B":1, "C":2, "D":3}
    return mapping.get(letter, None)

def ask_ai(prompt):
    if not AI_API_KEY:
        return "⚠️ مفتاح الذكاء الاصطناعي غير مضبوط (AI_API_KEY)."
    headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": "أنت مساعد ذكي لاختبارات القدرات (Qiyas). جاوب بالعربية باختصار ووضوح."},
            {"role": "user", "content": prompt}
        ]
    }
    try:
        r = requests.post(OPENAI_URL, headers=headers, json=payload, timeout=25)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        else:
            print("OpenAI error:", r.status_code, r.text)
            return "⚠️ تعذّر الاتصال بالذكاء الاصطناعي. تأكد من AI_API_KEY و AI_MODEL."
    except Exception as e:
        print("OpenAI exception:", e)
        return "⚠️ صار خطأ أثناء الاتصال بالذكاء الاصطناعي."

@app.route("/", methods=["GET"])
def home():
    return "🤖 Qiyas Bot is running with Quiz + AI"

@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json(silent=True) or {}
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return "no message", 200

    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()

    # إنشاء جلسة افتراضية
    if chat_id not in SESSION:
        SESSION[chat_id] = {"mode": "ai", "q": None, "awaiting": False, "correct": 0, "total": 0}

    # أوامر سريعة
    if text.lower() in ["/start", "start", "ابدأ", "بداية"]:
        send_message(chat_id,
            "مرحبًا بك في بوت القدرات ✅\n\n"
            "الأوامر:\n"
            "• اكتب: اسئلة قدرات — للدخول في وضع المسابقة\n"
            "• اكتب: التالي — لسؤال جديد\n"
            "• اكتب: خروج — للخروج من وضع المسابقة\n"
            "• أو اسأل أي سؤال وسأحاول مساعدتك بالذكاء الاصطناعي"
        )
        return "ok", 200

    if text in ["خروج", "انهاء", "إنهاء", "exit"]:
        SESSION[chat_id] = {"mode": "ai", "q": None, "awaiting": False, "correct": 0, "total": 0}
        send_message(chat_id, "تم الخروج من وضع المسابقة. أرسل أي سؤال وسأساعدك.")
        return "ok", 200

    # الدخول لوضع المسابقة
    if text in ["اسئلة قدرات", "أسئلة قدرات", "مسابقة", "سؤال", "اختبار"]:
        SESSION[chat_id]["mode"] = "quiz"
        q = pick_question()
        if not q:
            send_message(chat_id, "لا يوجد بنك أسئلة حالياً. أضف أسئلة في data/qiyas_questions.json.")
            return "ok", 200
        SESSION[chat_id]["q"] = q
        SESSION[chat_id]["awaiting"] = True
        SESSION[chat_id]["total"] += 1
        send_message(chat_id, format_question(q))
        return "ok", 200

    # سؤال جديد أثناء وضع المسابقة
    if text in ["التالي", "سؤال جديد"] and SESSION[chat_id]["mode"] == "quiz":
        q = pick_question()
        if not q:
            send_message(chat_id, "لا يوجد بنك أسئلة كافٍ حالياً.")
            return "ok", 200
        SESSION[chat_id]["q"] = q
        SESSION[chat_id]["awaiting"] = True
        SESSION[chat_id]["total"] += 1
        send_message(chat_id, format_question(q))
        return "ok", 200

    # التقييم أثناء وضع المسابقة
    if SESSION[chat_id]["mode"] == "quiz" and SESSION[chat_id]["awaiting"]:
        idx = letter_to_index(text)
        q = SESSION[chat_id]["q"]
        if idx is None:
            send_message(chat_id, "رجاءً أرسل حرف الاختيار: أ / ب / ج / د")
            return "ok", 200
        correct = q["answer_index"]
        if idx == correct:
            SESSION[chat_id]["correct"] += 1
            send_message(chat_id, "✅ إجابة صحيحة!\n" + f"التفسير: {q['explanation']}\n\nاكتب: التالي — لسؤال جديد")
        else:
            send_message(chat_id, "❌ إجابة غير صحيحة.\n" +
                         f"الإجابة الصحيحة هي: {['أ','ب','ج','د'][correct]} \n" +
                         f"التفسير: {q['explanation']}\n\nاكتب: التالي — لسؤال جديد")
        SESSION[chat_id]["awaiting"] = False
        return "ok", 200

    # افتراضيًا: ذكاء اصطناعي
    reply = ask_ai(text) if text else "أرسل نصًا وسأساعدك."
    send_message(chat_id, reply)
    return "ok", 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
