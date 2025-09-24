from flask import Flask, request
import os
import requests

app = Flask(__name__)

# توكن البوت من الـ Environment Variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

@app.route('/')
def home():
    return "البوت شغال ✅"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("📩 رسالة جديدة:", data, flush=True)  # تظهر في اللوقس

    if "message" in data:
        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', '')

        # رد تجريبي
        reply = f"إستلمت رسالتك: {text}"
        requests.post(URL, json={"chat_id": chat_id, "text": reply})

    return {"ok": True}

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
