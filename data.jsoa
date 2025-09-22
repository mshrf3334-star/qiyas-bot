import os
import json
import logging
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

# إعداد اللوجات
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# المتغيرات من Environment
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "openai/gpt-4o-mini")

bot = Bot(token=TOKEN)

app = Flask(__name__)

# Dispatcher للتعامل مع التحديثات
dispatcher = Dispatcher(bot, None, workers=0)

# أمر /start
def start(update: Update, context):
    update.message.reply_text("🚀 أهلاً! أنا بوت اختبارات القدرات. اسألني أو جرب /quiz")

# أمر /quiz
def quiz(update: Update, context):
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            questions = json.load(f)

        q = questions[0]  # أول سؤال للتجربة
        text = f"❓ {q['question']}\n\n"
        for i, choice in enumerate(q["choices"], start=1):
            text += f"{i}. {choice}\n"
        update.message.reply_text(text)
    except Exception as e:
        update.message.reply_text(f"⚠️ خطأ في تحميل الأسئلة: {e}")

# أي رسالة نصية
def echo(update: Update, context):
    update.message.reply_text("📌 استفسارك استقبلته، وجاري التطوير!")

# ربط الأوامر
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("quiz", quiz))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

# الراوت الأساسي
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

# صفحة رئيسية
@app.route("/", methods=["GET"])
def home():
    return "✅ البوت شغال تمام!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
