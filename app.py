import os
import logging
from flask import Flask, request
import requests

# إعداد اللوق
logging.basicConfig(level=logging.INFO)

# قراءة المتغيرات من Render (Environment Variables)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
AI_API_KEY = os.environ.get("AI_API_KEY")
AI_MODEL = os.environ.get("AI_MODEL", "gpt-4o-mini")

# تأكد أن التوكن موجود
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN غير موجود في Render")

# روابط تيليجرام
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# تطبيق Flask
app = Flask(__name__)

# استقبال التحديثات من تيليجرام
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

def ask_openai(prompt):
    """يتواصل مع OpenAI"""
    try:
        url = "https://api.openai.com/v1/responses"
        headers = {"Authorization": f"Bearer {AI_API_KEY}"}
        data = {"model": AI_MODEL, "input": prompt}

        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            return result["output"][0]["content"][0]["text"]
        else:
            logging.error(response.text)
            return "❌ حصل خطأ من OpenAI"
    except Exception as e:
        logging.error(e)
        return "⚠️ خطأ أثناء الاتصال بالذكاء الاصطناعي"

def send_message(chat_id, text):
    """يرسل رسالة للعميل"""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

@app.route("/")
def home():
    return "🤖 البوت شغال على Render!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
