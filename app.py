import os
import json
from flask import Flask, request
from telegram import Bot, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext

# تهيئة البوت
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TOKEN)

app = Flask(__name__)

# Dispatcher لمعالجة التحديثات
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

# تحميل بنك الأسئلة
QUESTIONS_FILE = "data.json"
if os.path.exists(QUESTIONS_FILE):
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)
else:
    questions = []

# أوامر البوت
def start(update: Update, context: CallbackContext):
    update.message.reply_text("👋 أهلاً بك في بوت قياس! اكتب 'سؤال' لأعطيك سؤال.")

def get_question(update: Update, context: CallbackContext):
    if not questions:
        update.message.reply_text("❌ لا توجد أسئلة حالياً في البنك.")
        return
    import random
    q = random.choice(questions)
    question_text = q["question"]
    choices = "\n".join([f"- {c}" for c in q.get("choices", [])])
    update.message.reply_text(f"📖 {question_text}\n\n{choices}")

# ربط الأوامر
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, get_question))

# Webhook
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/")
def home():
    return "بوت قياس شغال ✅"

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=PORT)
