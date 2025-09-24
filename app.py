import os
import json
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import openai

# إعداد اللوج
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# تحميل متغيرات البيئة
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")

openai.api_key = AI_API_KEY

# تحميل الداتا (مثلاً بنك الأسئلة)
DATA_FILE = "data.json"
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        DATA = json.load(f)
else:
    DATA = {"questions": []}

# Flask app
app = Flask(__name__)

@app.route("/")
def home():
    return "🚀 البوت والموقع شغالين يا بطل!"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "ok", 200

# أوامر البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("جدول الضرب", callback_data="multiplication")],
        [InlineKeyboardButton("اختبر نفسك", callback_data="quiz")],
        [InlineKeyboardButton("ذكاء اصطناعي", callback_data="ai")],
    ]
    await update.message.reply_text(
        "مرحباً بك في بوت القياس 🤖 اختر من القائمة:", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "multiplication":
        text = "\n".join([f"{i} × {j} = {i*j}" for i in range(1, 6) for j in range(1, 6)])
        await query.edit_message_text(f"📘 جدول الضرب:\n{text}")

    elif query.data == "quiz":
        if DATA["questions"]:
            q = DATA["questions"][0]
            await query.edit_message_text(f"❓ {q['question']}")
        else:
            await query.edit_message_text("مافي أسئلة في data.json 📂")

    elif query.data == "ai":
        await query.edit_message_text("✍️ أرسل سؤالك وسيجيبك الذكاء الاصطناعي")

async def ai_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    user_text = update.message.text

    try:
        response = openai.ChatCompletion.create(
            model=AI_MODEL,
            messages=[{"role": "user", "content": user_text}],
        )
        answer = response["choices"][0]["message"]["content"]
    except Exception as e:
        answer = f"⚠️ خطأ في الذكاء الاصطناعي: {str(e)}"

    await update.message.reply_text(answer)

# إعداد التطبيق
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_message))

# تشغيل البوت مع Flask
if __name__ != "__main__":
    # على Render
    application.run_polling(stop_signals=None)
