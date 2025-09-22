import os
import json
import logging
from flask import Flask, request
from telegram import Bot, Update, InputFile, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext
import requests

# إعداد اللوج
logging.basicConfig(level=logging.INFO)

# أخذ التوكن والمفاتيح من Environment
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Flask
app = Flask(__name__)

# Dispatcher
dispatcher = Dispatcher(bot, None, workers=0)

# تحميل بنك الأسئلة
QUESTIONS_FILE = "data.json"
if os.path.exists(QUESTIONS_FILE):
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        QUESTIONS = json.load(f)
else:
    QUESTIONS = []

# دالة سؤال الذكاء الاصطناعي
def ask_ai(prompt: str) -> str:
    try:
        r = requests.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {AI_API_KEY}"},
            json={"model": AI_MODEL, "input": prompt},
            timeout=30
        )
        data = r.json()
        return data["output"][0]["content"][0]["text"]
    except Exception as e:
        return f"⚠️ تعذّر الاتصال بالذكاء الاصطناعي: {e}"

# أوامر
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "مرحباً 👋\nهذا بوت قياس.\n"
        "أرسل: 'سؤال' لأخذ سؤال عشوائي من بنك الأسئلة.\n"
        "أو أرسل أي استفسار لأسأله الذكاء الاصطناعي 🤖."
    )

def ask_question(update: Update, context: CallbackContext):
    import random
    if QUESTIONS:
        q = random.choice(QUESTIONS)
        text = f"❓ {q['question']}\n\nالخيارات:\n"
        for i, c in enumerate(q["choices"], start=1):
            text += f"{i}. {c}\n"
        update.message.reply_text(text)
    else:
        update.message.reply_text("⚠️ لا يوجد أسئلة حالياً في البنك.")

def handle_message(update: Update, context: CallbackContext):
    text = update.message.text
    if text.strip() == "سؤال":
        ask_question(update, context)
    else:
        reply = ask_ai(text)
        update.message.reply_text(reply)

# ربط الهاندلرز
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# Webhook route
@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/")
def index():
    return "✅ Bot is running!"

# تشغيل السيرفر
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
