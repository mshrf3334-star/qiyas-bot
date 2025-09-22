import os
import imghdr
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
from telegram.ext import CallbackContext

# قراءة التوكن من المتغيرات
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TOKEN)

# إنشاء التطبيق Flask
app = Flask(__name__)

# أوامر البوت
def start(update: Update, context: CallbackContext):
    update.message.reply_text("أهلاً بك 👋 هذا بوت القدرات")

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text("أرسل لي أي سؤال أو صورة 🚀")

def handle_message(update: Update, context: CallbackContext):
    text = update.message.text
    update.message.reply_text(f"أنت كتبت: {text}")

def handle_photo(update: Update, context: CallbackContext):
    file = update.message.photo[-1].get_file()
    file_path = f"photo_{update.message.chat_id}.jpg"
    file.download(file_path)

    # التأكد من أن الملف صورة باستخدام imghdr
    if imghdr.what(file_path):
        update.message.reply_text("📷 وصلت الصورة وتم حفظها ✅")
    else:
        update.message.reply_text("❌ الملف ليس صورة صالحة")

# إعداد Dispatcher
from telegram.ext import Dispatcher
dispatcher = Dispatcher(bot, None, workers=0)
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_command))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
dispatcher.add_handler(MessageHandler(Filters.photo, handle_photo))

# Webhook
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/")
def home():
    return "Bot is running ✅"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
