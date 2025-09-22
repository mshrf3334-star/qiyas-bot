import os
import json
from flask import Flask, request
from telegram import Bot, Update, ReplyKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

# قراءة المتغيرات من Render
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
AI_API_KEY = os.environ.get("AI_API_KEY")
AI_MODEL = os.environ.get("AI_MODEL", "openai/gpt-4o-mini")

bot = Bot(token=TOKEN)

# Flask app
app = Flask(__name__)

# Dispatcher لتيليجرام
dispatcher = Dispatcher(bot, None, workers=0)

# تحميل بنك الأسئلة
with open("data.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

# متغير لتتبع حالة المستخدم
user_state = {}

# دالة البدء
def start(update: Update, context):
    update.message.reply_text(
        "👋 أهلاً بك في بوت القدرات.\n"
        "أرسل أي رسالة للبدء بالأسئلة."
    )

# دالة إرسال سؤال
def send_question(update: Update, context):
    chat_id = update.message.chat_id
    state = user_state.get(chat_id, {"index": 0, "score": 0})

    if state["index"] < len(QUESTIONS):
        q = QUESTIONS[state["index"]]
        question_text = f"س{q['id']}: {q['question']}"
        choices = q["choices"]

        keyboard = [[c] for c in choices]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

        update.message.reply_text(question_text, reply_markup=reply_markup)
        user_state[chat_id] = state
    else:
        score = state["score"]
        update.message.reply_text(f"✅ انتهيت! درجتك: {score}/{len(QUESTIONS)}")
        user_state[chat_id] = {"index": 0, "score": 0}

# دالة استلام الإجابات
def handle_answer(update: Update, context):
    chat_id = update.message.chat_id
    state = user_state.get(chat_id, {"index": 0, "score": 0})

    if state["index"] < len(QUESTIONS):
        q = QUESTIONS[state["index"]]
        answer = update.message.text.strip()

        if answer == q["answer_index"]:
            state["score"] += 1
            update.message.reply_text("👍 إجابة صحيحة!")
        else:
            update.message.reply_text(
                f"❌ خطأ. الإجابة الصحيحة: {q['answer_index']}"
            )

        state["index"] += 1
        user_state[chat_id] = state
        send_question(update, context)
    else:
        update.message.reply_text("🔄 أرسل /start للبدء من جديد.")

# ربط الأوامر بالـ Dispatcher
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_answer))

# Webhook endpoint
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

# للتجربة محلياً
@app.route("/")
def home():
    return "بوت القدرات شغال ✅"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
