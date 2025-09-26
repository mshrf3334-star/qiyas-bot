from telegram import Update
from telegram.ext import ContextTypes

ASK_FOR_NUMBER = 10

async def multiplication_table_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("أدخل الرقم الذي تريد جدول الضرب له:")
    return ASK_FOR_NUMBER

async def generate_multiplication_table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        n = int(update.message.text.strip())
        lines = [f"{n} × {i} = {n*i}" for i in range(1, 11)]
        await update.message.reply_text("\n".join(lines))
    except ValueError:
        await update.message.reply_text("الرجاء إدخال رقم صحيح.")
    return ASK_FOR_NUMBER
