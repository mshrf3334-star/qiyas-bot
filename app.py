import os, json
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")  # ضعه في Render env vars
bot = Bot(token=TOKEN)

app = Flask(__name__)

# حمّل بنك الأسئلة
with open("data.json", encoding="utf-8") as f:
    DATA = json.load(f)

# أوامر بسيطة للتأكد
def start(update, context):
    update.message.reply_text("بوت قياس شغّال ✅")

def echo(update, context):
    update.message.reply_text("تم الاستلام ✋")

# Dispatcher بدون .start_polling (لأننا Webhook)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

@app.get("/")
def home():
    return "البوت شغّال!", 200

# المسار الذي سنضبطه في setWebhook
@app.post("/webhook")
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True, silent=True), bot)
    dispatcher.process_update(update)
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
