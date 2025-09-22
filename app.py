import os
import json
import logging
import requests
from flask import Flask, request
from telegram import Bot, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext

# إعداد اللوجات
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# مفاتيح البيئة
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "openai/gpt-4o-mini")

if not TOKEN:
    raise RuntimeError("حدد TELEGRAM_BOT_TOKEN في المتغيرات")

bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

# تحميل بنك الأسئلة
with open("data.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

# تقدم المستخدمين + وضعية "اسأل قياس"
user_progress = {}     # user_id -> {index, correct, wrong}
ask_mode = set()       # المستخدمين في وضعية "اسأل قياس"

# القائمة الرئيسية
MAIN_MENU_KB = ReplyKeyboardMarkup(
    [
        ["🧠 اختبار القدرات"],
        ["📊 نتيجتي", "❓ اسأل قياس"]
    ],
    resize_keyboard=True
)

RESTART_TEXT = "🔁 إعادة الاختبار"
restart_kb = ReplyKeyboardMarkup([[RESTART_TEXT]], resize_keyboard=True, one_time_keyboard=True)

# =========================
# دوال مساعدة
# =========================
def reset_user(user_id: int):
    user_progress[user_id] = {"index": 0, "correct": 0, "wrong": 0}

def send_question(update: Update, context: CallbackContext, q_index: int, user_id: int):
    total_q = len(QUESTIONS)
    if q_index >= total_q:
        correct = user_progress[user_id]["correct"]
        wrong   = user_progress[user_id]["wrong"]
        total   = correct + wrong
        score   = round((correct / total) * 100, 2) if total > 0 else 0.0
        update.message.reply_text(
            f"🎉 خلصت الاختبار!\n\n"
            f"✅ صحيحة: {correct}\n"
            f"❌ خاطئة: {wrong}\n"
            f"📊 الدرجة: {score}%",
            reply_markup=restart_kb
        )
        return

    q = QUESTIONS[q_index]
    text = f"❓ السؤال {q_index+1}/{total_q}\n\n{q['question']}\n\n"
    for i, choice in enumerate(q.get("choices", []), start=1):
        text += f"{i}. {choice}\n"

    update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())

def ask_qiyas(prompt: str) -> str:
    """يرد على سؤال القدرات فقط بإجابات قصيرة"""
    keywords = ["قدرات", "اختبار", "كمي", "لفظي", "قدرة", "قياس"]
    if not any(word in prompt for word in keywords):
        return "⚠️ اكتب سؤال له علاقة باختبار القدرات فقط."

    if not AI_API_KEY:
        return "ℹ️ وضعية (اسأل قياس) غير مفعلة لأن AI_API_KEY غير مضبوط."

    try:
        r = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {AI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": AI_MODEL,
                "input": (
                    "جاوب بإيجاز وبالعربية (3–4 أسطر كحد أقصى) "
                    "على السؤال التالي المتعلق باختبار القدرات:\n\n"
                    f"{prompt}"
                )
            },
            timeout=30
        )
        data = r.json()
        if "output" in data and data["output"]:
            node = data["output"][0]["content"][0]
            return node.get("text", "⚠️ لم يصل رد من (اسأل قياس).").strip()
        return "⚠️ لم يصل رد من (اسأل قياس)."
    except Exception as e:
        logging.exception("AI error")
        return f"⚠️ خطأ أثناء الاتصال بـ (اسأل قياس): {e}"

# =========================
# أوامر
# =========================
def start(update: Update, context: CallbackContext):
    update.message.reply_text("مرحباً! اختر من الأزرار بالأسفل:", reply_markup=MAIN_MENU_KB)

def quiz(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    reset_user(user_id)
    update.message.reply_text("🚀 بدأنا اختبار القدرات. أجب برقم (1–4).", reply_markup=ReplyKeyboardRemove())
    send_question(update, context, 0, user_id)

def score(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in user_progress:
        update.message.reply_text("ℹ️ ابدأ أولاً بالضغط على (🧠 اختبار القدرات).", reply_markup=MAIN_MENU_KB)
        return
    prog = user_progress[user_id]
    idx  = prog["index"]
    c    = prog["correct"]
    w    = prog["wrong"]
    total = c + w
    pct   = round((c / total) * 100, 2) if total > 0 else 0.0
    update.message.reply_text(
        f"📊 نتيجتك:\n"
        f"السؤال الحالي: {min(idx+1, len(QUESTIONS))}/{len(QUESTIONS)}\n"
        f"✅ صحيحة: {c}\n"
        f"❌ خاطئة: {w}\n"
        f"📈 النسبة: {pct}%",
        reply_markup=MAIN_MENU_KB
    )

# =========================
# معالج الرسائل
# =========================
def handle_text(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = (update.message.text or "").strip()

    # أزرار القائمة
    if text == "🧠 اختبار القدرات":
        if user_id in ask_mode:
            ask_mode.discard(user_id)
        quiz(update, context)
        return

    if text == "📊 نتيجتي":
        score(update, context)
        return

    if text == "❓ اسأل قياس":
        ask_mode.add(user_id)
        update.message.reply_text(
            "اكتب سؤالك الآن 👇 (فقط أسئلة القدرات)",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    if text == "🔁 إعادة الاختبار":
        if user_id in ask_mode:
            ask_mode.discard(user_id)
        quiz(update, context)
        return

    # وضعية "اسأل قياس"
    if user_id in ask_mode:
        reply = ask_qiyas(text)
        update.message.reply_text(reply, reply_markup=MAIN_MENU_KB)
        ask_mode.discard(user_id)
        return

    # منطق الإجابة على الأسئلة
    if user_id not in user_progress:
        update.message.reply_text("💡 اختر من القائمة:", reply_markup=MAIN_MENU_KB)
        return

    q_index = user_progress[user_id]["index"]
    if q_index >= len(QUESTIONS):
        update.message.reply_text("✅ الاختبار انتهى. اختر من القائمة:", reply_markup=MAIN_MENU_KB)
        return

    if not text.isdigit():
        update.message.reply_text("⚠️ اكتب رقم الاختيار (1–4).")
        return

    choice_num = int(text) - 1
    if choice_num < 0 or choice_num > 3:
        update.message.reply_text("⚠️ الاختيارات من 1 إلى 4 فقط.")
        return

    q = QUESTIONS[q_index]
    if choice_num == q["answer_index"]:
        user_progress[user_id]["correct"] += 1
        update.message.reply_text(f"✅ إجابة صحيحة!\n{q.get('explanation','')}".strip())
    else:
        user_progress[user_id]["wrong"] += 1
        correct_choice = q["choices"][q["answer_index"]]
        update.message.reply_text(
            f"❌ خطأ.\nالصحيح: {correct_choice}\n{q.get('explanation','')}".strip()
        )

    user_progress[user_id]["index"] = q_index + 1
    send_question(update, context, user_progress[user_id]["index"], user_id)

# =========================
# Handlers
# =========================
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("quiz", quiz))
dispatcher.add_handler(CommandHandler("score", score))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

# Webhook
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/", methods=["GET"])
def home():
    return "✅ البوت شغال!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
