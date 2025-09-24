import os, json, random
from typing import List, Dict

from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# ====== تحميل الأسئلة من data.json ======
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

QUESTIONS = load_questions()

# ====== القوائم الرئيسية ======
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

# ====== جدول الضرب ======
def _make_table(n: int) -> str:
    lines = [f"{i} × {n} = {i*n}" for i in range(1, 13)]
    return "📚 جدول الضرب\n" + "\n".join(lines)

# ====== الذكاء الاصطناعي ======
async def ai_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["mode"] = "ai"
    await q.edit_message_text("اكتب سؤالك للذكاء الاصطناعي.\n\nللرجوع للقائمة: /start")

# ====== اختبر نفسك ======
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

def _question_markup(q: Dict) -> InlineKeyboardMarkup:
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
    await q.edit_message_text(
        text=f"📝 سؤال: {nxt['q']}",
        reply_markup=_question_markup(nxt)
    )

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

    chosen_text = ""
    if 0 <= chosen_idx < len(current["choices"]):
        chosen_text = current["choices"][chosen_idx]

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
        await q.edit_message_text("انتهت الأسئلة! 👏", reply_markup=kb)
        return
    await q.edit_message_text(text=f"📝 سؤال: {nxt['q']}", reply_markup=_question_markup(nxt))

# ====== موجه النصوص ======
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    txt = (update.message.text or "").strip()
    if mode == "mult":
        if not txt.isdigit():
            await update.message.reply_text("أرسل رقمًا صحيحًا فقط.")
            return
        n = int(txt)
        await update.message.reply_text(_make_table(n))
    elif mode == "ai":
        await update.message.reply_text("🤖 ميزة الذكاء الاصطناعي مفعلة فقط بمفتاح API.")
    else:
        await update.message.reply_text("ارجع للقائمة:", reply_markup=_make_menu_kb())

# ====== البداية ======
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_menu(update, context)

async def menu_mult(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["mode"] = "mult"
    await q.edit_message_text("أرسل رقمًا (مثال: 7) وسأعرض جدول ضربه.\n\nللرجوع: /start")

async def menu_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_menu(update, context)

# ====== Main ======
def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN غير موجود!")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CallbackQueryHandler(menu_quiz, pattern="^menu_quiz$"))
    app.add_handler(CallbackQueryHandler(menu_mult, pattern="^menu_mult$"))
    app.add_handler(CallbackQueryHandler(ai_answer, pattern="^menu_ai$"))
    app.add_handler(CallbackQueryHandler(menu_home, pattern="^menu_home$"))
    app.add_handler(CallbackQueryHandler(quiz_answer, pattern=r"^quiz_ans:\d+$"))
    app.add_handler(CallbackQueryHandler(quiz_next, pattern=r"^quiz_next$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    app.run_polling()

if __name__ == "__main__":
    main()
