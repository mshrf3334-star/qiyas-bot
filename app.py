# -*- coding: utf-8 -*-
"""
بوت قياس — Telegram + Render
يشمل:
- قائمة رئيسية (جدول الضرب • الذكاء الاصطناعي • اختبر نفسك)
- بنك أسئلة من data.json (يدعم صيغ متعددة)
- تشغيلتين: Polling أو Webhook عبر Flask
- مسار صحي لِـ Render "/"
- متغيرات البيئة: TELEGRAM_BOT_TOKEN, MODE, PORT, AI_API_KEY/OPENAI_API_KEY, AI_MODEL, WEBHOOK_URL
"""

import os, json, random, logging, asyncio
from typing import List, Dict, Optional

# Telegram Bot API (python-telegram-bot v20+)
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# Flask لاستقبال الويبهوك وعمل health check على Render
from flask import Flask, request, jsonify

# =======================================
# الإعدادات العامة + اللوجينغ
# =======================================
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("qiyas-bot")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
AI_KEY = (os.getenv("AI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini").strip()
PORT = int(os.getenv("PORT", "10000"))
MODE = os.getenv("MODE", "polling").strip().lower()   # polling | webhook
PUBLIC_URL = (
    os.getenv("WEBHOOK_URL")
    or os.getenv("RENDER_EXTERNAL_URL")
    or os.getenv("PUBLIC_URL")
    or ""
).strip()

if not TELEGRAM_TOKEN:
    raise RuntimeError("⚠️ TELEGRAM_BOT_TOKEN غير موجود في المتغيرات.")

# =======================================
# بنك الأسئلة من data.json
# =======================================
def load_questions(path: str = "data.json") -> List[Dict]:
    """
    يدعم شكلين:
    1) {"question": "...", "choices": [...], "answer_index": 1, "explanation": "..."}
    2) {"question": "...", "options":  [...], "answer":        "...", "explanation": "..."}
    ويُرجع قائمة موحّدة:
       {"id","q","choices","correct","explanation"}
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        log.warning("⚠️ لم يتم العثور على data.json — سيتم تشغيل البوت بدون أسئلة.")
        return []

    norm: List[Dict] = []
    for i, item in enumerate(raw, start=1):
        qtxt = item.get("question") or item.get("q") or ""
        choices = item.get("choices") or item.get("options") or []
        if not choices and "answer" in item:
            choices = [item["answer"]]
        if "answer_index" in item and isinstance(item["answer_index"], int) and 0 <= item["answer_index"] < len(choices):
            correct = choices[item["answer_index"]]
        else:
            correct = item.get("answer", choices[0] if choices else "")
        norm.append({
            "id": str(item.get("id", i)),
            "q": qtxt,
            "choices": choices,
            "correct": correct,
            "explanation": item.get("explanation", "")
        })
    return norm

QUESTIONS: List[Dict] = load_questions("data.json")

# =======================================
# واجهة القائمة الرئيسية
# =======================================
def _make_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 جدول الضرب", callback_data="menu_mult")],
        [InlineKeyboardButton("🤖 الذكاء الاصطناعي", callback_data="menu_ai")],
        [InlineKeyboardButton("📝 قياس: اختبر نفسك", callback_data="menu_quiz")],
    ])

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        q = update.callback_query
        await q.answer()
        await q.edit_message_text("اختر من القائمة:", reply_markup=_make_menu_kb())
    else:
        await update.message.reply_text("👋 مرحباً! اختر من القائمة:", reply_markup=_make_menu_kb())

# =======================================
# منطق بنك الأسئلة
# =======================================
def _pick_next_question(context: ContextTypes.DEFAULT_TYPE) -> Optional[Dict]:
    asked = context.user_data.get("asked_ids")
    if asked is None:
        asked = set()
    remaining = [q for q in QUESTIONS if q["id"] not in asked]
    if not remaining:
        return None
    q = random.choice(remaining)
    asked.add(q["id"])
    context.user_data["asked_ids"] = asked
    context.user_data["current_q"] = q
    return q

def _question_markup(q: Dict) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(choice, callback_data=f"quiz_ans:{idx}")]
               for idx, choice in enumerate(q["choices"])]
    return InlineKeyboardMarkup(buttons)

# =======================================
# Handlers القائمة
# =======================================
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_menu(update, context)

async def menu_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["asked_ids"] = set()
    nxt = _pick_next_question(context)
    if not nxt:
        await q.edit_message_text("لا توجد أسئلة حالياً.")
        return
    await q.edit_message_text(text=f"📝 سؤال: {nxt['q']}", reply_markup=_question_markup(nxt))

async def menu_mult(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["mode"] = "mult"
    await q.edit_message_text("أرسل رقمًا (مثال: 7) وسأعرض لك جدول ضربه 1..12.\n\nللرجوع للقائمة: /start")

async def menu_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["mode"] = "ai"
    await q.edit_message_text("اكتب سؤالك للذكاء الاصطناعي.\n\nللرجوع للقائمة: /start")

# =======================================
# اختبار قياس: التحقق والإكمال
# =======================================
async def quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    current = context.user_data.get("current_q")
    if not current:
        await q.edit_message_text("انتهت الجلسة. اضغط /start للعودة للقائمة.")
        return

    try:
        chosen_idx = int(q.data.split(":")[1])
    except Exception:
        chosen_idx = -1

    chosen_text = current["choices"][chosen_idx] if 0 <= chosen_idx < len(current["choices"]) else ""
    is_correct = (chosen_text == current["correct"])

    prefix = "✅ صحيح!" if is_correct else "❌ خطأ."
    explanation = f"\n\nالجواب الصحيح: {current['correct']}"
    if current.get("explanation"):
        explanation += f"\nالشرح: {current['explanation']}"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ السؤال التالي", callback_data="quiz_next")],
        [InlineKeyboardButton("🏠 القائمة", callback_data="menu_home")]
    ])
    await q.edit_message_text(f"{prefix}{explanation}", reply_markup=kb)

async def quiz_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    nxt = _pick_next_question(context)
    if not nxt:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 العودة للقائمة", callback_data="menu_home")]])
        await q.edit_message_text("انتهت الأسئلة! أحسنت 👏", reply_markup=kb)
        return
    await q.edit_message_text(text=f"📝 سؤال: {nxt['q']}", reply_markup=_question_markup(nxt))

# =======================================
# جدول الضرب + الذكاء الاصطناعي
# =======================================
def _make_table(n: int) -> str:
    lines = [f"{i} × {n} = {i*n}" for i in range(1, 13)]
    return "📚 جدول الضرب\n" + "\n".join(lines)

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    if mode == "mult":
        txt = (update.message.text or "").strip()
        if not txt.lstrip("-").isdigit():
            await update.message.reply_text("أرسل رقمًا صحيحًا فقط، مثال: 7")
            return
        n = int(txt)
        await update.message.reply_text(_make_table(n))
        return
    elif mode == "ai":
        question = (update.message.text or "").strip()
        if not question:
            return
        if AI_KEY:
            try:
                # مكتبة openai الجديدة (>=1.0)
                from openai import OpenAI
                client = OpenAI(api_key=AI_KEY)
                resp = client.chat.completions.create(
                    model=AI_MODEL,
                    messages=[
                        {"role": "system", "content": "أجب باختصار وبالعربية."},
                        {"role": "user", "content": question},
                    ],
                    temperature=0.4,
                    max_tokens=400,
                )
                answer = resp.choices[0].message.content.strip()
                await update.message.reply_text(answer)
                return
            except Exception as e:
                log.exception("AI error: %s", e)
        await update.message.reply_text("🤖 ميزة الذكاء الاصطناعي غير مفعلة حالياً. أضف AI_API_KEY ثم جرّب.")
        return
    else:
        await update.message.reply_text("اختر من القائمة:", reply_markup=_make_menu_kb())

# =======================================
# إنشاء تطبيق التيليجرام
# =======================================
def build_telegram_app() -> Application:
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # أوامر وقائمة
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CallbackQueryHandler(menu_quiz, pattern="^menu_quiz$"))
    application.add_handler(CallbackQueryHandler(menu_mult, pattern="^menu_mult$"))
    application.add_handler(CallbackQueryHandler(menu_ai, pattern="^menu_ai$"))
    application.add_handler(CallbackQueryHandler(show_menu, pattern="^menu_home$"))

    # اختبار
    application.add_handler(CallbackQueryHandler(quiz_answer, pattern=r"^quiz_ans:\d+$"))
    application.add_handler(CallbackQueryHandler(quiz_next, pattern=r"^quiz_next$"))

    # نصوص عامة
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    return application

telegram_app: Application = build_telegram_app()

# =======================================
# Flask (للويبهوك + Health Check)
# =======================================
flask_app = Flask(__name__)

@flask_app.get("/")
def health_root():
    return "OK ✅", 200

@flask_app.post("/webhook")
def webhook_receiver():
    """
    يستقبل تحديثات تيليجرام (Webhook).
    لكي يعمل: عيّن MODE=webhook و WEBHOOK_URL (أو تعتمد على RENDER_EXTERNAL_URL)
    ثم سيتم استدعاء /webhook من تيليجرام.
    """
    try:
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        # تمرير التحديث إلى PTB (يحتاج loop يعمل)
        asyncio.get_event_loop().create_task(telegram_app.process_update(update))
        return jsonify(ok=True)
    except Exception as e:
        log.exception("webhook error: %s", e)
        return jsonify(ok=False, error=str(e)), 500

# =======================================
# التشغيل
# =======================================
async def _set_webhook_if_needed():
    """يضبط Webhook في وضع الويبهوك."""
    if MODE != "webhook":
        return
    if not PUBLIC_URL:
        log.warning("⚠️ MODE=webhook لكن لم يُحدد PUBLIC_URL/RENDER_EXTERNAL_URL/WEBHOOK_URL.")
        return
    url = PUBLIC_URL.rstrip("/") + "/webhook"
    try:
        await telegram_app.bot.set_webhook(url)
        log.info("✅ Webhook set to: %s", url)
    except Exception as e:
        log.exception("Failed to set webhook: %s", e)

def run_polling():
    """تشغيل البوت بالـPolling (لا يحتاج استقبال HTTP من تيليجرام)."""
    log.info("🚀 Starting Telegram polling...")
    telegram_app.run_polling(close_loop=False)  # لا تغلق اللوب؛ ليسمح لـ Flask إن احتجنا

def run_webhook():
    """
    تشغيل Flask (ليستمع على $PORT) + حدث التيليجرام داخل نفس العملية.
    في Render استخدم Gunicorn:
        Procfile: web: gunicorn app:flask_app --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 120
    أو Start Command:
        gunicorn app:flask_app --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 120
    """
    # تأكيد ضبط الويبهوك
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_set_webhook_if_needed())

    log.info("🌐 Starting Flask on port %s (webhook mode)", PORT)
    # تشغيل Flask (Blocking)
    flask_app.run(host="0.0.0.0", port=PORT)

def main():
    if MODE == "webhook":
        # مخصص لـ Render + Gunicorn
        run_webhook()
    else:
        # أسهل: تشغيل مباشر
        run_polling()

if __name__ == "__main__":
    main()
