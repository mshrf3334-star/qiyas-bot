import os
import json
import logging
import requests
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

# التطبيق الجديد بدلاً من Dispatcher
application = Application.builder().token(TOKEN).build()

app = Flask(__name__)

# تحميل بنك الأسئلة
with open("data.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

# تقدم المستخدمين
user_progress = {}

# كيبورد إعادة التشغيل
RESTART_TEXT = "🔁 إعادة الاختبار"
restart_kb = ReplyKeyboardMarkup([[RESTART_TEXT]], resize_keyboard=True, one_time_keyboard=True)

def reset_user(user_id: int):
    user_progress[user_id] = {"index": 0, "correct": 0, "wrong": 0}

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, q_index: int, user_id: int):
    total_q = len(QUESTIONS)

    if q_index >= total_q:
        correct = user_progress[user_id]["correct"]
        wrong = user_progress[user_id]["wrong"]
        total = correct + wrong
        score = round((correct / total) * 100, 2) if total > 0 else 0.0

        await update.message.reply_text(
            f"🎉 خلصت الاختبار!\n\n"
            f"✅ صحيحة: {correct}\n"
            f"❌ خاطئة: {wrong}\n"
            f"📊 الدرجة: {score}%",
            reply_markup=restart_kb
        )
        return

    q = QUESTIONS[q_index]
    text = f"❓ السؤال {q_index+1}/{total_q}\n\n{q['question']}\n\n"
    for i, choice in enumerate(q["choices"], start=1):
        text += f"{i}. {choice}\n"

    await update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    reset_user(user_id)
    await update.message.reply_text("🚀 أهلاً! ابدأ الاختبار الآن. أجب برقم (1–4).")
    await send_question(update, context, 0, user_id)

# /quiz
async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    reset_user(user_id)
    await send_question(update, context, 0, user_id)

# /score
async def score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_progress:
        await update.message.reply_text("ℹ️ اكتب /quiz للبدء ثم استخدم /score لعرض نتيجتك.")
        return
    prog = user_progress[user_id]
    idx = prog["index"]
    correct = prog["correct"]
    wrong = prog["wrong"]
    total = correct + wrong
    pct = round((correct / total) * 100, 2) if total > 0 else 0.0
    await update.message.reply_text(
        f"📊 نتيجتك الحالية:\n"
        f"السؤال الحالي: {min(idx+1, len(QUESTIONS))}/{len(QUESTIONS)}\n"
        f"✅ صحيحة: {correct}\n"
        f"❌ خاطئة: {wrong}\n"
        f"📈 النسبة: {pct}%"
    )

# استقبال الإجابات
async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = (update.message.text or "").strip()

    if text == RESTART_TEXT:
        reset_user(user_id)
        await update.message.reply_text("🔁 بدأنا من جديد! بالتوفيق 🤍", reply_markup=ReplyKeyboardRemove())
        await send_question(update, context, 0, user_id)
        return

    if user_id not in user_progress:
        await update.message.reply_text("💡 اكتب /quiz للبدء.")
        return

    q_index = user_progress[user_id]["index"]
    if q_index >= len(QUESTIONS):
        await update.message.reply_text("✅ الاختبار انتهى. اضغط الزر لإعادته.", reply_markup=restart_kb)
        return

    q = QUESTIONS[q_index]

    if not text.isdigit():
        await update.message.reply_text("⚠️ اكتب رقم الاختيار (1، 2، 3، 4).")
        return

    choice_num = int(text) - 1
    if choice_num < 0 or choice_num > 3:
        await update.message.reply_text("⚠️ الاختيارات من 1 إلى 4 فقط.")
        return

    if choice_num == q["answer_index"]:
        user_progress[user_id]["correct"] += 1
        await update.message.reply_text(f"✅ إجابة صحيحة!\n{q.get('explanation','')}".strip())
    else:
        user_progress[user_id]["wrong"] += 1
        correct_choice = q["choices"][q["answer_index"]]
        explanation = q.get("explanation", "")
        await update.message.reply_text(
            f"❌ خطأ.\n"
            f"الصحيح: {correct_choice}\n"
            f"{explanation}".strip()
        )

    user_progress[user_id]["index"] = q_index + 1
    await send_question(update, context, user_progress[user_id]["index"], user_id)

# ربط الأوامر
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("quiz", quiz))
application.add_handler(CommandHandler("score", score))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer))

# Webhook
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return "ok"

@app.route("/", methods=["GET"])
def home():
    return "✅ البوت شغال!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
