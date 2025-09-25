# ask_qiyas_ai.py
from telegram import Update
from telegram.ext import ContextTypes
from openai import OpenAI
import os, asyncio, textwrap

# إعدادات افتراضية (يمكن تغييرها من الـ env)
DEFAULT_MODEL = "gpt-4o"  # جودة أعلى من gpt-4o-mini

SYSTEM_PROMPT = """أنت خبير قياس وقدرات وذكاء عام باللغة العربية الفصحى.
- أجب بدقة وباختصار مفيد أولاً، ثم وسّع عند الحاجة.
- استخدم عناوين فرعية ونقاط مرتبة عند الشرح.
- في المسائل الحسابية اذكر خطوات الحل باقتضاب، وتحقق من النتيجة.
- إن كان السؤال غامضًا فاطلب توضيحًا محددًا.
- لا تضع معلومات بلا مصادر ضمنية أو استنتاجات واهية.
"""

def _split_chunks(text: str, max_len: int = 3500):
    """تقسيم النص الطويل على دفعات مناسبة لتيليجرام (أقل من 4096)."""
    text = textwrap.dedent(text).strip()
    parts, buf, count = [], [], 0
    for line in text.splitlines(True):
        ln = len(line)
        if count + ln > max_len and buf:
            parts.append("".join(buf))
            buf, count = [line], ln
        else:
            buf.append(line); count += ln
    if buf:
        parts.append("".join(buf))
    return parts or [""]

async def ask_qiyas_ai_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ميزة: اسأل قياس (ذكاء اصطناعي)."""
    # قراءة المفاتيح عند الاستدعاء (أضمن مع إعادة النشر)
    ai_key = os.environ.get("AI_API_KEY", "").strip()
    model  = os.environ.get("AI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

    if not ai_key:
        await update.message.reply_text("مفتاح AI_API_KEY غير مضاف في الإعدادات.")
        return

    # التقاط السؤال سواء كان بعد /ask_ai أو في بقية الرسالة
    if context.args:
        user_question = " ".join(context.args).strip()
    else:
        # يدعم الكتابة: "/ask_ai ما هو..." أو رد بدون args
        user_question = (update.message.text or "").replace("/ask_ai", "", 1).strip()

    if not user_question:
        await update.message.reply_text("اكتب سؤالك بعد الأمر /ask_ai مثلًا:\n/ask_ai طرق تحسين الذاكرة؟")
        return

    # مؤشر يكتب…
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    client = OpenAI(api_key=ai_key)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_question}
            ],
            temperature=0.2,   # ثبات وجودة أعلى
            top_p=1.0,
            max_tokens=800,    # رد وافي لكن غير مبالغ فيه
        )

        answer = (resp.choices[0].message.content or "").strip()
        if not answer:
            await update.message.reply_text("لم يصلني رد واضح من النموذج. جرّب سؤالًا أقصر أو أدق.")
            return

        # تقسيم وإرسال الرد
        for chunk in _split_chunks(answer):
            await update.message.reply_text(chunk, disable_web_page_preview=True)
            await asyncio.sleep(0.15)

    except Exception as e:
        msg = str(e)
        # رسائل ألطف لبعض الأخطاء الشائعة
        if "rate" in msg.lower():
            nice = "النظام مشغول الآن (Rate limit). حاول بعد لحظات."
        elif "api_key" in msg.lower() or "authentication" in msg.lower():
            nice = "مشكلة مصادقة مع مزود الذكاء الاصطناعي. تحقق من AI_API_KEY."
        else:
            nice = f"حدث خطأ أثناء معالجة طلبك.\nالتفاصيل: {msg}"
        await update.message.reply_text(nice)
