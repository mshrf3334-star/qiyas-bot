import os
import imghdr   # ✅ هذا الاستيراد الصحيح
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
import logging

# تفعيل اللوجات عشان لو فيه خطأ يبان في Render
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

app = Flask(__name__)

# المتغيرات من Render
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")

bot = Bot(token=TOKEN)

# تعريف ديسباتشر
from telegram.ext import Dispatcher
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

# أوامر البوت
def start(update, context):
    update.message.reply_text("🚀 أهلاً بك في بوت قياس! جرب تكتب أي رسالة.")

def echo(update, context):
    user_text = update.message.text
    update.message.reply_text(f"📩 رسالتك: {user_text}")

# إضافة الهاندلرز
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

# Webhook للتيليجرام
@app.route(f"/{TOKEN}", methods=["POST"])
def respond():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/")
def index():
    return "🤖 البوت شغال على Render بنجاح!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
