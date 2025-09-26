# app.py — Webhook only / قوي ومرن
import os
import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# ميزات
from multiplication import ask_for_number, handle_possible_number_message
from cognitive_questions import start_cognitive_quiz, handle_cognitive_callback
from intelligence_questions import start_intelligence_quiz, handle_intelligence_callback
from ask_qiyas_ai import ask_qiyas_ai_handler
from qiyas_200 import start_qiyas_200_quiz, handle_qiyas_200_callback  # <-- الجديد

BOT_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = (os.environ.get("WEBHOOK_URL") or "").rstrip("/")
PORT        = int(os.environ.get("PORT", "10000"))

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN مفقود")
if not WEBHOOK_URL:
    raise RuntimeError("WEBHOOK_URL مفقود (ضع رابط خدمة Render العامة)")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("qiyas-bot")

def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("جدول الضرب")],
            [KeyboardButton("اختبر قدراتك (500 سؤال)")],
            [KeyboardButton("أسئلة الذكاء (300 سؤال)")],
            [KeyboardButton("اختبار قياس (200 سؤال)")],  # <-- الزر الجديد
            [KeyboardButton("اسأل قياس (ذكاء اصطناعي)")],
        ],
        resize_keyboard=True,
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html("مرحباً! اختر من القائمة 👇", reply_markup=main_keyboard())

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("استخدم الأزرار أو الأوامر: /multiplication /cognitive /intelligence /ask_ai", reply_markup=main_keyboard())

async def route_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = (update.message.text or "").strip()
    if t == "جدول الضرب":
        await ask_for_number(update, context); return
    if t == "اختبر قدراتك (500 سؤال)":
        await start_cognitive_quiz(update, context); return
    if t == "أسئلة الذكاء (300 سؤال)":
        await start_intelligence_quiz(update, context); return
    if t == "اختبار قياس (200 سؤال)":
        await start_qiyas_200_quiz(update, context); return  # <-- يبدأ الاختبار الطويل
    if t == "اسأل قياس (ذكاء اصطناعي)":
        await update.message.reply_text("اكتب سؤالك بالأمر: /ask_ai سؤالك هنا"); return
    await update.message.reply_text("اختر من القائمة.", reply_markup=main_keyboard())

async def unknown_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أمر غير معروف. استخدم /help", reply_markup=main_keyboard())

def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))

    # جدول الضرب
    app.add_handler(CommandHandler("multiplication", ask_for_number))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_possible_number_message))

    # أزرار القائمة
    app.add_handler(MessageHandler(filters.Regex(
        r"^(جدول الضرب|اختبر قدراتك \(500 سؤال\)|أسئلة الذكاء \(300 سؤال\)|اختبار قياس \(200 سؤال\)|اسأل قياس \(ذكاء اصطناعي\))$"
    ), route_buttons))

    # CallbackQuery للأنماط
    app.add_handler(CallbackQueryHandler(handle_cognitive_callback, pattern=r"^cog\|"))
    app.add_handler(CallbackQueryHandler(handle_intelligence_callback, pattern=r"^iq\|"))
    app.add_handler(CallbackQueryHandler(handle_qiyas_200_callback, pattern=r"^q200\|"))  # <-- الجديد

    app.add_handler(CommandHandler("ask_ai", ask_qiyas_ai_handler))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_cmd))
    return app

def main():
    app = build_app()
    log.info("Starting Webhook at %s", WEBHOOK_URL)
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
        drop_pending_updates=True,
    )

if __name__ == "__main__":
    main()
