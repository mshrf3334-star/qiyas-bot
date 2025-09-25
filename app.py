import os
import logging
from typing import Any, Dict

from flask import Flask, request, abort, jsonify
import requests

# =========================
# إعداد السجلّات
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
log = logging.getLogger("qiyas-bot")

# =========================
# متغيرات البيئة
# =========================
BOT_TOKEN    = os.getenv("BOT_TOKEN")  # إلزامي
AI_API_KEY   = os.getenv("AI_API_KEY", "")  # اختياري
AI_MODEL     = os.getenv("AI_MODEL", "gpt-4o-mini")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")  # تقدر تغيّره من الإعدادات
TG_SECRET    = os.getenv("TG_SECRET", "")  # اختياري: سرّ للتحقق من مرسل الويبهوك

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN غير موجود في Environment Variables على Render.")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# =========================
# تطبيق Flask
# =========================
app = Flask(__name__)

@app.get("/")
def home():
    """صحة الخدمة"""
    return "✅ البوت شغال على Render!", 200


# =========================
# أدوات مساعدة
# =========================
def _j(d: Dict[str, Any], *keys, default=None):
    """قراءة آمنة من ديكشنري متشعّب"""
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def tg_send_message(chat_id: int, text: str, parse_mode: str | None = None):
    """إرسال رسالة تيليجرام مع تايم-آوت ومعالجة أخطاء"""
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        r = requests.post(url, json=payload, timeout=12)
        r.raise_for_status()
    except Exception as e:
        log.error(f"Telegram send error: {e}")

def ask_openai(prompt: str) -> str:
    """نداء OpenAI باختصار؛ إذا المفتاح غير موجود يرجّع رسالة مناسبة"""
    if not AI_API_KEY:
        return "🤖 الذكاء الاصطناعي غير مفعّل. أضف AI_API_KEY ثم جرّب."

    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {AI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": AI_MODEL,
                "messages": [
                    {"role": "system", "content": "أجب باختصار وبالعربية."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.4,
                "max_tokens": 500,
            },
            timeout=20,
        )
        if r.status_code == 200:
            data = r.json()
            return _j(data, "choices", 0, "message", "content", default="").strip() or "…"
        else:
            log.error(f"OpenAI Error {r.status_code}: {r.text}")
            return "❌ حصل خطأ أثناء توليد الإجابة من OpenAI."
    except Exception as e:
        log.error(f"OpenAI Connection Error: {e}")
        return "⚠️ تعذّر الاتصال بالذكاء الاصطناعي الآن."


# =========================
# Webhook
# =========================
@app.post(WEBHOOK_PATH)
def webhook():
    # تحقق اختياري من السر لو مفعّل
    if TG_SECRET:
        if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != TG_SECRET:
            abort(403)

    update = request.get_json(silent=True) or {}
    log.info(update)

    message = update.get("message") or update.get("edited_message")
    if not message:
        # مهم نرجّع 200 بسرعة لتجنّب إعادة المحاولة من تيليجرام
        return jsonify(ok=True)

    chat_id = _j(message, "chat", "id")
    text = message.get("text", "") if isinstance(message, dict) else ""

    if not chat_id:
        return jsonify(ok=True)

    # أوامر بسيطة
    if text.strip() == "/start":
        tg_send_message(
            chat_id,
            "👋 أهلاً! اكتب سؤالك وسأجيبك بالذكاء الاصطناعي.\n"
            "— أرسل /help لعرض المساعدة."
        )
        return jsonify(ok=True)

    if text.strip() == "/help":
        tg_send_message(
            chat_id,
            "ℹ️ الأوامر:\n"
            "• /start — بدء المحادثة\n"
            "• /help — هذه المساعدة\n"
            "أرسل أي سؤال نصي وسيتم الرد عبر الذكاء الاصطناعي."
        )
        return jsonify(ok=True)

    if text:
        reply = ask_openai(text)
        tg_send_message(chat_id, reply)
    else:
        tg_send_message(chat_id, "أرسل نصًا لو سمحت.")

    return jsonify(ok=True)


# =========================
# تشغيل محلي (للاختبار)
# =========================
if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
