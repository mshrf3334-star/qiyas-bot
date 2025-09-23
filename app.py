import os
import json
import logging
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد اللوجات
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable not set")

# إنشاء التطبيق
application = Application.builder().token(TOKEN).build()
app = Flask(__name__)

# تحميل الأسئلة
try:
    with open("data.json", "r", encoding="utf-8") as f:
        QUESTIONS = json.load(f)
    logging.info(f"✅ تم تحميل {len(QUESTIONS)} سؤال")
except Exception as e:
    logging.error(f"❌ خطأ في تحميل data.json: {e}")
    QUESTIONS = []

# متابعة تقدم المستخدمين
user_progress = {}

def reset_user(user_id):
    user_progress[user_id] = {"index": 0, "correct": 0, "wrong": 0}

async def send_question(update, context, user_id):
    if user_id not in user_progress:
        reset_user(user_id)
    
    progress = user_progress[user_id]
    q_index = progress["index"]
    
    if q_index >= len(QUESTIONS):
        # انتهاء الأسئلة
        correct = progress["correct"]
        wrong = progress["wrong"]
        total = correct + wrong
        score = round((correct / total) * 100, 2) if total > 0 else 0
        
        await update.message.reply_text(
            f"🎉 انتهى الاختبار!\n\n"
            f"✅ الإجابات الصحيحة: {correct}\n"
            f"❌ الإجابات الخاطئة: {wrong}\n"
            f"📊 النسبة: {score}%"
        )
        return
    
    # إرسال السؤال الحالي
    question = QUESTIONS[q_index]
    question_text = f"السؤال {q_index + 1}/{len(QUESTIONS)}:\n{question['question']}\n\n"
    
    for i, choice in enumerate(question['choices'], 1):
        question_text += f"{i}. {choice}\n"
    
    await update.message.reply_text(question_text)

async def start(update, context):
    user_id = update.message.from_user.id
    reset_user(user_id)
    await update.message.reply_text("مرحباً! ابدأ الاختبار بالرد بأرقام الإجابات (1-4)")
    await send_question(update, context, user_id)

async def handle_answer(update, context):
    user_id = update.message.from_user.id
    answer_text = update.message.text.strip()
    
    if user_id not in user_progress:
        await update.message.reply_text("اكتب /start للبدء")
        return
    
    progress = user_progress[user_id]
    q_index = progress["index"]
    
    if q_index >= len(QUESTIONS):
        await update.message.reply_text("الاختبار انتهى. اكتب /start للبدء من جديد")
        return
    
    # التحقق من الإجابة
    if not answer_text.isdigit() or not (1 <= int(answer_text) <= 4):
        await update.message.reply_text("⚠️ الرجاء إدخال رقم بين 1 و 4")
        return
    
    user_choice = int(answer_text) - 1
    current_question = QUESTIONS[q_index]
    
    if user_choice == current_question['answer_index']:
        progress["correct"] += 1
        response = "✅ إجابة صحيحة!"
    else:
        progress["wrong"] += 1
        correct_answer = current_question['choices'][current_question['answer_index']]
        response = f"❌ إجابة خاطئة. الإجابة الصحيحة: {correct_answer}"
    
    # التقدم للسؤال التالي
    progress["index"] += 1
    await update.message.reply_text(response)
    await send_question(update, context, user_id)

# إعداد handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))

# Webhook endpoint
@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(), application.bot)
    application.update_queue.put(update)
    return 'ok'

@app.route('/')
def index():
    return '✅ البوت يعمل!'

@app.route('/set_webhook')
def set_webhook():
    webhook_url = f'https://{request.host}/webhook/{TOKEN}'
    application.bot.set_webhook(webhook_url)
    return f'Webhook set to: {webhook_url}'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
