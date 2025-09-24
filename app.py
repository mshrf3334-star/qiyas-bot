import os, json, random
from typing import List, Dict
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# ====== تحميل الأسئلة ======
def load_questions(path: str = "data.json") -> List[Dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    norm = []
    for i, item in enumerate(raw, start=1):
        qtxt = item.get("question") or item.get("q") or ""
        choices = item.get("choices") or item.get("options") or []
        if "answer_index" in item:
            correct = choices[item["answer_index"]]
        else:
            correct = item.get("answer", "")
        norm.append({
            "id": str(item.get("id", i)),
            "q": qtxt,
            "choices": choices,
            "correct": correct,
            "explanation": item.get("explanation", "")
        })
    return norm

QUESTIONS: List[Dict] = load_questions()

# ====== القوائم ======
def _make_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 جدول الضرب", callback_data="menu_mult")],
        [InlineKeyboardButton("🤖 الذكاء الاصطناعي", callback_data="menu_ai")],
        [InlineKeyboardButton("📝 قياس: اختبر نفسك", callback_data="menu_quiz")],
    ])

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 مرحباً! اختر من القائمة:", reply_markup=_make_menu_kb())

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("اختر من القائمة:", reply_markup=_make_menu_kb())

# ====== جدول الضرب ======
def _make_table(n: int) -> str:
    lines = [f"{i} × {n} = {i*n}" for i in range(1, 13)]
    return "📚 جدول الضرب\n" + "\n".join(lines)

async def menu_mult(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["mode"] = "mult"
    await q.edit_message_text("أرسل رقمًا (مثال: 7) وسأعرض لك جدول ضربه.\n\nللرجوع: /start")

# ====== الذكاء الاصطناعي ======
async def menu_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["mode"] = "ai"
    await q.edit_message_text("اكتب سؤالك للذكاء الاصطناعي.\n\nللرجوع: /start")

# ====== اختبار قياس ======
def _pick_next_question(context: ContextTypes.DEFAULT_TYPE) -> Dict | None:
    asked = context.user_data.get("asked_ids", set())
    remaining = [q for q in QUESTIONS if q["id"] not in asked]
    if not remaining:
        return None
    q = random.choice(remaining)
    asked.add(q["id"])
    context.user_data["asked_ids"] = asked
    context.user_data["current_q"] = q
    return q

def _question_markup(q: Dict):
    buttons = []
    for idx, choice in enumerate(q["choices"]):
        buttons.append([InlineKeyboardButton(choice, callback_data=f"quiz_ans:{idx}")])
    return InlineKeyboardMarkup(buttons)

async def menu_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["asked_ids"] = set()
    nxt = _pick_next_question(context)
    if not nxt:
        await q.edit_message_text("لا توجد أسئلة حالياً.")
        return
    await q.edit_message_text(f"📝 سؤال: {nxt['q']}", reply_markup=_question_markup(nxt))

async def quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    current = context.user_data.get("current_q")
    if not current:
        await q.edit_message_text("انتهت الجلسة. اضغط /start للعودة للقائمة.")
        return
    chosen_idx = int(q.data.split(":")[1])
    chosen_text = current["choices"][chosen_idx]
    is_correct = (chosen_text == current["correct"])
    prefix = "✅ صحيح!" if is_correct else "❌ خطأ."
    explanation = f"\n\nالجواب الصحيح: {current['correct']}"
    if current.get("explanation"):
        explanation += f"\nالشرح: {current['explanation']}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ التالي", callback_data="quiz_next")],
        [InlineKeyboardButton("🏠 القائمة", callback_data="menu_home")]
    ])
    await q.edit_message_text(f"{prefix}{explanation}", reply_markup=kb)

async def quiz_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    nxt = _pick_next_question(context)
    if not nxt:
        await q.edit_message_text("انتهت الأسئلة 👏", reply_markup=_make_menu_kb())
        return
    await q.edit_message_text(f"📝 سؤال: {nxt['q']}", reply_markup=_question_markup(nxt))

# ====== راوتر النصوص ======
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    if mode == "mult":
        txt = update.message.text.strip()
        if not txt.isdigit():
            await update.message.reply_text("أرسل رقمًا صحيحًا مثال: 7")
            return
        await update.message.reply_text(_make_table(int(txt)))
    elif mode == "ai":
        question = update.message.text.strip()
        api_key = os.getenv("AI_API_KEY")
        if api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                resp = client.chat.completions.create(
                    model=os.getenv("AI_MODEL", "gpt-4o-mini"),
                    messages=[
                        {"role": "system", "content": "أجب بالعربية وباختصار"},
                        {"role": "user", "content": question}
                    ]
                )
                await update.message.reply_text(resp.choices[0].message.content.strip())
                return
            except Exception as e:
                await update.message.reply_text(f"خطأ بالذكاء الاصطناعي: {e}")
        else:
            await update.message.reply_text("🤖 أضف AI_API_KEY لتفعيل الذكاء الاصطناعي.")
    else:
        await update.message.reply_text("اختر من القائمة:", reply_markup=_make_menu_kb())

# ====== البداية ======
def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("لا يوجد TELEGRAM_BOT_TOKEN")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CallbackQueryHandler(menu_mult, pattern="^menu_mult$"))
    app.add_handler(CallbackQueryHandler(menu_ai, pattern="^menu_ai$"))
    app.add_handler(CallbackQueryHandler(menu_quiz, pattern="^menu_quiz$"))
    app.add_handler(CallbackQueryHandler(show_menu, pattern="^menu_home$"))
    app.add_handler(CallbackQueryHandler(quiz_answer, pattern=r"^quiz_ans:\d+$"))
    app.add_handler(CallbackQueryHandler(quiz_next, pattern="^quiz_next$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    port = int(os.getenv("PORT", "10000"))
    url = os.getenv("RENDER_EXTERNAL_URL")
    if url:
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=token,
            webhook_url=f"https://{url}/{token}"
        )
    else:
        app.run_polling()

if __name__ == "__main__":
    main()
