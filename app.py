import os
import json
import random
from typing import Dict, Any

from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext

# -----------------------------
# إعدادات عامة
# -----------------------------
app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN غير مضبوط في المتغيرات")

bot = Bot(token=TOKEN)

# تحميل بنك الأسئلة من ملف واحد في جذر المشروع
with open("data.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

# حالة المستخدمين: نخزن آخر سؤال أرسلناه لكل مستخدم
user_state: Dict[int, Dict[str, Any]] = {}

# مِزاد Dispatcher
dp = Dispatcher(bot, None, workers=0, use_context=True)

# -----------------------------
# أدوات مساعدة
# -----------------------------
LETTER_MAP_AR = {"أ": 0, "ا": 0, "ب": 1, "ج": 2, "د": 3}
LETTER_MAP_EN = {"A": 0, "B": 1, "C": 2, "D": 3}

def choice_index_from_text(text: str):
    """يحاول يفهم إدخال المستخدم ويعيد رقم الخيار 0..3 أو None"""
    if not text:
        return None
    t = text.strip().upper()

    # أرقام 1..4
    if t in {"1", "2", "3", "4"}:
        return int(t) - 1

    # حروف عربية
    t_ar = t.replace("إ", "ا").replace("أ", "ا").replace("ٱ", "ا")
    if t_ar and t_ar[0] in LETTER_MAP_AR:
        return LETTER_MAP_AR[t_ar[0]]

    # حروف إنجليزية
    if t and t[0] in LETTER_MAP_EN:
        return LETTER_MAP_EN[t[0]]

    return None

def send_random_question(update: Update, context: CallbackContext):
    """يرسل سؤال عشوائي ويخزن حالته للمستخدم"""
    chat_id = update.effective_chat.id
    q = random.choice(QUESTIONS)

    # صياغة الرسالة
    msg = f"❓ {q['question']}\n\n"
    msg += "اختر إجابة واحدة:\n"
    # نعرض الخيارات بشكل مرتب 1..4 مع الحروف العربية
    labels = ["أ", "ب", "ج", "د"]
    for i, choice in enumerate(q["choices"]):
        # لو الخيارات نفسها فيها (أ) نعرض كما هي
        if "أ)" in choice or "ب)" in choice or "ج)" in choice or "د)" in choice:
            msg += f"- {choice}\n"
        else:
            msg += f"- {labels[i]}) {choice}\n"

    msg += "\nأرسل رقم الخيار (1-4) أو الحرف (أ/ب/ج/د)."

    # حفظ الحالة
    user_state[chat_id] = {
        "qid": q.get("id"),
        "answer_index": int(q["answer_index"]),
        "explanation": q.get("explanation", ""),
        "question": q,
    }

    update.message.reply_text(msg)

# -----------------------------
# Handlers
# -----------------------------
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 أهلاً بك في بوت قياس!\n"
        "سأعطيك سؤالاً عشوائياً مع خيارات.\n"
        "أرسل رقم الخيار (1-4) أو الحرف (أ/ب/ج/د)، وبعد التقييم أرسلك سؤال جديد.\n"
        "موفق 🤍"
    )
    send_random_question(update, context)

def handle_message(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    text = update.message.text or ""

    # إذا لا يوجد حالة سابقة، أرسل سؤال جديد
    if chat_id not in user_state:
        send_random_question(update, context)
        return

    state = user_state[chat_id]
    correct_index = state["answer_index"]
    q = state["question"]

    # حاول نفهم اختيار المستخدم
    idx = choice_index_from_text(text)

    # إن ما قدرنا نفهم، جرّبه كنص كامل يطابق أحد الخيارات
    if idx is None:
        norm = text.strip()
        for i, ch in enumerate(q["choices"]):
            if norm == ch or norm in ch:
                idx = i
                break

    # إذا ما زال None نطلب منه اختيار صحيح
    if idx is None or idx not in (0, 1, 2, 3):
        update.message.reply_text("❗️ أرسل رقم 1-4 أو حرف (أ/ب/ج/د) فقط.")
        return

    # قيّم الإجابة
    if idx == correct_index:
        reply = "✅ إجابة صحيحة!"
    else:
        labels = ["أ", "ب", "ج", "د"]
        reply = (
            "❌ إجابة غير صحيحة.\n"
            f"الصحيح: {labels[correct_index]}) {q['choices'][correct_index]}"
        )

    # أضف الشرح لو موجود
    exp = state.get("explanation", "")
    if exp:
        reply += f"\n\nالشرح: {exp}"

    update.message.reply_text(reply)

    # أرسل سؤال جديد مباشرة
    send_random_question(update, context)

# ربط الهاندلرز
dp.add_handler(CommandHandler("start", start))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# -----------------------------
# Flask Routes
# -----------------------------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dp.process_update(update)
    return "ok", 200

@app.route("/")
def index():
    return "بوت قياس شغال ✅", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
