import os
import json
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد اللوجات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN not set")

application = Application.builder().token(TOKEN).build()
app = Flask(__name__)

# تحميل الأسئلة
try:
    with open("data.json", "r", encoding="utf-8") as f:
        QUESTIONS = json.load(f)
    logger.info(f"Loaded {len(QUESTIONS)} questions")
except Exception as e:
    logger.error(f"Error loading data.json: {e}")
    QUESTIONS = []

user_progress = {}

def reset_user(user_id):
    user_progress[user_id] = {"index": 0, "correct": 0, "wrong": 0}

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    if not QUESTIONS:
        await update.message.reply_text("❌ لا توجد أسئلة متاحة")
        return

    progress = user_progress.get(user_id, {"index": 0, "correct": 0, "wrong": 0})
    q_index = progress["index"]
    
    if q_index >= len(QUESTIONS):
        correct = progress["correct"]
        wrong = progress["wrong"]
        total = correct + wrong
        score = round((correct / total) * 100, 2) if total > 0 else 0
        
        await update.message.reply_text(
            f"🎉 انتهى الاختبار!\n"
            f"✅ الصحيحة: {correct}\n"
            f"❌ الخاطئة: {wrong}\n"
            f"📊 النسبة: {score}%"
        )
        return

    q = QUESTIONS[q_index]
    text = f"السؤال {q_index + 1}/{len(QUESTIONS)}:\n{q['question']}\n\n"
    for i, choice in enumerate(q["choices"], 1):
        text += f"{i}. {choice}\n"
    
    await update.message.reply_text(text)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    reset_user(user_id)
    await update.message.reply_text("🚀 أهلاً! ابدأ بالإجابة برقم من 1 إلى 4")
    await send_question(update, context, user_id)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    
    if user_id not in user_progress:
        await update.message.reply_text("اكتب /start للبدء")
        return
    
    progress = user_progress[user_id]
    q_index = progress["index"]
    
    if q_index >= len(QUESTIONS):
        await update.message.reply_text("انتهى الاختبار. اكتب /start للبدء من جديد")
        return
    
    if not text.isdigit() or not (1 <= int(text) <= 4):
        await update.message.reply_text("⚠️ أدخل رقم من 1 إلى 4")
        return
    
    choice_index = int(text) - 1
    current_q = QUESTIONS[q_index]
    
    if choice_index == current_q["answer_index"]:
        progress["correct"] += 1
        await update.message.reply_text("✅ صحيح!")
    else:
        progress["wrong"] += 1
        correct_answer = current_q["choices"][current_q["answer_index"]]
        await update.message.reply_text(f"❌ خطأ. الإجابة الصحيحة: {correct_answer}")
    
    progress["index"] += 1
    await send_question(update, context, user_id)

# تسجيل ال handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        update = Update.de_json(data, application.bot)
        application.update_queue.put(update)
        return 'ok'
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'error', 500

@app.route('/')
def home():
    return '✅ البوت شغال!'

@app.route('/set_webhook')
def set_webhook():
    try:
        webhook_url = f'https://{request.host}/webhook/{TOKEN}'
        application.bot.set_webhook(webhook_url)
        return f'✅ Webhook set: {webhook_url}'
    except Exception as e:
        return f'❌ Error: {e}'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
