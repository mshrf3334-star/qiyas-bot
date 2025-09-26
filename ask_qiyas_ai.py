# ask_qiyas_ai.py
# — يعمل بدون tenacity — يستخدم إعادة محاولة بسيطة

import os
import logging
import asyncio
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes
from openai import OpenAI

# ===== الإعدادات من المتغيرات البيئية =====
AI_API_KEY = os.getenv("AI_API_KEY")
AI_MODEL   = os.getenv("AI_MODEL", "gpt-4o-mini")

logger = logging.getLogger(__name__)
_client: Optional[OpenAI] = None


def _get_client() -> Optional[OpenAI]:
    """تهيئة عميل OpenAI مرة واحدة."""
    global _client
    if not AI_API_KEY:
        return None
    if _client is None:
        _client = OpenAI(api_key=AI_API_KEY)
    return _client


async def ask_qiyas_ai_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    أمر: /ask_ai سؤالك هنا
    أو: ردّ بالأمر /ask_ai على رسالة تحوي السؤال.
    """
    # الحصول على نص السؤال
    question = " ".join(context.args) if context.args else None
    if not question and update.message and update.message.reply_to_message:
        question = update.message.reply_to_message.text

    if not question:
        await update.effective_message.reply_html(
            "اكتب سؤالك بعد الأمر:<code> /ask_ai سؤالك </code>\n"
            "أو ردّ بالأمر على رسالة تحتوي سؤالك."
        )
        return

    if not AI_API_KEY:
        await update.effective_message.reply_text(
            "🛑 لم يتم ضبط مفتاح الذكاء الاصطناعي (AI_API_KEY)."
        )
        return

    try:
        answer = await _ask_llm(question)
        if not answer:
            answer = "لم أستطع توليد إجابة الآن. حاول لاحقًا."
        # حد التلغرام 4096 حرف للرسالة الواحدة
        await update.effective_message.reply_text(answer[:4096])
    except Exception as e:
        logger.exception("ask_ai error: %s", e)
        await update.effective_message.reply_text("حدث خطأ أثناء الإجابة. حاول لاحقًا.")


async def _ask_llm(prompt: str) -> str:
    """
    نداء LLM مع محاولات بسيطة (3 محاولات بتأخيرات 0s/1.5s/3s).
    """
    client = _get_client()
    if not client:
        return "المفتاح غير مهيأ."

    delays = [0.0, 1.5, 3.0]
    last_err: Optional[Exception] = None

    for delay in delays:
        if delay:
            await asyncio.sleep(delay)
        try:
            resp = client.chat.completions.create(
                model=AI_MODEL,
                temperature=0.3,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "أنت مساعد قياس ذكي بالعربية: موجز، دقيق، ويشرح الخطوات عند الحاجة."
                        ),
                    },
                    {"role": "user", "content": prompt.strip()},
                ],
            )
            content = (resp.choices[0].message.content or "").strip()
            return content
        except Exception as e:
            last_err = e
            logger.warning("LLM call failed (will retry): %s", e)

    # إذا فشلت كل المحاولات
    raise last_err if last_err else RuntimeError("LLM call failed")
