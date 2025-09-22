from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, MessageHandler, Filters, CommandHandler
import os

app = Flask(__name__)

# جلب التوكن من متغيرات البيئة
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TOKEN)

# إعداد الديسباتشر
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

# أوامر بسيطة
def start(update, context):
    update.message.reply_text("أهلاً 👋 هذا بوت القدرات Qiyas Bot جاهز!")

def echo(update, context):
    update.message.reply_text(update.message.text)

# إضافة الهاندلرز
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/")
def home():
    return "Qiyas Bot is running ✅"

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=PORT)
