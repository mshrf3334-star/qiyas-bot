import os
from flask import Flask, request
import requests

# متغيرات البيئة من Render
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")

app = Flask(__name__)

TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

@app.route("/")
def home():
    return "🤖 Qiyas Bot is running!", 200

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"]["text"]

        # نرسل النص للذكاء الاصطناعي
        headers = {"Authorization": f"Bearer {AI_API_KEY}"}
        payload = {
            "model": AI_MODEL,
            "messages": [
                {"role": "system", "content": "أنت مساعد ذكي للتدريب على اختبارات القدرات (Qiyas)."},
                {"role": "user", "content": user_text}
            ]
        }

        try:
            r = requests.post(OPENAI_URL, headers=headers, json=payload)
            result = r.json()
            ai_reply = result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            ai_reply = "⚠️ صار خطأ أثناء الاتصال بالذكاء الاصطناعي."

        # نرد على المستخدم
        requests.post(TELEGRAM_URL, json={"chat_id": chat_id, "text": ai_reply})

    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
