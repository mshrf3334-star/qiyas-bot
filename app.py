import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler

# إنشاء تطبيق Flask
app = Flask(__name__)

# قراءة التوكن من متغير البيئة
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TOKEN)

# إنشاء Dispatcher
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

# دالة أمر /start
def start(update, context):
    update.message.reply_text("🚀 البوت شغال تمام!")

# إضافة الأمر للديسباتشر
dispatcher.add_handler(CommandHandler("start", start))

# راوت رئيسي للتجربة
@app.route('/')
def index():
    return "✅ البوت يعمل على Render!"

# راوت خاص بالويب هوك
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

# تشغيل التطبيق
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
