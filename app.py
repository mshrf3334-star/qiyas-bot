# app.py — Telegram Bot (Webhook only on Render)
import os
import logging

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

# وحدات الميزات
from multiplication import (
    multiplication_table_handler,
    generate_multiplication_table,
    ASK_FOR_NUMBER,
)
from cognitive_questions import (
    start_cognitive_quiz,
    handle_answer,
    SELECTING_ANSWER,
)
from intelligence_questions import (
    start_intelligence_quiz,
    handle_intelligence_answer,
    SELECTING_INTELLIGENCE_ANSWER,
)
from ask_qiyas_ai import ask_qiyas_ai_handler

# ========= الإعدادات =========
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = int(os.getenv("PORT", "10000"))

# Render يوفّر هذا المتغير تلقائياً؛ ويمكنك أيضاً ضبط WEBHOOK_URL يدوياً إن أردت
BASE_URL = (os.getenv("WEBHOOK_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").rstrip("/")

if not BOT_TOKEN:
    raise RuntimeError("❌ TELEGRAM_BOT_TOKEN غير مضبوط.")
if not BASE_URL:
    raise RuntimeError("❌ لم يتم تحديد رابط الويب هوك. اضبط WEBHOOK_URL أو اعتمد على RENDER_EXTERNAL_URL.")

# ========= تسجيل =========
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("bot")

# ========= واجهة المستخدم =========
BTN_MULT = "جدول الضرب"
BTN_COG  = "اختبر قدراتك (500 سؤال)"
BTN_AI   = "اسأل قياس (ذكاء اصطناعي)"
BTN_IQ   = "أسئلة الذكاء (300 سؤال)"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [KeyboardButton(BTN_MULT)],
        [KeyboardButton(BTN_COG)],
        [KeyboardButton(BTN_AI)],
        [KeyboardButton(BTN_IQ)],
    ]
    await update.message.reply_html(
        "مرحباً! اختر من القائمة 👇",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "استخدم الأزرار أو الأوامر:\n"
        "/multiplication /cognitive /intelligence /ask_ai"
    )

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = (update.message.text or "").strip()
    if t == BTN_MULT:
        await multiplication_table_handler(update, context)
    elif t == BTN_COG:
        await start_cognitive_quiz(update, context)
    elif t == BTN_AI:
        await update.message.reply_text("اكتب سؤالك بالأمر: /ask_ai سؤالك هنا")
    elif t == BTN_IQ:
        await start_intelligence_quiz(update, context)
    else:
        await update.message.reply_text("اختر من القائمة.")

# ========= بناء التطبيق والهاندلرز =========
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
        name="multiplication_conv",
        persistent=False,
    ))

    # القدرات المعرفية
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("cognitive", start_cognitive_quiz)],
        states={SELECTING_ANSWER: [MessageHandler(filters.TEXT | filters.CallbackQueryFilter(), handle_answer)]},
        fallbacks=[CommandHandler("start", start)],
        name="cognitive_conv",
        persistent=False,
    ))

    # الذكاء (ألغاز)
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("intelligence", start_intelligence_quiz)],
        states={SELECTING_INTELLIGENCE_ANSWER: [MessageHandler(filters.TEXT | filters.CallbackQueryFilter(), handle_intelligence_answer)]},
        fallbacks=[CommandHandler("start", start)],
        name="intelligence_conv",
        persistent=False,
    ))

    # اسأل قياس (ذكاء اصطناعي)
    app.add_handler(CommandHandler("ask_ai", ask_qiyas_ai_handler))

    # أزرار القائمة النصية
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu))

    return app

# ========= التشغيل بالويب هوك فقط =========
def main():
    app = build_app()

    public_webhook = f"{BASE_URL}/{BOT_TOKEN}"
    logger.info("Starting webhook on %s (port %s)", public_webhook, PORT)

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,                 # مسار سري
        webhook_url=public_webhook,         # العنوان الخارجي
        drop_pending_updates=True,
    )

if __name__ == "__main__":
    main()
