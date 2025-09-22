import os
import requests
from flask import Flask, request

app = Flask(__name__)

# اقرأ التوكن من Environment Variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")

TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}"

@app.route("/")
def home():
    return "Qiyas Bot is running ✅"

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update:
        return "no update"

    chat_id = update["message"]["chat"]["id"]
    user_message = update["message"].get("text", "")

    # رد تجريبي مباشر
    reply_text = f"📚 أهلاً بك في بوت القدرات!\n\nرسالتك: {user_message}"

    # إرسال الرد إلى تيليجرام
    send_message(chat_id, reply_text)

    return "ok"

def send_message(chat_id, text):
    url = f"{TELEGRAM_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
