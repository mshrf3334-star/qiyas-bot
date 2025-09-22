import os
import requests
from flask import Flask, request

app = Flask(__name__)

# ====== المتغيرات من Render ======
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")           # مفتاح OpenAI
AI_MODEL   = os.getenv("AI_MODEL", "gpt-4o-mini")  # اسم الموديل

TELEGRAM_BASE = f"https://api.telegram.org/bot{TOKEN}"

# ====== توابع مساعدة ======
def send_message(chat_id: int, text: str):
    """إرسال رسالة لتليجرام (مع قصّ النص إذا تعدّى حد 4096 حرف)."""
    if len(text) > 4096:
        text = text[:4090] + " ..."
    requests.post(f"{TELEGRAM_BASE}/sendMessage", json={"chat_id": chat_id, "text": text})

def ask_ai(prompt: str) -> str:
    """استدعاء OpenAI والرجوع بإجابة مناسبة."""
    if not AI_API_KEY:
        return "⚠️ مفتاح الذكاء الاصطناعي (AI_API_KEY) غير مضبوط في Render."

    try:
        headers = {
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": AI_MODEL,
            "messages": [
                {"role": "system", "content": "أنت مساعد ذكي للتدريب على اختبارات القدرات (Qiyas). جاوب بالعربية باختصار ووضوح."},
                {"role": "user", "content": prompt},
            ],
        }
        r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=25)
        if r.status_code == 200:
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()
        else:
            # نطبع في اللوق لمعرفة المشكلة (401/400/429/500...)
            print("OpenAI error:", r.status_code, r.text)
            return "⚠️ تعذّر الاتصال بالذكاء الاصطناعي. تأكد من المفتاح (AI_API_KEY) واسم الموديل (AI_MODEL)."
    except Exception as e:
        print("OpenAI exception:", e)
        return "⚠️ صار خطأ أثناء الاتصال بالذكاء الاصطناعي."

# ====== مسارات الويب ======
@app.route("/")
def home():
    return "🤖 Qiyas Bot + AI is running!", 200

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json(silent=True) or {}
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return "no message", 200

    chat_id = msg["chat"]["id"]
    text = msg.get("text")

    if text:
        reply = ask_ai(text)
    else:
        reply = "📩 أرسل نصًا وسأساعدك في أسئلة القدرات."

    send_message(chat_id, reply)
    return "ok", 200

# ====== تشغيل محلي (لن يُستخدم على Render) ======
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
