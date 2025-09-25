import os
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# إنشاء كائن Flask
flask_app = Flask(__name__)

# مسار صحي لـ Render
@flask_app.route("/")
def health():
    return "OK", 200

# توكن البوت
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("❌ لم يتم العثور على TELEGRAM_BOT_TOKEN في المتغيرات")

# إنشاء تطبيق تيليجرام
application = Application.builder().token(BOT_TOKEN).build()

# ---------- أوامر بسيطة ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🤖 جرّب الذكاء الاصطناعي", callback_data="ai")],
        [InlineKeyboardButton("📚 جدول الضرب", callback_data="mult")],
    ]
    await update.message.reply_text("👋 مرحباً! اختر من القائمة:", 
                                    reply_markup=InlineKeyboardMarkup(kb))

async def menu_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("✍️ اكتب سؤالك للذكاء الاصطناعي:")

async def menu_mult(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("📌 أرسل رقمًا (مثال: 7) وسأعرض لك جدول ضربه 1..12")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()
    if txt.isdigit():
        n = int(txt)
        table = "\n".join([f"{i} × {n} = {i*n}" for i in range(1, 13)])
        await update.message.reply_text("📚 جدول الضرب:\n" + table)
    else:
        await update.message.reply_text("🤖 حالياً ميزة الذكاء الاصطناعي تجريبية.")

# ---------- ربط الهاندلرز ----------
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(menu_ai, pattern="^ai$"))
application.add_handler(CallbackQueryHandler(menu_mult, pattern="^mult$"))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))


# ---------- تشغيل البوت مع Render ----------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=f"{os.getenv('RENDER_EXTERNAL_URL')}/{BOT_TOKEN}"
    )
