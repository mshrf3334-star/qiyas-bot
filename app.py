# app.py
import os
import json
import random
from flask import Flask, request, jsonify

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, Dispatcher

# ========= الإعدادات =========
TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("ضع متغير البيئة BOT_TOKEN في إعدادات Render.")

# تحميل بنك الأسئلة من data.json (تأكد أن الملف JSON سليم ومغلق بالأقواس)
with open("data.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

# حالة مؤقتة للمستخدمين بالذاكرة
STATE = {}  # user_id -> {"qid":int, "answer_index":int}

# بوت وتوزيع
bot = Bot(token=TOKEN)
updater = Updater(token=TOKEN, use_context=True)
dispatcher: Dispatcher = updater.dispatcher

# ========= دوال البوت =========
def pick_question() -> dict:
    """يرجع سؤال عشوائي من القائمة."""
    return random.choice(QUESTIONS)

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "أهلًا 👋 أنا بوت قياس.\nأرسل /quiz لبدء سؤال عشوائي، أو /help للمساعدة."
    )

def help_cmd(update: Update, context: CallbackContext):
    update.message.reply_text(
        "الأوامر:\n/quiz سؤال عشوائي\n/stop لإلغاء السؤال الحالي"
    )

def stop_cmd(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    STATE.pop(uid, None)
    update.message.reply_text("تم إلغاء السؤال الحالي.", reply_markup=ReplyKeyboardRemove())

def quiz(update: Update, context: CallbackContext):
    q = pick_question()
    uid = update.effective_user.id
    STATE[uid] = {"qid": q.get("id"), "answer_index": q.get("answer_index", 0)}

    # لوحة خيارات
    choices = q.get("choices", [])
    keyboard = [[c] for c in choices]
    kb = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    update.message.reply_text(f"سؤال #{q.get('id')}:\n{q.get('question')}", reply_markup=kb)

def on_text(update: Update, context: CallbackContext):
    """استقبال إجابة المستخدم على السؤال الحالي."""
    if not update.message:
        return

    uid = update.effective_user.id
    if uid not in STATE:
        # بدون حالة -> اعرض مساعدة بسيطة
        if update.message.text.strip().startswith("/"):
            return  # أوامر تُعالَج handlers أخرى
        update.message.reply_text("أرسل /quiz لبدء سؤال جديد.")
        return

    # لدينا سؤال جارٍ
    user_ans = update.message.text.strip()
    # ابحث السؤال من الذاكرة (أبسط شكل: استرجاعه من القائمة)
    current = STATE[uid]
    qid = current["qid"]

    q = next((x for x in QUESTIONS if x.get("id") == qid), None)
    if not q:
        update.message.reply_text("السؤال غير موجود، أرسل /quiz للمحاولة مجددًا.", reply_markup=ReplyKeyboardRemove())
        STATE.pop(uid, None)
        return

    correct_idx = int(q.get("answer_index", 0))
    choices = q.get("choices", [])
    correct_val = choices[correct_idx] if 0 <= correct_idx < len(choices) else None

    if correct_val is not None and user_ans == str(correct_val):
        update.message.reply_text("✔️ إجابة صحيحة! 🎉", reply_markup=ReplyKeyboardRemove())
    else:
        exp = q.get("explanation", "")
        update.message.reply_text(f"✖️ إجابة غير صحيحة.\nالصحيح: {correct_val}\nالشرح: {exp}", reply_markup=ReplyKeyboardRemove())

    # نظّف الحالة واطلب سؤالًا جديدًا سريعًا
    STATE.pop(uid, None)
    update.message.reply_text("أرسل /quiz لسؤال آخر.")

# ربط الهاندلرز
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_cmd))
dispatcher.add_handler(CommandHandler("stop", stop_cmd))
dispatcher.add_handler(CommandHandler("quiz", quiz))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, on_text))

# ========= تطبيق Flask ومسارات الويبهوك =========
app = Flask(__name__)

@app.get("/")
def health():
    return "OK", 200

# ويبهـوك رئيسي على جذر الموقع (لو تبي مسار مخصص غيّر السطر تحت)
@app.post("/")
def telegram_webhook_root():
    update = Update.de_json(request.get_json(force=True, silent=True) or {}, bot)
    dispatcher.process_update(update)
    return jsonify(ok=True)

# مسار بديل باسم التوكن (تقدر تستخدمه للـ setWebhook)
@app.post(f"/webhook/{TOKEN}")
def telegram_webhook_token():
    update = Update.de_json(request.get_json(force=True, silent=True) or {}, bot)
    dispatcher.process_update(update)
    return jsonify(ok=True)

# مساعدة لتثبيت الويبهوك من المتصفح: /setwebhook?url=https://example.onrender.com/webhook/<TOKEN>
@app.get("/setwebhook")
def set_webhook():
    url = request.args.get("url")
    if not url:
        # حاول أخذ عنوان Render تلقائيًا
        base = os.getenv("RENDER_EXTERNAL_URL")
        if base:
            url = f"{base}/webhook/{TOKEN}"
    if not url:
        return "مرّر باراميتر ?url=...", 400
    ok = bot.set_webhook(url)
    return jsonify(ok=ok, url=url)

if __name__ == "__main__":
    # للتشغيل المحلي فقط (Render يستخدم gunicorn)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
