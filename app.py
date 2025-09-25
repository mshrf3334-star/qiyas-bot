import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

# ====== إعدادات عامة ======
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====== متغيرات البيئة ======
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("BOT_TOKEN")
AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_MODEL = os.environ.get("AI_MODEL", "gpt-4o-mini")
PORT = int(os.environ.get("PORT", "10000"))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "").strip().rstrip("/")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN غير موجود في Environment Variables")

# ====== استيراد الوحدات التابعة (مع إصلاح اسم ملف الضرب) ======
# يحاول أولاً 'multiplication.py' ثم 'mutiplication.py'
try:
    from multiplication import multiplication_table_handler, generate_multiplication_table
except ModuleNotFoundError:
    from mutiplication import multiplication_table_handler, generate_multiplication_table  # type: ignore

from cognitive_questions import start_cognitive_quiz, handle_answer, SELECTING_ANSWER
from intelligence_questions import (
    start_intelligence_quiz,
    handle_intelligence_answer,
    SELECTING_INTELLIGENCE_ANSWER
)
from ask_qiyas_ai import ask_qiyas_ai_handler  # هذه الدالة تقرأ مفاتيحها من env أيضاً

# ====== ثوابت المحادثة ======
ASK_FOR_NUMBER = 0

# ====== واجهة البداية ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    keyboard = [
        [KeyboardButton("جدول الضرب")],
        [KeyboardButton("اختبر قدراتك (500 سؤال)")],
        [KeyboardButton("اسأل قياس (ذكاء اصطناعي)")],
        [KeyboardButton("أسئلة الذكاء (300 سؤال)")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_html(
        f"مرحباً {user.mention_html()}!\nاختر من القائمة:",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("استخدم الأزرار أو الأوامر: /multiplication /cognitive /intelligence /ask_ai")

async def multiplication_table_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await multiplication_table_handler(update, context)
    return ASK_FOR_NUMBER

async def cognitive_questions_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await start_cognitive_quiz(update, context)

async def ask_qiyas_ai(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # الدالة الداخلية تتولى استخدام AI_API_KEY و AI_MODEL من env
    await ask_qiyas_ai_handler(update, context)

async def intelligence_questions_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await start_intelligence_quiz(update, context)

async def handle_main_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    if text == "جدول الضرب":
        await multiplication_table_entry(update, context)
    elif text == "اختبر قدراتك (500 سؤال)":
        await cognitive_questions_entry(update, context)
    elif text == "اسأل قياس (ذكاء اصطناعي)":
        await update.message.reply_text("اكتب سؤالك بالأمر: /ask_ai سؤالك هنا")
    elif text == "أسئلة الذكاء (300 سؤال)":
        await intelligence_questions_entry(update, context)
    else:
        await update.message.reply_text("اختر من القائمة لو سمحت.")

def build_application() -> Application:
    return Application.builder().token(TELEGRAM_BOT_TOKEN).build()

def main() -> None:
    app = build_application()

    # أوامر أساسية
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # جدول الضرب
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("multiplication", multiplication_table_entry)],
        states={ASK_FOR_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_multiplication_table)]},
        fallbacks=[CommandHandler("start", start)],
    ))

    # أسئلة قدرات معرفية
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("cognitive", cognitive_questions_entry)],
        states={SELECTING_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]},
        fallbacks=[CommandHandler("start", start)],
    ))

    # أسئلة ذكاء
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("intelligence", intelligence_questions_entry)],
        states={SELECTING_INTELLIGENCE_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_intelligence_answer)]},
        fallbacks=[CommandHandler("start", start)],
    ))

    # اسأل قياس بالذكاء الاصطناعي
    app.add_handler(CommandHandler("ask_ai", ask_qiyas_ai))

    # أزرار القائمة
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu_buttons))

    # ====== تشغيل (Webhook على Render أو Polling محلي) ======
    if WEBHOOK_URL:
        logger.info("Running with WEBHOOK at %s", WEBHOOK_URL)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELEGRAM_BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}",
            drop_pending_updates=True
        )
    else:
        logger.info("Running with POLLING")
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
