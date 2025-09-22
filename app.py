import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

# إعداد المتغيرات من البيئة (Environment Variables)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TELEGRAM_BOT_TOKEN)

app = Flask(__name__)

# أوامر البوت
def start(update, context):
    update.message.reply_text("أهلاً بك 👋 هذا بوت اختبارات القدرات.")

def help_command(update, context):
    update.message.reply_text("استخدم /start للبدء، أو أرسل أي سؤال للتجربة.")

def echo(update, context):
    update.message.reply_text(f"سؤالك: {update.message.text}")

# ربط Dispatcher
from telegram.ext import CallbackContext
dispatcher = Dispatcher(bot, None, workers=0)

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_command))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

# Webhook
@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/")
def home():
    return "Qiyas Bot is running ✅"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
