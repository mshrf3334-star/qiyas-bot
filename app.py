import os
from flask import Flask, request
import telegram

app = Flask(__name__)

# التوكن لازم يكون موجود في متغير بيئة TELEGRAM_BOT_TOKEN
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("⚠️ ضع TELEGRAM_BOT_TOKEN في Environment Variables في Render")

bot = telegram.Bot(token=TOKEN)

# المسار الأساسي (للاختبار/Health Check)
@app.route("/", methods=["GET"])
def home():
    return "البوت شغال ✅", 200

# مسار الويبهوك (ثابت /webhook)
@app.route("/webhook", methods=["POST"])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)

    # هنا منطق التعامل مع الرسائل
    chat_id = update.effective_chat.id
    text = update.message.text if update.message else ""

    if text == "/start":
        bot.send_message(chat_id=chat_id, text="🚀 أهلاً بك! البوت شغال ✅")
    else:
        bot.send_message(chat_id=chat_id, text=f"📩 استلمت: {text}")

    return "ok", 200
