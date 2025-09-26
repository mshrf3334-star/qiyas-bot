# app.py — Webhook only (محسّن)
import os
import logging
from typing import Iterable

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters, AIORateLimiter
)

# وحداتك
from multiplication import multiplication_table_handler, generate_multiplication_table
from cognitive_questions import start_cognitive_quiz, handle_answer, SELECTING_ANSWER
from intelligence_questions import (
    start_intelligence_quiz, handle_intelligence_answer, SELECTING_INTELLIGENCE_ANSWER
)
from ask_qiyas_ai import ask_qiyas_ai_handler

# ===== إعدادات =====
BOT_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN")
PORT        = int(os.environ.get("PORT", "10000"))
WEBHOOK_URL = (os.environ.get("WEBHOOK_URL") or "").rstrip("/")

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN مفقود")
if not WEBHOOK_URL:
    raise RuntimeError("WEBHOOK_URL مفقود (ضع رابط خدمة Render العامة)")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("qiyas-bot")

ASK_FOR_NUMBER = 0

# ===== Utilities =====
def chunk_text(text: str, limit: int = 4000) -> Iterable[str]:
    """يقسم النص لقطع تلائم حد تيليجرام."""
    text = text or ""
    for i in range(0, len(text), limit):
        yield text[i:i+limit]

async def safe_reply(update: Update, text: str, **kw):
    """يرسل نص طويل على دفعات تلقائياً."""
    for piece in chunk_text(text):
        await update.effective_message.reply_text(piece, **kw)

# ===== واجهة المستخدم =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [KeyboardButton("جدول الضرب")],
        [KeyboardButton("اختبر قدراتك (500 سؤال)")],
        [KeyboardButton("أسئلة الذكاء (300 سؤال)")],
        [KeyboardButton("اسأل قياس (ذكاء اصطناعي)")],
    ]
    await update.message.reply_html(
        "مرحباً! اختر من القائمة 👇",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "الأوامر المتاحة:\n"
        "/multiplication — جدول الضرب\n"
        "/cognitive — اختبار القدرات (500)\n"
        "/intelligence — أسئلة ذكاء (300)\n"
        "/ask_ai سؤالك — اسأل الذكاء الاصطناعي\n"
        "/ping — فحص سريع"
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ البوت شغّال.")

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = (update.message.text or "").strip()
    if t == "جدول الضرب":
        await multiplication_table_handler(update, context)
    elif t == "اختبر قدراتك (500 سؤال)":
        await start_cognitive_quiz(update, context)
    elif t == "أسئلة الذكاء (300 سؤال)":
        await start_intelligence_quiz(update, context)
    elif t == "اسأل قياس (ذكاء اصطناعي)":
        await update.message.reply_text("اكتب سؤالك بالأمر: /ask_ai سؤالك هنا")
    else:
        await update.message.reply_text("اختر من القائمة.")

# ===== أخطاء عامة =====
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled error: %s", context.error)
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "عذراً، حصل خطأ غير متوقع. جرّب لاحقاً."
            )
    except Exception:
        pass

def build_app() -> Application:
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .rate_limiter(AIORateLimiter(max_retries=2))  # احترام قيود تيليجرام
        .concurrent_updates(True)
        .build()
    )

    # أوامر عامة
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("ping", ping))

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

    app.add_error_handler(error_handler)
    return app

def main():
    app = build_app()
    logger.info("Starting Webhook at %s", WEBHOOK_URL)
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,                       # path سري
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}", # العنوان العام الكامل
        allowed_updates=[
            "message","edited_message","callback_query","my_chat_member","chat_member"
        ],
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
