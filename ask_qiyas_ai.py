from telegram import Update
from telegram.ext import ContextTypes
from openai import OpenAI
import os

AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_MODEL   = os.environ.get("AI_MODEL", "gpt-4o-mini")

async def ask_qiyas_ai_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /ask_ai"""
    q = (update.message.text or "").replace("/ask_ai", "", 1).strip()
    if not q:
        await update.message.reply_text("اكتب سؤالك بعد الأمر /ask_ai")
        return

    if not AI_API_KEY:
        await update.message.reply_text("مفتاح الذكاء الاصطناعي غير مُعد.")
        return

    try:
        client = OpenAI(api_key=AI_API_KEY)
        resp = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "أنت مساعد يجيب بالعربية على أسئلة قياس والقدرات."},
                {"role": "user", "content": q},
            ],
        )
        text = resp.choices[0].message.content.strip()
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ: {e}")
