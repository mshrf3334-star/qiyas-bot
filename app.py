# app.py
import os
import json
import logging
import subprocess
from flask import Flask, request

# تلغرام v13
from telegram import Bot, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext

# -----------------------------
# لوجز واضحة
# -----------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("qiyas-bot")

# -----------------------------
# إعداد التوكن
# -----------------------------
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("حدد TELEGRAM_BOT_TOKEN في المتغيرات")

bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=0)

# -----------------------------
# إنشاء data.json تلقائيًا إن لم يوجد
# -----------------------------
DATA_PATH = "data.json"

if not os.path.exists(DATA_PATH):
    try:
        # يشغّل السكربت اللي يولّد بنك الأسئلة
        subprocess.run(["python", "make_data.py"], check=True)
        logger.info("✅ تم إنشاء data.json تلقائيًا عبر make_data.py")
    except Exception as e:
        logger.error("⚠️ خطأ أثناء إنشاء data.json: %s", e)

# -----------------------------
# تحميل بنك الأسئلة
# -----------------------------
try:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        QUESTIONS = json.load(f)
except Exception as e:
    logger.error("تعذّر تحميل %s: %s", DATA_PATH, e)
    QUESTIONS = []

if not isinstance(QUESTIONS, list):
    logger.error("صيغة %s غير صحيحة؛ يجب أن تكون قائمة أسئلة.", DATA_PATH)
    QUESTIONS = []

# -----------------------------
# إدارة تقدّم المستخدمين
# user_id -> { index, correct, wrong }
# -----------------------------
user_progress = {}

# كيبورد رئيسي
BTN_START_QUIZ = "📝 اختبر نفسك"
BTN_RESTART    = "🔁 إعادة الاختبار"

main_kb = ReplyKeyboardMarkup(
    [[BTN_START_QUIZ]],
    resize_keyboard=True
)
restart_kb = ReplyKeyboardMarkup(
    [[BTN_RESTART]],
    resize_keyboard=True,
    one_time_keyboard=True
)

def reset_user(user_id: int):
    user_progress[user_id] = {"index": 0, "correct": 0, "wrong": 0}

# -----------------------------
# إرسال سؤال
# -----------------------------
def send_question(update: Update, context: CallbackContext, q_index: int, user_id: int):
    total_q = len(QUESTIONS)

    if total_q == 0:
        update.message.reply_text("⚠️ لا توجد أسئلة حالياً. ارفع/أنشئ data.json ثم أعد المحاولة.")
        return

    # انتهى الاختبار
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
    header = f"❓ السؤال {q_index+1}/{total_q}\n\n"
    body   = f"{q.get('question','')}\n\n"
    choices = q.get("choices", [])
    for i, choice in enumerate(choices, start=1):
        body += f"{i}. {choice}\n"

    update.message.reply_text(header + body, reply_markup=ReplyKeyboardRemove())

# -----------------------------
# أوامر
# -----------------------------
def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    reset_user(user_id)
    update.message.reply_text(
        "🚀 أهلاً بك! اختر من الأسفل:",
        reply_markup=main_kb
    )

def quiz(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    reset_user(user_id)
    update.message.reply_text("✅ بدأ الاختبار. أجب برقم (1–4).", reply_markup=ReplyKeyboardRemove())
    send_question(update, context, 0, user_id)

def score(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in user_progress:
        update.message.reply_text("ℹ️ اكتب /quiz للبدء ثم استخدم /score لعرض نتيجتك.")
        return
    prog = user_progress[user_id]
    idx = prog["index"]
    correct = prog["correct"]
    wrong = prog["wrong"]
    total = correct + wrong
    pct = round((correct / total) * 100, 2) if total > 0 else 0.0
    update.message.reply_text(
        f"📊 نتيجتك الحالية:\n"
        f"السؤال الحالي: {min(idx+1, len(QUESTIONS))}/{len(QUESTIONS)}\n"
        f"✅ صحيحة: {correct}\n"
        f"❌ خاطئة: {wrong}\n"
        f"📈 النسبة: {pct}%"
    )

# -----------------------------
# المعالجة النصية
# -----------------------------
def handle_text(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = (update.message.text or "").strip()

    # أزرار القائمة
    if text == BTN_START_QUIZ:
        return quiz(update, context)

    if text == BTN_RESTART:
        reset_user(user_id)
        update.message.reply_text("🔁 بدأنا من جديد! بالتوفيق 🤍", reply_markup=ReplyKeyboardRemove())
        return send_question(update, context, 0, user_id)

    # إذا المستخدم ما بدأ
    if user_id not in user_progress:
        update.message.reply_text("💡 اختر (📝 اختبر نفسك) أو اكتب /quiz للبدء.")
        return

    # لو خلص الأسئلة
    q_index = user_progress[user_id]["index"]
    if q_index >= len(QUESTIONS):
        update.message.reply_text("✅ انتهى الاختبار. اضغط (🔁 إعادة الاختبار) لبدء جديد.", reply_markup=restart_kb)
        return

    # التحقق من الإجابة
    if not text.isdigit():
        update.message.reply_text("⚠️ اكتب رقم الاختيار (1، 2، 3، 4).")
        return

    choice_num = int(text) - 1
    if choice_num < 0 or choice_num > 3:
        update.message.reply_text("⚠️ الاختيارات من 1 إلى 4 فقط.")
        return

    q = QUESTIONS[q_index]
    answer_index = q.get("answer_index", 0)
    explanation  = q.get("explanation", "")
    choices      = q.get("choices", [])

    if choice_num == answer_index:
        user_progress[user_id]["correct"] += 1
        msg = "✅ إجابة صحيحة!"
        if explanation:
            msg += f"\n{explanation}"
        update.message.reply_text(msg)
    else:
        user_progress[user_id]["wrong"] += 1
        correct_choice = choices[answer_index] if 0 <= answer_index < len(choices) else "—"
        msg = f"❌ خطأ.\nالصحيح: {correct_choice}"
        if explanation:
            msg += f"\n{explanation}"
        update.message.reply_text(msg)

    # التالي
    user_progress[user_id]["index"] = q_index + 1
    send_question(update, context, user_progress[user_id]["index"], user_id)

# -----------------------------
# ربط الهاندلرز
# -----------------------------
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("quiz", quiz))
dispatcher.add_handler(CommandHandler("score", score))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

# -----------------------------
# Webhook + Health
# -----------------------------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
    except Exception as e:
        logger.exception("Webhook error: %s", e)
    return "ok"

@app.route("/", methods=["GET"])
def home():
    return "✅ Qiyas Bot is running!"

# للتشغيل المحلي إن احتجت
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
