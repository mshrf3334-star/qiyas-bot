import os
import json
import logging
from flask import Flask, request
from telegram import Bot, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext

# إعداد اللوجات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# تحميل التوكن
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN غير معين")
    raise ValueError("TELEGRAM_BOT_TOKEN غير معين")

# تهيئة البوت
try:
    bot = Bot(token=TOKEN)
    dispatcher = Dispatcher(bot, None, workers=0)
    logger.info("✅ تم تهيئة البوت بنجاح")
except Exception as e:
    logger.error(f"❌ خطأ في تهيئة البوت: {e}")
    raise

# تحميل الأسئلة
try:
    with open("data.json", "r", encoding="utf-8") as f:
        QUESTIONS = json.load(f)
    logger.info(f"✅ تم تحميل {len(QUESTIONS)} سؤال")
except Exception as e:
    logger.error(f"❌ خطأ في تحميل data.json: {e}")
    QUESTIONS = []

# متابعة المستخدمين
user_progress = {}

def reset_user(user_id):
    user_progress[user_id] = {"index": 0, "correct": 0, "wrong": 0}

def send_question(update, context, user_id):
    if not QUESTIONS:
        update.message.reply_text("❌ لا توجد أسئلة متاحة")
        return
        
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
        
        update.message.reply_text(
            f"🎉 انتهى الاختبار!\n"
            f"✅ الصحيحة: {correct}\n"
            f"❌ الخاطئة: {wrong}\n"
            f"📊 النسبة: {score}%"
        )
        return
    
    # عرض السؤال
    q = QUESTIONS[q_index]
    text = f"السؤال {q_index + 1}/{len(QUESTIONS)}:\n{q['question']}\n\n"
    for i, choice in enumerate(q["choices"], 1):
        text += f"{i}. {choice}\n"
    
    update.message.reply_text(text)

def start(update, context):
    user_id = update.message.from_user.id
    reset_user(user_id)
    update.message.reply_text("🚀 أهلاً! ابدأ بالإجابة برقم من 1 إلى 4")
    send_question(update, context, user_id)

def handle_message(update, context):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    
    if user_id not in user_progress:
        update.message.reply_text("اكتب /start للبدء")
        return
    
    progress = user_progress[user_id]
    q_index = progress["index"]
    
    if q_index >= len(QUESTIONS):
        update.message.reply_text("انتهى الاختبار. اكتب /start للبدء من جديد")
        return
    
    if not text.isdigit() or not (1 <= int(text) <= 4):
        update.message.reply_text("⚠️ أدخل رقم من 1 إلى 4")
        return
    
    choice_index = int(text) - 1
    current_q = QUESTIONS[q_index]
    
    if choice_index == current_q["answer_index"]:
        progress["correct"] += 1
        update.message.reply_text("✅ صحيح!")
    else:
        progress["wrong"] += 1
        correct_answer = current_q["choices"][current_q["answer_index"]]
        update.message.reply_text(f"❌ خطأ. الإجابة الصحيحة: {correct_answer}")
    
    progress["index"] += 1
    send_question(update, context, user_id)

# تسجيل ال handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        update = Update.de_json(data, bot)
        dispatcher.process_update(update)
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
        bot.set_webhook(webhook_url)
        return f'✅ Webhook set: {webhook_url}'
    except Exception as e:
        return f'❌ Error: {e}'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port)
