import os
import json
import random
import logging
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, MessageHandler, Filters, CommandHandler
import requests

# إعداد اللوقز
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# جلب المتغيرات من Render
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")

bot = Bot(token=TELEGRAM_BOT_TOKEN)

app = Flask(__name__)

# تحميل بنك الأسئلة من ملف data.json
with open("data.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)


# دالة لاختيار سؤال عشوائي
def get_random_question():
    return random.choice(QUESTIONS)


# دالة للرد من الذكاء الاصطناعي
def ask_ai(prompt: str) -> str:
    try:
        url = "https://api.openai.com/v1/responses"
        headers = {
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {"model": AI_MODEL, "input": prompt}

        response = requests.post(url, headers=headers, json=payload)
        data = response.json()

        if "output" in data:
            return data["output"][0]["content"][0]["text"]
        elif "choices" in data:
            return data["choices"][0]["message"]["content"]
        else:
            return "⚠️ تعذّر الحصول على رد من الذكاء الاصطناعي."
    except Exception as e:
        logging.error(f"AI Error: {e}")
        return "⚠️ خطأ في الاتصال بالذكاء الاصطناعي."


# أوامر البوت
def start(update: Update, context):
    update.message.reply_text("👋 أهلاً! أرسل 'سؤال' للحصول على سؤال عشوائي، أو اكتب أي شيء للتحدث مع الذكاء الاصطناعي.")


def question(update: Update, context):
    q = get_random_question()
    text = f"📘 سؤال:\n{q['question']}\n\nالاختيارات:\n"
    for i, choice in enumerate(q["choices"], 1):
        text += f"{i}. {choice}\n"
    update.message.reply_text(text)


def handle_message(update: Update, context):
    user_text = update.message.text
    if "سؤال" in user_text:
        return question(update, context)
    else:
        ai_reply = ask_ai(user_text)
        update.message.reply_text(ai_reply)


# إعداد الديسباتشر
dispatcher = Dispatcher(bot, None, workers=0)
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))


# Webhook من Render
@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"


@app.route("/")
def home():
    return "✅ Bot is running on Render!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
