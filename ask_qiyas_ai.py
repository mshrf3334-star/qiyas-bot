# ask_qiyas_ai.py
import os, asyncio
from tenacity import retry, wait_fixed, stop_after_attempt
from openai import OpenAI
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_MODEL   = os.environ.get("AI_MODEL", "openai/gpt-4o-mini")

def _chunks(s: str, n: int = 3500):
    s = s or ""
    for i in range(0, len(s), n):
        yield s[i:i+n]

@retry(wait=wait_fixed(1.5), stop=stop_after_attempt(2))
def _ask_llm(question: str) -> str:
    client = OpenAI(api_key=AI_API_KEY)
    resp = client.chat.completions.create(
        model=AI_MODEL,
        temperature=0.3,
        messages=[
            {"role": "system", "content":
             "أنت مساعد قياس ذكي بالعربية: مختصر، دقيق، وخطوة-بخطوة عند الحاجة."},
            {"role": "user", "content": question.strip()}
        ],
    )
    return (resp.choices[0].message.content or "").strip()

async def ask_qiyas_ai_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the AI-powered 'Ask Qiyas' feature."""
    text = (update.message.text or "").replace("/ask_ai", "", 1).strip()

    if not AI_API_KEY:
        await update.message.reply_text("مفتاح الذكاء الاصطناعي غير مُهيأ على الخادم.")
        return
    if not text:
        await update.message.reply_text("اكتب سؤالك بعد الأمر: /ask_ai سؤالك هنا")
        return

    # أظهر حالة الكتابة
    try:
        await update.effective_chat.send_action(ChatAction.TYPING)
    except Exception:
        pass

    try:
        answer = await asyncio.wait_for(
            asyncio.to_thread(_ask_llm, text),
            timeout=20
        )
        if not answer:
            answer = "لم أحصل على إجابة مناسبة، جرّب إعادة الصياغة."
        for part in _chunks(answer):
            await update.message.reply_text(part)
    except asyncio.TimeoutError:
        await update.message.reply_text("المهلة انتهت ⏱️ — جرّب سؤالاً أقصر أو أعِد المحاولة.")
    except Exception as e:
        await update.message.reply_text(f"تعذّر إكمال الطلب: {e}")
