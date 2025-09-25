from telegram import Update
from telegram.ext import ContextTypes
from openai import OpenAI
import os

# This will be set from main.py
AI_API_KEY = os.environ.get("AI_API_KEY", "YOUR_AI_API_KEY")
AI_MODEL = os.environ.get("AI_MODEL", "openai/gpt-4o-mini")

async def ask_qiyas_ai_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the AI-powered 'Ask Qiyas' feature."""
    if not AI_API_KEY or not AI_MODEL:
        await update.message.reply_text("عذراً، لم يتم تهيئة مفتاح API أو نموذج الذكاء الاصطناعي بشكل صحيح.")
        return

    client = OpenAI(api_key=AI_API_KEY)

    user_question = update.message.text.replace("/ask_ai ", "").strip()

    if not user_question:
        await update.message.reply_text("الرجاء طرح سؤال بعد الأمر /ask_ai.")
        return

    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "أنت مساعد ذكاء اصطناعي متخصص في تقديم معلومات حول القدرات المعرفية والذكاء، وتجيب على أسئلة الطلاب باللغة العربية."},
                {"role": "user", "content": user_question}
            ]
        )
        ai_response = response.choices[0].message.content
        await update.message.reply_text(ai_response)
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ أثناء معالجة طلبك: {e}")
