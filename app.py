import os
import json
import logging
import random
from flask import Flask, request

# Telegram Bot API v13
from telegram import Bot, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext

# ---------------- Logging ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("qiyas-bot")

# ---------------- ENV ----------------
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("حدد TELEGRAM_BOT_TOKEN في المتغيرات على Render")

bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, workers=0)

# ---------------- Load Questions ----------------
DATA_FILE = "data.json"
with open(DATA_FILE, "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

# ---------------- Keyboards ----------------
RESTART_TEXT = "🔁 إعادة الاختبار"
TIMES_MENU   = ["5 أسئلة", "10 أسئلة", "20 سؤال"]
TIMES_QUIT   = "⏹️ إنهاء اختبار الضرب"

MAIN_MENU_KB = ReplyKeyboardMarkup(
    [
        ["🧠 اختبار القدرات"],
        ["📊 نتيجتي", "🧮 اختبار جدول الضرب"]
    ],
    resize_keyboard=True
)
restart_kb = ReplyKeyboardMarkup([[RESTART_TEXT]], resize_keyboard=True, one_time_keyboard=True)
times_choose_kb = ReplyKeyboardMarkup([TIMES_MENU, [TIMES_QUIT]], resize_keyboard=True)
times_kb = ReplyKeyboardMarkup([[TIMES_QUIT]], resize_keyboard=True)

# ---------------- State ----------------
# اختيار من متعدد: user_id -> { pool, index, correct, wrong, type }
user_progress = {}
# وضعية عامة: user_id -> "mcq" | "times" | None
mode = {}
# حالة اختبار الضرب: user_id -> {"q":..,"correct":..,"a":..,"b":..,"answer":..,"total":..,"choosing":True/False}
times_state = {}

# ---------------- Helpers (MCQ) ----------------
def make_pool(qtype: str | None):
    if not qtype or qtype.lower() == "all":
        return QUESTIONS[:], "all"
    qtype = qtype.lower()
    pool = [q for q in QUESTIONS if str(q.get("type","")).lower() == qtype]
    return (pool if pool else QUESTIONS[:]), (qtype if pool else "all")

def reset_user(user_id: int, qtype: str | None = None):
    pool, qtype_final = make_pool(qtype)
    user_progress[user_id] = {"pool": pool, "index": 0, "correct": 0, "wrong": 0, "type": qtype_final}

def send_mcq_question(update: Update, context: CallbackContext, user_id: int):
    st = user_progress[user_id]
    pool = st["pool"]
    idx  = st["index"]
    total_q = len(pool)

    if idx >= total_q:
        correct = st["correct"]; wrong = st["wrong"]
        total = correct + wrong
        score = round((correct / total) * 100, 2) if total > 0 else 0.0
        kind = st["type"]
        update.message.reply_text(
            f"🎉 خلّصت اختبار ({'الكل' if kind=='all' else kind}).\n\n"
            f"✅ صحيحة: {correct}\n"
            f"❌ خاطئة: {wrong}\n"
            f"📊 الدرجة: {score}%",
            reply_markup=restart_kb,
        )
        return

    q = pool[idx]
    text = f"❓ السؤال {idx+1}/{total_q}\n\n{q['question']}\n\n"
    for i, choice in enumerate(q["choices"], start=1):
        text += f"{i}. {choice}\n"
    update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())

# ---------------- Helpers (Times) ----------------
def times_reset(user_id: int, total=10):
    times_state[user_id] = {"q": 0, "correct": 0, "a": 0, "b": 0, "answer": 0, "total": total, "choosing": False}

def times_next_question(update: Update, user_id: int):
    st = times_state[user_id]
    st["q"] += 1
    if st["q"] > st["total"]:
        score = round(st["correct"] / st["total"] * 100, 2)
        update.message.reply_text(
            f"✅ انتهى اختبار الضرب!\n"
            f"عدد الأسئلة: {st['total']}\n"
            f"إجابات صحيحة: {st['correct']}\n"
            f"درجتك: {score}%",
            reply_markup=MAIN_MENU_KB
        )
        mode[user_id] = None
        return
    a = random.randint(1, 10); b = random.randint(1, 10)
    st["a"], st["b"], st["answer"] = a, b, a * b
    update.message.reply_text(
        f"سؤال {st['q']}/{st['total']} — اكتب الناتج رقمياً:\n\n{a} × {b} = ؟",
        reply_markup=times_kb
    )

# ---------------- Commands ----------------
def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    mode[user_id] = None
    update.message.reply_text("مرحباً! اختر من الأزرار:", reply_markup=MAIN_MENU_KB)

def quiz(update: Update, context: CallbackContext):
    qtype = None
    if context.args:
        qtype = context.args[0].lower()
        if qtype not in {"math", "logic", "all"}:
            update.message.reply_text("ℹ️ الأنواع المتاحة: math, logic, all\nمثال: /quiz math")
            return
    user_id = update.message.from_user.id
    mode[user_id] = "mcq"
    reset_user(user_id, qtype)
    kind = user_progress[user_id]["type"]
    update.message.reply_text(f"🧠 بدأنا اختبار ({'الكل' if kind=='all' else kind}). جاوب بالأرقام 1–4.", reply_markup=ReplyKeyboardRemove())
    send_mcq_question(update, context, user_id)

