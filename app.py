# app.py
import os
import logging
from fastapi import FastAPI, Request
import uvicorn

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

# وحداتك
from multiplication import multiplication_table_handler, generate_multiplication_table
from cognitive_questions import start_cognitive_quiz, handle_answer, SELECTING_ANSWER
from intelligence_questions import (
    start_intelligence_quiz, handle_intelligence_answer, SELECTING_INTELLIGENCE_ANSWER
)
from ask_qiyas_ai import ask_qiyas_ai_handler

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
logger = logging.getLogger(__name__)

ASK_FOR_NUMBER = 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [KeyboardButton("جدول الضرب")],
        [KeyboardButton("اختبر قدراتك (500 سؤال)")],
        [KeyboardButton("اسأل قياس (ذكاء اصطناعي)")],
        [KeyboardButton("أسئلة الذكاء (300 سؤال)")],
    ]
    await update.message.reply_html(
        "مرحباً! اختر من القائمة 👇",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("استخدم: /multiplication /cognitive /intelligence /ask_ai")

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

def build_ptb_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("multiplication", multiplication_table_handler)],
        states={ASK_FOR_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_multiplication_table)]},
        fallbacks=[CommandHandler("start", start)],
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("cognitive", start_cognitive_quiz)],
        states={SELECTING_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]},
        fallbacks=[CommandHandler("start", start)],
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("intelligence", start_intelligence_quiz)],
        states={SELECTING_INTELLIGENCE_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_intelligence_answer)]},
        fallbacks=[CommandHandler("start", start)],
    ))

    app.add_handler(CommandHandler("ask_ai", ask_qiyas_ai_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu))

    return app

ptb = build_ptb_app()
fastapi_app = FastAPI()

@fastapi_app.get("/")
async def root():
    return {"ok": True, "service": "qiyas-bot"}

@fastapi_app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, ptb.bot)
    await ptb.process_update(update)
    return {"ok": True}

if __name__ == "__main__":
    # اضبط الويب هوك مرة واحدة (أو من ملف مستقل)
    import asyncio
    async def _set_hook():
        await ptb.initialize()
        await ptb.bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}", drop_pending_updates=True)
        await ptb.shutdown()  # سنشغل المعالجة عبر FastAPI
    asyncio.run(_set_hook())

    uvicorn.run(fastapi_app, host="0.0.0.0", port=PORT)
