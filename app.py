import os
import logging
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

# ===== Logging =====
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("qiyas-bot")

# ===== Config =====
# استخدم نفس اسم المتغير اللي وضعته في Render
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing in environment variables.")

# Render يوفّر متغير RENDER_EXTERNAL_URL تلقائيًا
PUBLIC_URL = os.getenv("PUBLIC_URL") or os.getenv("RENDER_EXTERNAL_URL")

# ===== Telegram objects =====
bot = Bot(token=TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

# ===== Handlers =====
def cmd_start(update: Update, context):
    update.message.reply_text("👋 أهلاً بك في بوت القدرات (Qiyas)! أرسل أي رسالة أجرب أرد عليك.")

def echo(update: Update, context):
    text = update.message.text or ""
    update.message.reply_text(f"📩 استلمت: {text}")

dispatcher.add_handler(CommandHandler("start", cmd_start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

# ===== Flask app =====
app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    msg = "🤖 Qiyas Bot is running."
    if PUBLIC_URL:
        msg += f" Webhook URL: {PUBLIC_URL}/{TOKEN}"
    return msg

# نقطة استقبال التحديثات من تيليجرام (Webhook)
@app.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
    except Exception as e:
        logger.exception("update processing failed: %s", e)
        return "error", 500
    return "ok", 200

# Route مساعد لتثبيت الـ webhook يدويًا بعد النشر
@app.route("/setwebhook", methods=["GET"])
def set_webhook():
    if not PUBLIC_URL:
        return jsonify({"ok": False, "error": "PUBLIC_URL/RENDER_EXTERNAL_URL not set"}), 400
    url = f"{PUBLIC_URL}/{TOKEN}"
    ok = bot.set_webhook(url)
    return jsonify({"ok": ok, "url": url})

# للتشغيل المحلي (اختياري). في Render نشغّل بـ: gunicorn app:app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Starting local server on port {port}")
    # عند التشغيل محليًا يمكنك تفعيل polling بدل webhook لو رغبت:
    # from telegram.ext import Updater
    # Updater(TOKEN, use_context=True).start_polling()
    app.run(host="0.0.0.0", port=port)
