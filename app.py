import os
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext

# إعداد اللوقز عشان نعرف الأخطاء
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# نجيب التوكن من البيئة
TOKEN = os.getenv("BOT_TOKEN", "ضع_التوكن_حقك_هنا")
bot = Bot(token=TOKEN)

# تطبيق Flask
app = Flask(__name__)

# دالة البداية
def start(update: Update, context: CallbackContext):
    update.message.reply_text("👋 أهلاً بك في بوت القدرات - qiyas_q_bot")

# دالة استقبال أي رسالة
def echo(update: Update, context: CallbackContext):
    update.message.reply_text(f"📌 رسالتك: {update.message.text}")

# إعداد Dispatcher
dispatcher = Dispatcher(bot, None, workers=0)
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

# Webhook endpoint
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

# الصفحة الرئيسية
@app.route("/")
def index():
    return "🤖 Qiyas Bot is running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
