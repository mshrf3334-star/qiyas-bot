import os, json, random
from typing import List, Dict, Optional

from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# ========== تحميل الأسئلة وتهيئتها ==========
def _try_read_json(paths: list[str]) -> Optional[list]:
    for p in paths:
        try:
            if p and os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list) and data:
                    print(f"[INFO] Loaded questions from: {p}")
                    return data
        except Exception as e:
            print(f"[WARN] Failed to read {p}: {e}")
    return None

def load_questions() -> List[Dict]:
    """
    يدعم شكلين للمدخلات:
    1) {"question": "...", "choices": [...], "answer_index": 1, "explanation": "..."}
    2) {"question": "...", "options":  [...], "answer":        "...", "explanation": "..."}
    ويُرجع قائمة موحّدة: {"id","q","choices","correct","explanation"}
    """
    # مسارات محتملة: متغير بيئة, داخل المشروع, Secret Files في Render
    env_path = os.getenv("DATA_PATH")
    candidates = [
        env_path,
        "data.json",
        "data/data.json",
        "/etc/secrets/data.json",
        "/etc/secrets/data",  # في حال سُمي الملف "data" بدون امتداد
    ]
    raw = _try_read_json([p for p in candidates if p])

    # في حال ما وجدنا ملف، نضع عيّنة بسيطة بدل التعطّل
    if not raw:
        print("[WARN] No data.json found. Using fallback sample questions.")
        raw = [
            {
                "id": 1,
                "question": "٢ + ٢ = ؟",
                "choices": ["3", "4", "5"],
                "answer_index": 1,
                "explanation": "معلومة أساسية في الجمع."
            },
            {
                "id": 2,
                "question": "عاصمة السعودية؟",
                "options": ["جدة", "الرياض", "مكة"],
                "answer": "الرياض"
            }
        ]

    norm: List[Dict] = []
    for i, item in enumerate(raw, start=1):
        qtxt = item.get("question") or item.get("q") or ""
        choices = item.get("choices") or item.get("options") or []

        # تنظيف الخيارات من الفراغات
        choices = [str(c).strip() for c in choices if str(c).strip()]

        # تحديد الصحيح
        correct = ""
        if "answer_index" in item and choices:
            try:
                correct = choices[int(item["answer_index"])]
            except Exception:
                correct = ""
        if not correct:
            correct = (item.get("answer") or "").strip()

        # لو ما فيه خيارات لكن عندنا إجابة، خلّ الخيار الوحيد هو الإجابة
        if not choices and correct:
            choices = [correct]

        if not qtxt or not choices:
            # تخطّي العناصر غير الصالحة بدل ما يطيح البوت
            print(f"[WARN] Skipped invalid question at index {i}")
            continue

        norm.append({
            "id": str(item.get("id", i)),
            "q": qtxt,
            "choices": choices,
            "correct": correct,
            "explanation": (item.get("explanation") or "").strip()
        })
    return norm

QUESTIONS: List[Dict] = load_questions()

# ========== أدوات مساعدة ==========
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

def _pick_next_question(context: ContextTypes.DEFAULT_TYPE) -> Optional[Dict]:
    asked = context.user_data.get("asked_ids")
    if not isinstance(asked, set):
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

# ========== القائمة ==========
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_menu(update, context)

async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pong ✅")

async def menu_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    # جلسة جديدة
    context.user_data["mode"] = "quiz"
    context.user_data["asked_ids"] = set()
    nxt = _pick_next_question(context)
    if not nxt:
        await q.edit_message_text("لا توجد أسئلة حالياً.")
        return
    await q.edit_message_text(text=f"📝 سؤال:\n{nxt['q']}",
                              reply_markup=_question_markup(nxt))

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

# ========== اختبار قياس ==========
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
    is_correct = (chosen_text == current["correct"]) if current["correct"] else False

    prefix = "✅ صحيح!" if is_correct else "❌ خطأ."
    explanation = ""
    if current.get("correct"):
        explanation += f"\n\nالجواب الصحيح: {current['correct']}"
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
    await q.edit_message_text(text=f"📝 سؤال:\n{nxt['q']}",
                              reply_markup=_question_markup(nxt))

# ========== جدول الضرب & الذكاء ==========
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

    if mode == "ai":
        question = (update.message.text or "").strip()
        api_key = os.getenv("AI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                # OpenAI SDK الرسمي (>=1.0)
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                model = os.getenv("AI_MODEL", "gpt-4o-mini")
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "أجب باختصار وبالعربية."},
                        {"role": "user", "content": question},
                    ],
                    temperature=0.4,
                    max_tokens=400,
                )
                answer = (resp.choices[0].message.content or "").strip()
                if not answer:
                    answer = "لم يصلني رد من النموذج."
                await update.message.reply_text(answer)
                return
            except Exception as e:
                print(f"[WARN] OpenAI error: {e}")
        await update.message.reply_text("🤖 ميزة الذكاء الاصطناعي غير مفعلة حالياً. أضف AI_API_KEY ثم جرّب.")
        return

    # أي نص خارج الأوضاع يرجّع للقائمة
    await update.message.reply_text("اختر من القائمة:", reply_markup=_make_menu_kb())

# ========== البداية والويبهوك ==========
def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN غير موجود في المتغيرات.")

    app = Application.builder().token(token).build()

    # أوامر وقائمة
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("ping", ping_cmd))
    app.add_handler(CallbackQueryHandler(menu_quiz, pattern="^menu_quiz$"))
    app.add_handler(CallbackQueryHandler(menu_mult, pattern="^menu_mult$"))
    app.add_handler(CallbackQueryHandler(menu_ai, pattern="^menu_ai$"))
    app.add_handler(CallbackQueryHandler(show_menu, pattern="^menu_home$"))

    # اختبار
    app.add_handler(CallbackQueryHandler(quiz_answer, pattern=r"^quiz_ans:\d+$"))
    app.add_handler(CallbackQueryHandler(quiz_next, pattern=r"^quiz_next$"))

    # نصوص عامة
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    # Webhook على Render
    external = os.getenv("RENDER_EXTERNAL_URL")  # Render يضبطه تلقائياً
    port = int(os.getenv("PORT", "10000"))
    if external:
        # يثبت الويبهوك تلقائياً
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=token,
            webhook_url=f"{external.rstrip('/')}/{token}",
        )
    else:
        print("Running in polling (no RENDER_EXTERNAL_URL found)")
        app.run_polling()

if __name__ == "__main__":
    main()
