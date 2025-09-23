# app.py
import os, json, time, random, asyncio
from flask import Flask, request
from typing import Dict, Any, Optional, List

# Telegram v20
from telegram import (
    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, Bot, KeyboardButton
)
from telegram.ext import (
    Application, MessageHandler, CommandHandler, ContextTypes, filters
)

# ======== الإعدادات ========
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # اختياري
BOT_NAME = "قياس"

# ======== الذكاء الاصطناعي (اختياري) ========
USE_AI = bool(OPENAI_API_KEY)
if USE_AI:
    import openai
    openai.api_key = OPENAI_API_KEY

async def ai_reply(text: str) -> str:
    """يرد من OpenAI (إن وجد)."""
    if not USE_AI:
        return "وضع الذكاء الاصطناعي غير مفعّل حاليًا."
    def _call():
        msgs = [
            {"role": "system", "content": f"أنت مساعد تعليمي عربي مختصر وودود باسم {BOT_NAME}. اشرح ببساطة وبخطوات."},
            {"role": "user", "content": text},
        ]
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=msgs, max_tokens=350, temperature=0.4
        )
        return resp["choices"][0]["message"]["content"].strip()
    return await asyncio.to_thread(_call)

# ======== تحميل بنك الأسئلة ========
def load_questions() -> List[Dict[str, Any]]:
    path = "data.json"
    if not os.path.exists(path):
        print("⚠️ لم يتم العثور على data.json — ميزة الاختبار ستظهر رسالة تنبيه.")
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # فحص بسيط للصيغة
        for i, q in enumerate(data, start=1):
            assert isinstance(q.get("question"), str)
            assert isinstance(q.get("choices"), list) and len(q["choices"]) == 4
            assert isinstance(q.get("answer_index"), int)
        print(f"✅ تم تحميل {len(data)} سؤالًا من data.json")
        return data
    except Exception as e:
        print("❌ خطأ قراءة/صيغة في data.json:", e)
        return []

QUESTIONS = load_questions()

# ======== حالة المستخدم ========
# state[user_id] = {
#   "mode": "idle" | "quiz" | "table" | "ai",
#   "idx": int, "correct": int, "wrong": int, "total": int,
#   "current_q": {...}, "timestamp": float
# }
state: Dict[int, Dict[str, Any]] = {}
COOLDOWN_SEC = 2.0  # مانع سبام بسيط

def now() -> float:
    return time.time()

def cooldown_ok(uid: int) -> bool:
    s = state.get(uid, {})
    last = s.get("timestamp", 0)
    if now() - last < COOLDOWN_SEC:
        return False
    s["timestamp"] = now()
    state[uid] = s
    return True

# ======== أدوات الاختبار ========
MAIN_KB = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🎯 اختبر نفسك"), KeyboardButton("🧮 جدول الضرب")],
        [KeyboardButton("🧠 اسأل قياس (ذكاء اصطناعي)")],
        [KeyboardButton("📊 نتيجتي"), KeyboardButton("🔁 إعادة")],
    ],
    resize_keyboard=True
)

CHOICE_KB = ReplyKeyboardMarkup(
    [[KeyboardButton("1"), KeyboardButton("2")],
     [KeyboardButton("3"), KeyboardButton("4")],
     [KeyboardButton("🔙 رجوع")]],
    resize_keyboard=True, one_time_keyboard=False
)

def reset_progress(uid: int):
    state[uid] = {
        "mode": "idle", "idx": 0, "correct": 0, "wrong": 0,
        "total": 0, "current_q": None, "timestamp": 0.0
    }

def pick_random_question() -> Optional[Dict[str, Any]]:
    if not QUESTIONS:
        return None
    return random.choice(QUESTIONS)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, q: Dict[str, Any]):
    txt = f"❓ سؤال #{q.get('id','')}\n\n{q['question']}\n\n"
    for i, ch in enumerate(q["choices"], start=1):
        txt += f"{i}) {ch}\n"
    await update.message.reply_text(txt.strip(), reply_markup=CHOICE_KB)

def evaluate_answer(q: Dict[str, Any], user_text: str) -> (bool, str):
    # يقبل الرقم (1-4) أو النص الكامل
    ans_idx = q["answer_index"]
    correct_val = q["choices"][ans_idx]
    user_text = user_text.strip()
    ok = False
    if user_text.isdigit():
        ok = (int(user_text) - 1) == ans_idx
    else:
        ok = (user_text == str(correct_val))
    exp = q.get("explanation", "")
    if ok:
        return True, f"✅ صحيحة! {('— ' + exp) if exp else ''}".strip()
    else:
        return False, f"❌ خاطئة.\nالصحيح: {correct_val}\n{exp}".strip()

def score_line(s: Dict[str, Any]) -> str:
    total = s.get("total", 0)
    c = s.get("correct", 0)
    w = s.get("wrong", 0)
    pct = round((c / total) * 100, 2) if total else 0.0
    return f"📊 نتيجتك: صحيحة {c} — خاطئة {w} — النسبة {pct}%"

# ======== Telegram Handlers ========
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    reset_progress(uid)
    await update.message.reply_text(
        f"أهلًا 👋 أنا {BOT_NAME}.\nاختر من القائمة:",
        reply_markup=MAIN_KB
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "الأوامر:\n"
        "/start — القائمة الرئيسية\n"
        "/help — المساعدة\n"
        "أو استخدم الأزرار: 🎯 اختبر نفسك، 🧮 جدول الضرب، 🧠 اسأل قياس، 📊 نتيجتي، 🔁 إعادة",
        reply_markup=MAIN_KB
    )

