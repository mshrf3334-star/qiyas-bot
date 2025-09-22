import os
import json
import logging
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext

# إعداد اللوجات
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=0)

# تحميل بنك الأسئلة
with open("data.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

# تقدم المستخدمين: user_id → {index, correct, wrong}
user_progress = {}

def send_question(update: Update, context: CallbackContext, q_index: int, user_id: int):
    if q_index >= len(QUESTIONS):
        correct = user_progress[user_id]["correct"]
        wrong = user_progress[user_id]["wrong"]
        total = correct + wrong
        score = round((correct / total) * 100, 2) if total > 0 else 0
        update.message.reply_text(
            f"🎉 خلصت الاختبار!\n\n"
            f"✅ صحيحة: {correct}\n"
            f"❌ خاطئة: {wrong}\n"
            f"📊 الدرجة: {score}%"
        )
        return

    q = QUESTIONS[q_index]
    text = f"❓ السؤال {q_index+1}/{len(QUESTIONS)}\n\n{q['question']}\n\n"
    for i, choice in enumerate(q["choices"], start=1):
        text += f"{i}. {choice}\n"
    update.message.reply_text(text)

def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_progress[user_id] = {"index": 0, "correct": 0, "wrong": 0}
    update.message.reply_text("🚀 أهلاً! ابدأ الاختبار الآن.")
    send_question(update, context, 0, user_id)

def quiz(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_progress[user_id] = {"index": 0, "correct": 0, "wrong": 0}
    send_question(update, context, 0, user_id)

def answer(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in user_progress:
        update.message.reply_text("💡 اكتب /quiz للبدء.")
        return

    q_index = user_progress[user_id]["index"]
    if q_index >= len(QUESTIONS):
        update.message.reply_text("✅ الاختبار خلص.")
        return

    q = QUESTIONS[q_index]
    msg = update.message.text.strip()

    if not msg.isdigit():
        update.message.reply_text("⚠️ اكتب رقم الاختيار (1، 2، 3، 4).")
        return

    choice_num = int(msg) - 1
    if choice_num == q["answer_index"]:
        update.message.reply_text("✅ إجابة صحيحة!\n" + q["explanation"])
        user_progress[user_id]["correct"] += 1
    else:
        correct_choice = q["choices"][q["answer_index"]]
        update.message.reply_text(f"❌ خطأ.\nالصحيح: {correct_choice}\n{q['explanation']}")
        user_progress[user_id]["wrong"] += 1

    # الانتقال للسؤال التالي
    user_progress[user_id]["index"] = q_index + 1
    send_question(update, context, user_progress[user_id]["index"], user_id)

# ربط الأوامر
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("quiz", quiz))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, answer))

# Webhook
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/", methods=["GET"])
def home():
    return "✅ البوت شغال!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
