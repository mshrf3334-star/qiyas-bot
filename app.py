import os
import json
import random
import requests
from flask import Flask, request
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# ======================
# إعداد المتغيرات
# ======================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")

# Flask app
app = Flask(__name__)

# ======================
# ذكاء اصطناعي OpenAI
# ======================
def ask_ai(question: str) -> str:
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": AI_MODEL,
            "messages": [{"role": "user", "content": question}],
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"⚠️ خطأ في الاتصال بالذكاء الاصطناعي: {e}"

# ======================
# بوت تيليجرام
# ======================
async def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("📒 جدول الضرب", callback_data="table")],
        [InlineKeyboardButton("🤖 الذكاء الاصطناعي", callback_data="ai")],
        [InlineKeyboardButton("📝 قياس: اختبر نفسك", callback_data="test")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("مرحباً! 👋 اختر خدمة:", reply_markup=reply_markup)

# جدول الضرب
async def multiplication(update: Update, context):
    q = random.randint(1, 9)
    w = random.randint(1, 9)
    correct = q * w
    options = [correct, correct+1, correct-1, correct+2]
    random.shuffle(options)

    keyboard = [[InlineKeyboardButton(str(opt), callback_data=f"ans:{opt}:{correct}")] for opt in options]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(f"📒 كم حاصل {q} × {w} ؟", reply_markup=reply_markup)

# اختبار قياس
async def qiyas_test(update: Update, context):
    q = "2 + 2 = ؟"
    options = [3, 4, 5]
    keyboard = [[InlineKeyboardButton(str(opt), callback_data=f"ans:{opt}:4")] for opt in options]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(f"📝 سؤال: {q}", reply_markup=reply_markup)

# ذكاء اصطناعي
async def ai_chat(update: Update, context):
    await update.callback_query.message.reply_text("🤖 أرسل سؤالك للذكاء الاصطناعي:")

# الردود على الأزرار
async def button(update: Update, context):
    query = update.callback_query
    await query.answer()

    if query.data == "table":
        await multiplication(update, context)
    elif query.data == "test":
        await qiyas_test(update, context)
    elif query.data == "ai":
        await ai_chat(update, context)
    elif query.data.startswith("ans:"):
        chosen, correct = query.data.split(":")[1:]
        if chosen == correct:
            await query.message.reply_text("✅ إجابة صحيحة!")
        else:
            await query.message.reply_text("❌ إجابة خاطئة، حاول مرة أخرى.")

# ذكاء اصطناعي عبر الرسائل
async def handle_message(update: Update, context):
    if update.message.text:
        reply = ask_ai(update.message.text)
        await update.message.reply_text(reply)

# ======================
# إعداد Webhook
# ======================
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route("/")
def home():
    return "✅ Bot is running!"

@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "ok"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
