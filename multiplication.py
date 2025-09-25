from telegram import Update
from telegram.ext import ContextTypes

async def multiplication_table_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the multiplication table feature."""
    # TODO: Ask the user for a number
    await update.message.reply_text("أدخل الرقم الذي تريد جدول الضرب له:")

async def generate_multiplication_table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generates the multiplication table for the given number."""
    try:
        number = int(update.message.text)
        table = ""
        for i in range(1, 11):
            table += f"{number} x {i} = {number * i}\n"
        await update.message.reply_text(table)
    except ValueError:
        await update.message.reply_text("الرجاء إدخال رقم صحيح.")