async def show_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in state:
        reset_progress(uid)
    await update.message.reply_text(score_line(state[uid]), reply_markup=MAIN_KB)

async def handle_main_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """يرجع True إذا تمت المعالجة هنا."""
    uid = update.effective_user.id
    txt = (update.message.text or "").strip()

    if txt == "🔁 إعادة":
        reset_progress(uid)
        await update.message.reply_text("تمت الإعادة. اختر وضعًا:", reply_markup=MAIN_KB)
        return True

    if txt == "📊 نتيجتي":
        await show_score(update, context)
        return True

    if txt == "🎯 اختبر نفسك":
        if not QUESTIONS:
            await update.message.reply_text("لا يوجد بنك أسئلة (data.json غير متاح أو فيه خطأ).", reply_markup=MAIN_KB)
            return True
        if uid not in state:
            reset_progress(uid)
        s = state[uid]
        s["mode"] = "quiz"
        q = pick_random_question()
        s["current_q"] = q
        s["total"] += 1
        s["idx"] += 1
        state[uid] = s
        await update.message.reply_text("بدأ الاختبار — اختر الإجابة الصحيحة:", reply_markup=CHOICE_KB)
        await send_question(update, context, q)
        return True

    if txt == "🧮 جدول الضرب":
        if uid not in state:
            reset_progress(uid)
        s = state[uid]
        s["mode"] = "table"
        # سؤال عشوائي 2..12
        a, b = random.randint(2, 12), random.randint(2, 12)
        s["current_q"] = {"id": None, "question": f"{a} × {b} = ?", "choices": [], "answer_index": None, "answer": a*b}
        s["total"] += 1
        s["idx"] += 1
        state[uid] = s
        await update.message.reply_text(f"❓ {a} × {b} = ?", reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("🔙 رجوع")]], resize_keyboard=True))
        return True

    if txt == "🧠 اسأل قياس (ذكاء اصطناعي)":
        if uid not in state:
            reset_progress(uid)
        s = state[uid]
        s["mode"] = "ai"
        state[uid] = s
        await update.message.reply_text("أرسل سؤالك التعليمي وسأجيبك.", reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("🔙 رجوع")]], resize_keyboard=True))
        return True

    if txt == "🔙 رجوع":
        if uid not in state:
            reset_progress(uid)
        s = state[uid]
        s["mode"] = "idle"
        s["current_q"] = None
        state[uid] = s
        await update.message.reply_text("رجعناك للقائمة الرئيسية:", reply_markup=MAIN_KB)
        return True

    return False

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    uid = update.effective_user.id
    if uid not in state:
        reset_progress(uid)

    # مانع سبام بسيط
    if not cooldown_ok(uid):
        return

    # أزرار رئيسية
    if await handle_main_buttons(update, context):
        return

    s = state[uid]
    mode = s.get("mode", "idle")
    txt = (update.message.text or "").strip()

    # === وضع الاختبار من data.json ===
    if mode == "quiz":
        q = s.get("current_q")
        if not q:
            await update.message.reply_text("اكتب: 🎯 اختبر نفسك لبدء سؤال.", reply_markup=MAIN_KB)
            return
        ok, msg = evaluate_answer(q, txt)
        if ok:
            s["correct"] += 1
        else:
            s["wrong"] += 1
        state[uid] = s
        await update.message.reply_text(msg)
        # سؤال جديد تلقائي
        q2 = pick_random_question()
        s["current_q"] = q2
        s["total"] += 1
        s["idx"] += 1
        state[uid] = s
        await send_question(update, context, q2)
        return

    # === وضع جدول الضرب ===
    if mode == "table":
        q = s.get("current_q")
        if not q:
            await update.message.reply_text("اختر 🧮 جدول الضرب للبدء.", reply_markup=MAIN_KB)
            return
        # يقبل رقم المستخدم
        if not txt.isdigit():
            await update.message.reply_text("اكتب الناتج كرقم صحيح أو اضغط 🔙 رجوع.")
            return
        user_val = int(txt)
        correct = int(q["answer"])
        if user_val == correct:
            s["correct"] += 1
            await update.message.reply_text("✅ صحيح! ممتاز.")
        else:
            s["wrong"] += 1
            await update.message.reply_text(f"❌ خاطئ. الصحيح: {correct}")
        # سؤال ضرب جديد
        a, b = random.randint(2, 12), random.randint(2, 12)
        s["current_q"] = {"id": None, "question": f"{a} × {b} = ?", "choices": [], "answer_index": None, "answer": a*b}
        s["total"] += 1
        s["idx"] += 1
        state[uid] = s
        await update.message.reply_text(f"❓ {a} × {b} = ?")
        return

    # === وضع الذكاء الاصطناعي ===
    if mode == "ai":
        reply = await ai_reply(txt)
        await update.message.reply_text(reply)
        return

    # === الوضع الافتراضي ===
    await update.message.reply_text("اختر من القائمة:", reply_markup=MAIN_KB)

# ======== Flask + Webhook ========
app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()
# نعيد ربط الهاندلرز بعد تعريفها
application.add_handler(CommandHandler("start", cmd_start))
application.add_handler(CommandHandler("help", cmd_help))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)
        application.update_queue.put(update)
    except Exception as e:
        print("Webhook error:", e)
    return "ok", 200

@app.get("/")
def index():
    return f"{BOT_NAME} bot is running", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
