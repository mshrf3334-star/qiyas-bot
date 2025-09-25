import os
import logging
from flask import Flask, request
import requests

# ----------------------------
# إعداد اللوق
# ----------------------------
logging.basicConfig(level=logging.INFO)

# ----------------------------
# قراءة المتغيرات من Render
# ----------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
AI_API_KEY = os.environ.get("AI_API_KEY")
AI_MODEL = os.environ.get("AI_MODEL", "gpt-4o-mini")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN غير موجود في Render")

# رابط API تيليجرام
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ----------------------------
# إنشاء تطبيق Flask
# ----------------------------
app = Flask(__name__)

# ----------------------------
# Webhook: استقبال الرسائل من تيليجرام
# ----------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    logging.info(update)

    if "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        user_text = update["message"]["text"]

        # الرد من OpenAI
        reply = ask_openai(user_text)

        # إرسال الرد للعميل
        send_message(chat_id, reply)

    return {"ok": True}


# ----------------------------
# التكامل مع OpenAI
# ----------------------------
def ask_openai(prompt):
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": AI_MODEL,
            "messages": [
                {"role": "system", "content": "أجب بالعربية باختصار."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500
        }

        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            logging.error(f"OpenAI Error: {response.status_code} - {response.text}")
            return "❌ حصل خطأ من OpenAI"
    except Exception as e:
        logging.error(f"OpenAI Connection Error: {e}")
        return "⚠️ خطأ أثناء الاتصال بالذكاء الاصطناعي"


# ----------------------------
# إرسال رسالة لتيليجرام
# ----------------------------
def send_message(chat_id, text):
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        logging.error(f"Telegram send error: {e}")


# ----------------------------
# صفحة افتراضية للتأكد أن السيرفر شغال
# ----------------------------
@app.route("/")
def home():
    return "🤖 البوت شغال على Render!"


# ----------------------------
# تشغيل محلي
# ----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
