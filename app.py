import os
import json
import logging
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد اللوجات
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("حدد TELEGRAM_BOT_TOKEN في المتغيرات")

application = Application.builder().token(TOKEN).build()
app = Flask(__name__)

# تحميل بنك الأسئلة
try:
    with open("data.json", "r", encoding="utf-8") as f:
        QUESTIONS = json.load(f)
except FileNotFoundError:
    QUESTIONS = []
    logging.error("⚠️ ملف data.json غير موجود!")

user_progress = {}
RESTART_TEXT = "🔁 إعادة الاختبار"
restart_kb = ReplyKeyboardMarkup([[RESTART_TEXT]], resize_keyboard=True)

def reset_user(user_id: int):
    user_progress[user_id] = {"index": 0, "correct": 0, "wrong": 0}

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, q_index: int, user_id: int):
    if not QUESTIONS:
        await update.message.reply_text("❌ لا توجد أسئلة متاحة.")
        return

    total_q = len(QUESTIONS)
    if q_index >= total_q:
        correct = user_progress[user_id]["correct"]
        wrong = user_progress[user_id]["wrong"]
        total = correct + wrong
        score = round((correct / total) * 100, 2) if total > 0 else 0.0

        await update.message.reply_text(
            f"🎉 خلصت الاختبار!\n\n✅ صحيحة: {correct}\n❌ خاطئة: {wrong}\n📊 الدرجة: {score}%",
            reply_markup=restart_kb
        )
        return

    q = QUESTIONS[q_index]
    text = f"❓ السؤال {q_index+1}/{total_q}\n\n{q['question']}\n\n"
    for i, choice in enumerate(q["choices"], start=1):
        text += f"{i}. {choice}\n"

    await update.message.reply_text(text)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    reset_user(user_id)
    await update.message.reply_text("🚀 أهلاً! ابدأ الاختبار الآن. أجب برقم (1–4).")
    await send_question(update, context, 0, user_id)

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    reset_user(user_id)
    await send_question(update, context, 0, user_id)

async def score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_progress:
        await update.message.reply_text("💡 اكتب /quiz للبدء.")
        return
    
    prog = user_progress[user_id]
    correct = prog["correct"]
    wrong = prog["wrong"]
    total = correct + wrong
    score_pct = round((correct / total) * 100, 2) if total > 0 else 0.0
    
    await update.message.reply_text(
        f"📊 نتيجتك:\n✅ صحيحة: {correct}\n❌ خاطئة: {wrong}\n📈 النسبة: {score_pct}%"
    )

async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if text == RESTART_TEXT:
        reset_user(user_id)
        await update.message.reply_text("🔁 بدأنا من جديد! بالتوفيق 🤍")
        await send_question(update, context, 0, user_id)
        return

    if user_id not in user_progress:
        await update.message.reply_text("💡 اكتب /quiz للبدء.")
        return

    q_index = user_progress[user_id]["index"]
    if q_index >= len(QUESTIONS):
        await update.message.reply_text("✅ الاختبار انتهى.", reply_markup=restart_kb)
        return

    q = QUESTIONS[q_index]

    if not text.isdigit() or not (1 <= int(text) <= 4):
        await update.message.reply_text("⚠️ اكتب رقم من 1 إلى 4 فقط.")
        return

    choice_num = int(text) - 1
    if choice_num == q["answer_index"]:
        user_progress[user_id]["correct"] += 1
        await update.message.reply_text(f"✅ صحيح!\n{q.get('explanation','')}".strip())
    else:
        user_progress[user_id]["wrong"] += 1
        correct_choice = q["choices"][q["answer_index"]]
        await update.message.reply_text(f"❌ خطأ. الصحيح: {correct_choice}")

    user_progress[user_id]["index"] += 1
    await send_question(update, context, user_progress[user_id]["index"], user_id)

# تسجيل ال handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("quiz", quiz))
application.add_handler(CommandHandler("score", score))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer))

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    json_data = request.get_json()
    update = Update.de_json(json_data, application.bot)
    application.update_queue.put(update)
    return "OK"

@app.route("/", methods=["GET"])
def index():
    return "✅ البوت شغال!"

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    webhook_url = f"https://{request.host}/webhook/{TOKEN}"
    application.bot.set_webhook(webhook_url)
    return f"✅ Webhook set to: {webhook_url}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
