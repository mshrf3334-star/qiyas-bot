import os
import json
import logging
import subprocess
import requests
from flask import Flask, request
from telegram import Bot, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext

# -----------------------------
# إعداد اللوجات
# -----------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("qiyas-bot")

# -----------------------------
# التوكن
# -----------------------------
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("حدد TELEGRAM_BOT_TOKEN في المتغيرات")

AI_API_KEY = os.getenv("AI_API_KEY")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.openai.com/v1/chat/completions")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")

bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=0)

# -----------------------------
# تحميل data.json
# -----------------------------
DATA_PATH = "data.json"
if not os.path.exists(DATA_PATH):
    try:
        subprocess.run(["python", "make_data.py"], check=True)
        logger.info("✅ تم إنشاء data.json تلقائياً")
    except Exception as e:
        logger.error("⚠️ خطأ أثناء إنشاء data.json: %s", e)

try:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        QUESTIONS = json.load(f)
except Exception as e:
    logger.error("تعذّر تحميل %s: %s", DATA_PATH, e)
    QUESTIONS = []

if not isinstance(QUESTIONS, list):
    QUESTIONS = []

# بنك خاص بالضرب
MULTIPLY_QUESTIONS = [
    q for q in QUESTIONS
    if ("tags" in q and any("ضرب" == t for t in q.get("tags", [])))
       or ("×" in q.get("question", ""))
]

# -----------------------------
# إدارة تقدم المستخدمين
# -----------------------------
user_progress = {}

BTN_START_QUIZ = "📝 اختبر نفسك"
BTN_RESTART    = "🔁 إعادة الاختبار"
BTN_AI         = "🤖 اسأل قياس"
BTN_MULTIPLY   = "📚 جدول الضرب"

main_kb = ReplyKeyboardMarkup(
    [[BTN_START_QUIZ, BTN_AI],
     [BTN_MULTIPLY]],
    resize_keyboard=True
)
restart_kb = ReplyKeyboardMarkup(
    [[BTN_RESTART]],
    resize_keyboard=True,
    one_time_keyboard=True
)

def reset_user(user_id: int, bank: str = "all"):
    user_progress[user_id] = {"index": 0, "correct": 0, "wrong": 0, "bank": bank}

def get_active_bank(user_id: int):
    bank = user_progress.get(user_id, {}).get("bank", "all")
    return MULTIPLY_QUESTIONS if bank == "multiply" else QUESTIONS

# -----------------------------
# إرسال سؤال
# -----------------------------
def send_question(update: Update, context: CallbackContext, q_index: int, user_id: int):
    ACTIVE = get_active_bank(user_id)
    total_q = len(ACTIVE)
    if total_q == 0:
        update.message.reply_text("⚠️ لا توجد أسئلة حالياً.")
        return

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

    q = ACTIVE[q_index]
    header = f"❓ السؤال {q_index+1}/{total_q}\n\n"
    body   = f"{q.get('question','')}\n\n"
    for i, choice in enumerate(q.get("choices", []), start=1):
        body += f"{i}. {choice}\n"

    update.message.reply_text(header + body, reply_markup=ReplyKeyboardRemove())

# -----------------------------
# أوامر
# -----------------------------
def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    reset_user(user_id)
    update.message.reply_text("🚀 أهلاً بك! اختر من الأسفل:", reply_markup=main_kb)

def quiz(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    reset_user(user_id, bank="all")
    update.message.reply_text("✅ بدأ الاختبار. أجب برقم (1–4).", reply_markup=ReplyKeyboardRemove())
    send_question(update, context, 0, user_id)

def score(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in user_progress:
        update.message.reply_text("ℹ️ اكتب /quiz للبدء ثم /score لعرض نتيجتك.")
        return
    prog = user_progress[user_id]
    ACTIVE = get_active_bank(user_id)
    idx = prog["index"]
    correct = prog["correct"]
    wrong = prog["wrong"]
    total = correct + wrong
    pct = round((correct / total) * 100, 2) if total > 0 else 0.0
    update.message.reply_text(
        f"📊 نتيجتك الحالية:\n"
        f"السؤال الحالي: {min(idx+1, len(ACTIVE))}/{len(ACTIVE)}\n"
        f"✅ صحيحة: {correct}\n"
        f"❌ خاطئة: {wrong}\n"
        f"📈 النسبة: {pct}%"
    )

def count_cmd(update: Update, context: CallbackContext):
    update.message.reply_text(f"📦 عدد الأسئلة: {len(QUESTIONS)}")

def count_mul(update: Update, context: CallbackContext):
    update.message.reply_text(f"✖️ عدد أسئلة الضرب: {len(MULTIPLY_QUESTIONS)}")

# -----------------------------
# معالجة النصوص
# -----------------------------
def handle_text(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = (update.message.text or "").strip()

    if text == BTN_START_QUIZ:
        return quiz(update, context)
    if text == BTN_RESTART:
        reset_user(user_id, bank="all")
        update.message.reply_text("🔁 بدأنا من جديد!", reply_markup=ReplyKeyboardRemove())
        return send_question(update, context, 0, user_id)
    if text == BTN_MULTIPLY:
        reset_user(user_id, bank="multiply")
        update.message.reply_text("✅ بدأ اختبار جدول الضرب.", reply_markup=ReplyKeyboardRemove())
        return send_question(update, context, 0, user_id)
    if text == BTN_AI:
        update.message.reply_text("🧠 أرسل سؤالك إلى *قياس*:", parse_mode="Markdown")
        context.user_data["ai_mode"] = True
        return

    if context.user_data.get("ai_mode"):
        context.user_data["ai_mode"] = False
        reply = ask_ai(text)
        update.message.reply_text(f"🤖 إجابة قياس:\n\n{reply}")
        return

    if user_id not in user_progress:
        update.message.reply_text("💡 اختر (📝 اختبر نفسك) أو (📚 جدول الضرب).")
        return

    ACTIVE = get_active_bank(user_id)
    q_index = user_progress[user_id]["index"]
    if q_index >= len(ACTIVE):
        update.message.reply_text("✅ انتهى الاختبار. اضغط (🔁 إعادة الاختبار).", reply_markup=restart_kb)
        return

    if not text.isdigit():
        update.message.reply_text("⚠️ اكتب رقم الاختيار (1–4).")
        return

    choice_num = int(text) - 1
    if choice_num < 0 or choice_num > 3:
        update.message.reply_text("⚠️ الاختيارات من 1 إلى 4 فقط.")
        return

    q = ACTIVE[q_index]
    if choice_num == q.get("answer_index", 0):
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

# -----------------------------
# التكامل مع الذكاء الاصطناعي (قياس)
# -----------------------------
def ask_ai(question: str) -> str:
    if not AI_API_KEY:
        return "⚠️ مفتاح قياس غير محدد."
    try:
        headers = {"Authorization": f"Bearer {AI_API_KEY}"}
        payload = {
            "model": AI_MODEL,
            "messages": [
                {"role": "system", "content": "أنت مساعد خبير في اختبار القدرات اسمه قياس."},
                {"role": "user", "content": question}
            ]
        }
        resp = requests.post(AI_BASE_URL, headers=headers, json=payload, timeout=30)
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ خطأ من قياس: {e}"

# -----------------------------
# ربط الأوامر
# -----------------------------
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("quiz", quiz))
dispatcher.add_handler(CommandHandler("score", score))
dispatcher.add_handler(CommandHandler("count", count_cmd))
dispatcher.add_handler(CommandHandler("count_mul", count_mul))
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
