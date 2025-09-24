from flask import Flask, request
import telegram
import os

app = Flask(__name__)

# جلب التوكن من المتغيرات البيئية في Render
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
bot = telegram.Bot(token=TOKEN)

@app.route('/')
def home():
    return "البوت شغال ✅"

# مسار الويب هوك - لازم يكون مطابق للرابط اللي سجلته مع Telegram
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        chat_id = update.message.chat.id
        text = update.message.text

        # رد بسيط
        bot.sendMessage(chat_id=chat_id, text=f"📩 وصلتني رسالتك: {text}")
    except Exception as e:
        print("Error:", e)
    return "ok"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
