# app.py — Webhook only (Render-ready)
import os
import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

# وحدات الميزات
from multiplication import multiplication_table_handler, generate_multiplication_table
from cognitive_questions import start_cognitive_quiz, handle_answer, SELECTING_ANSWER
from intelligence_questions import (
    start_intelligence_quiz, handle_intelligence_answer, SELECTING_INTELLIGENCE_ANSWER
)
from ask_qiyas_ai import ask_qiyas_ai_handler

# ========= الإعدادات =========
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get("PORT", "10000"))

# نأخذ الرابط العام تلقائياً من Render إن وُجد، أو من متغير اختياري WEBHOOK_URL
PUBLIC_URL = (os.environ.get("RENDER_EXTERNAL_URL")
              or os.environ.get("WEBHOOK_URL")
              or "").rstrip("/")

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN مفقود في Environment Variables")

# ========= لوجينغ =========
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# حالة محادثة جدول الضرب
ASK_FOR_NUMBER = 0

# ========= الهاندلرز =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [KeyboardButton("جدول الضرب")],
        [KeyboardButton("اختبر قدراتك (500 سؤال)")],
        [KeyboardButton("اسأل قياس (ذكاء اصطناعي)")],
        [KeyboardButton("أسئلة الذكاء (300 سؤال)")],
    ]
    await update.message.reply_html(
        "مرحباً! اختر من القائمة 👇",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "استخدم الأزرار أو الأوامر: /multiplication /cognitive /intelligence /ask_ai"
    )

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = (update.message.text or "").strip()
    if t == "جدول الضرب":
        await multiplication_table_handler(update, context)
    elif t == "اختبر قدراتك (500 سؤال)":
        await start_cognitive_quiz(update, context)
    elif t == "اسأل قياس (ذكاء اصطناعي)":
        await update.message.reply_text("اكتب سؤالك بالأمر: /ask_ai سؤالك هنا")
    elif t == "أسئلة الذكاء (300 سؤال)":
        await start_intelligence_quiz(update, context)
    else:
        await update.message.reply_text("اختر من القائمة.")

def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()

    # أوامر عامة
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))

    # جدول الضرب
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("multiplication", multiplication_table_handler)],
        states={ASK_FOR_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_multiplication_table)]},
        fallbacks=[CommandHandler("start", start)],
    ))

    # القدرات المعرفية
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("cognitive", start_cognitive_quiz)],
        states={SELECTING_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]},
        fallbacks=[CommandHandler("start", start)],
    ))

    # الذكاء
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("intelligence", start_intelligence_quiz)],
        states={SELECTING_INTELLIGENCE_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_intelligence_answer)]},
        fallbacks=[CommandHandler("start", start)],
    ))

    # اسأل قياس (ذكاء اصطناعي)
    app.add_handler(CommandHandler("ask_ai", ask_qiyas_ai_handler))

    # أزرار القائمة
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu))

    return app

def main():
    app = build_app()

    # نجهز بارامترات تشغيل السيرفر
    webhook_kwargs = dict(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,              # المسار السري
        drop_pending_updates=True,
    )

    # إذا عرفنا الرابط العام، نضبط الويبهوك تلقائياً
    if PUBLIC_URL:
        webhook_url = f"{PUBLIC_URL}/{BOT_TOKEN}"
        webhook_kwargs["webhook_url"] = webhook_url
        logger.info("Starting Webhook at %s", webhook_url)
    else:
        # لو ما فيه رابط عام، نشغّل السيرفر فقط (مفيد إذا سبق وضبطت الويبهوك يدوياً)
        logger.info("Starting Webhook server without setting webhook_url (PUBLIC_URL missing)")

    app.run_webhook(**webhook_kwargs)

if __name__ == "__main__":
    main()
