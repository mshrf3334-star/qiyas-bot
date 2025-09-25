import logging
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from multiplication import multiplication_table_handler, generate_multiplication_table
from cognitive_questions import start_cognitive_quiz, handle_answer, SELECTING_ANSWER
from ask_qiyas_ai import ask_qiyas_ai_handler, AI_API_KEY as AI_API_KEY_AI_MODULE, AI_MODEL as AI_MODEL_AI_MODULE
from intelligence_questions import start_intelligence_quiz, handle_intelligence_answer, SELECTING_INTELLIGENCE_ANSWER

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Replace with your actual bot token and AI API key
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
AI_API_KEY = os.environ.get("AI_API_KEY", "YOUR_AI_API_KEY")
AI_MODEL = os.environ.get("AI_MODEL", "openai/gpt-4o-mini")

AI_API_KEY_AI_MODULE = AI_API_KEY
AI_MODEL_AI_MODULE = AI_MODEL

# States for ConversationHandler
ASK_FOR_NUMBER = 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message when the command /start is issued."""
    user = update.effective_user
    keyboard = [
        [KeyboardButton("جدول الضرب")],
        [KeyboardButton("اختبر قدراتك (500 سؤال)")],
        [KeyboardButton("اسأل قياس (ذكاء اصطناعي)")],
        [KeyboardButton("أسئلة الذكاء (300 سؤال)")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_html(
        f"مرحباً {user.mention_html()}!\nأنا بوت قياس القدرات المعرفية. اختر أحد الخيارات التالية:",
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message when the command /help is issued."""
    await update.message.reply_text("يمكنك اختيار أحد الخيارات من القائمة الرئيسية.")

async def multiplication_table_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for the multiplication table feature."""
    await multiplication_table_handler(update, context)
    return 0 # Placeholder for state, will be replaced by a state constant

async def cognitive_questions_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for the cognitive questions feature."""
    return await start_cognitive_quiz(update, context)


async def ask_qiyas_ai(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the AI-powered 'Ask Qiyas' feature."""
    await ask_qiyas_ai_handler(update, context)


async def intelligence_questions_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for the intelligence questions feature."""
    return await start_intelligence_quiz(update, context)


async def handle_main_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles messages from the main menu buttons."""
    text = update.message.text

    if text == "جدول الضرب":
        await multiplication_table_entry(update, context)
    elif text == "اختبر قدراتك (500 سؤال)":
        await cognitive_questions_entry(update, context)
    elif text == "اسأل قياس (ذكاء اصطناعي)":
        await update.message.reply_text("الرجاء طرح سؤالك بعد الأمر /ask_ai (مثال: /ask_ai ما هو الذكاء؟)")
    elif text == "أسئلة الذكاء (300 سؤال)":
        await intelligence_questions_entry(update, context)
    else:
        await update.message.reply_text("الرجاء اختيار أحد الخيارات من القائمة الرئيسية.")

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    # On different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    multiplication_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("multiplication", multiplication_table_entry)],
        states={
            ASK_FOR_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_multiplication_table)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    application.add_handler(multiplication_conv_handler)
    cognitive_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("cognitive", cognitive_questions_entry)],
        states={
            SELECTING_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    application.add_handler(cognitive_conv_handler)

    application.add_handler(CommandHandler("ask_ai", ask_qiyas_ai))
    intelligence_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("intelligence", intelligence_questions_entry)],
        states={
            SELECTING_INTELLIGENCE_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_intelligence_answer)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    application.add_handler(intelligence_conv_handler)


    # On non command messages - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu_buttons))

    # Run the bot
    # For local development, use application.run_polling()
    # For deployment with webhook, use application.run_webhook()
    # application.run_polling(allowed_updates=Update.ALL_TYPES)

    # For webhook deployment on Render
    PORT = int(os.environ.get("PORT", "8443"))
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

    if WEBHOOK_URL:
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
        )
    else:
        application.run_polling(allowed_updates=Update.ALL_TYPES)



if __name__ == "__main__":
    main()
