import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
import logging
import requests

# إعدادات البوت
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")

bot = Bot(token=TOKEN)

app = Flask(__name__)

# تفعيل اللوغ
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    level=logging.INFO)

# ديسباتشر للتعامل مع التحديثات
dispatcher = Dispatcher(bot, None, workers=0)

# أوامر البوت
def start(update: Update, context):
    update.message.reply_text("أهلاً 👋 معك بوت Qiyas جاهز يساعدك.")

def echo(update: Update, context):
    user_text = update.message.text

    # نرسل النص للذكاء الاصطناعي
    headers = {"Authorization": f"Bearer {AI_API_KEY}"}
    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": "أنت مساعد ذكي للقدرات"},
            {"role": "user", "content": user_text}
        ]
    }

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        result = response.json()
        ai_reply = result["choices"][0]["message"]["content"]
        update.message.reply_text(ai_reply)
    except Exception as e:
        update.message.reply_text("⚠️ صار خطأ، جرّب مرة ثانية")

# ربط الأوامر
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/")
def index():
    return "🤖 البوت شغال!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