def score(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in user_progress:
        update.message.reply_text("ℹ️ اكتب /quiz للبدء ثم /score لعرض نتيجتك.")
        return
    st = user_progress[user_id]
    idx = st["index"]; c = st["correct"]; w = st["wrong"]
    total = c + w
    pct = round((c / total) * 100, 2) if total > 0 else 0.0
    update.message.reply_text(
        f"📊 نتيجتك ({'الكل' if st['type']=='all' else st['type']}):\n"
        f"السؤال: {min(idx+1, len(st['pool']))}/{len(st['pool'])}\n"
        f"✅ صحيحة: {c}\n❌ خاطئة: {w}\n📈 النسبة: {pct}%"
    )

# ---------------- Text Handler ----------------
def handle_text(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = (update.message.text or "").strip()

    # أزرار القائمة
    if text == "🧠 اختبار القدرات":
        quiz(update, context); return
    if text == "📊 نتيجتي":
        score(update, context); return
    if text == "🧮 اختبار جدول الضرب":
        mode[user_id] = "times"
        # اختيار عدد الأسئلة أولاً
        times_state[user_id] = {"choosing": True}
        update.message.reply_text("اختر عدد الأسئلة:", reply_markup=times_choose_kb)
        return

    # إعادة اختبار MCQ
    if text == RESTART_TEXT:
        if user_id in user_progress:
            prev_type = user_progress[user_id].get("type", "all")
        else:
            prev_type = "all"
        mode[user_id] = "mcq"
        reset_user(user_id, prev_type)
        update.message.reply_text("🔁 بدأنا من جديد!", reply_markup=ReplyKeyboardRemove())
        send_mcq_question(update, context, user_id)
        return

    # منطق اختيار عدد أسئلة الضرب
    if mode.get(user_id) == "times":
        st = times_state.get(user_id, {})
        if text == TIMES_QUIT:
            mode[user_id] = None
            update.message.reply_text("تم إنهاء اختبار الضرب.", reply_markup=MAIN_MENU_KB)
            return
        if st.get("choosing"):
            if text not in TIMES_MENU:
                update.message.reply_text("اختر من الأزرار: 5 أسئلة / 10 أسئلة / 20 سؤال", reply_markup=times_choose_kb)
                return
            total = 10
            if text.startswith("5"): total = 5
            elif text.startswith("10"): total = 10
            elif text.startswith("20"): total = 20
            times_reset(user_id, total=total)
            update.message.reply_text(f"🧮 بدأنا اختبار الضرب ({total} سؤال). اكتب الناتج رقمياً.", reply_markup=times_kb)
            times_next_question(update, user_id)
            return
        # الإجابة الرقمية
        if not text.isdigit():
            update.message.reply_text("⚠️ اكتب الناتج رقمياً (مثال: 24) أو اضغط إنهاء.", reply_markup=times_kb)
            return
        st = times_state[user_id]
        val = int(text)
        if val == st["answer"]:
            st["correct"] = st.get("correct", 0) + 1
            update.message.reply_text("✅ صحيح!")
        else:
            update.message.reply_text(f"❌ خطأ. الصحيح: {st['answer']}")
        times_next_question(update, user_id)
        return

    # وضعية MCQ
    if mode.get(user_id) == "mcq":
        if user_id not in user_progress:
            update.message.reply_text("💡 اكتب /quiz للبدء.", reply_markup=MAIN_MENU_KB)
            return
        st = user_progress[user_id]
        idx = st["index"]
        if idx >= len(st["pool"]):
            update.message.reply_text("✅ الاختبار انتهى.", reply_markup=restart_kb)
            return
        if not text.isdigit():
            update.message.reply_text("⚠️ اكتب رقم الاختيار (1–4).")
            return
        choice = int(text) - 1
        if choice < 0 or choice > 3:
            update.message.reply_text("⚠️ الاختيارات من 1 إلى 4 فقط.")
            return
        q = st["pool"][idx]
        if choice == q["answer_index"]:
            st["correct"] += 1
            update.message.reply_text(f"✅ صحيح!\n{q.get('explanation','')}".strip())
        else:
            st["wrong"] += 1
            correct_choice = q["choices"][q["answer_index"]]
            update.message.reply_text(f"❌ خطأ.\nالصحيح: {correct_choice}\n{q.get('explanation','')}".strip())
        st["index"] += 1
        send_mcq_question(update, context, user_id)
        return

    # لو ما في وضعية
    update.message.reply_text("اختر من الأزرار:", reply_markup=MAIN_MENU_KB)

# ---------------- Bind ----------------
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("quiz", quiz))
dispatcher.add_handler(CommandHandler("score", score))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

# ---------------- Webhook ----------------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/", methods=["GET"])
def home():
    return "✅ البوت شغال!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
