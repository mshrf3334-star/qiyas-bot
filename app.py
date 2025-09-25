import os
import logging
import json
import random
from typing import List, Dict, Optional

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# -----------------------------
# إعداد اللوق للتصحيح
# -----------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# -----------------------------
# التحقق من المتغيرات
# -----------------------------
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AI_KEY = os.getenv("AI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")

if not BOT_TOKEN:
    raise RuntimeError("❌ TELEGRAM_BOT_TOKEN غير موجود في متغيرات البيئة.")
if not AI_KEY:
    logging.warning("⚠️ AI_API_KEY غير موجود. ميزة الذكاء الاصطناعي ستتعطل.")

# -----------------------------
# تحميل الأسئلة من data.json
# -----------------------------
def load_questions(path: str = "data.json") -> List[Dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    norm = []
    for i, item in enumerate(raw, start=1):
        qtxt = item.get("question") or item.get("q") or ""
        choices = item.get("choices") or item.get("options") or []
        if not choices and "answer" in item:
            choices = [item["answer"]]
        if "answer_index" in item and 0 <= item["answer_index"] < len(choices):
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

QUESTIONS = load_questions("data.json")

# -----------------------------
# القائمة الرئيسية
# -----------------------------
def _make_menu_kb() -> InlineKeyboardMarkup:
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

# -----------------------------
# منطق بنك الأسئلة
# -----------------------------
def _pick_next_question(context: ContextTypes.DEFAULT_TYPE) -> Optional[Dict]:
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
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(choice, callback_data=f"quiz_ans:{idx}")]
         for idx, choice in enumerate(q["choices"])]
    )

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
        await q.edit_message_text("انتهت الجلسة. اضغط /start للرجوع للقائمة.")
        return

    chosen_idx = int(q.data.split(":")[1])
    chosen_text = current["choices"][chosen_idx]
    is_correct = (chosen_text == current["correct"])
    msg = "✅ صحيح!" if is_correct else "❌ خطأ."
    msg += f"\n\nالجواب الصحيح: {current['correct']}"
    if current.get("explanation"):
        msg += f"\nالشرح: {current['explanation']}"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ السؤال التالي", callback_data="quiz_next")],
        [InlineKeyboardButton("🏠 القائمة", callback_data="menu_home")]
    ])
    await q.edit_message_text(msg, reply_markup=kb)

async def quiz_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    nxt = _pick_next_question(context)
    if not nxt:
        await q.edit_message_text("انتهت الأسئلة! 👏", reply_markup=_make_menu_kb())
        return
    await q.edit_message_text(f"📝 سؤال: {nxt['q']}", reply_markup=_question_markup(nxt))

# -----------------------------
# جدول الضرب + الذكاء الاصطناعي
# -----------------------------
def _make_table(n: int) -> str:
    return "\n".join([f"{i} × {n} = {i*n}" for i in range(1, 13)])

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    txt = update.message.text.strip()

    if mode == "mult":
        if not txt.isdigit():
            await update.message.reply_text("أرسل رقم صحيح مثال: 7")
            return
        n = int(txt)
        await update.message.reply_text(_make_table(n))
    elif mode == "ai":
        if not AI_KEY:
            await update.message.reply_text("🤖 ميزة الذكاء الاصطناعي غير مفعلة.")
            return
        try:
            from openai import OpenAI
            client = OpenAI(api_key=AI_KEY)
            resp = client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": "أجب بإيجاز وبالعربية"},
                    {"role": "user", "content": txt},
                ],
                max_tokens=300,
            )
            answer = resp.choices[0].message.content.strip()
            await update.message.reply_text(answer)
        except Exception as e:
            await update.message.reply_text(f"خطأ: {e}")
    else:
        await update.message.reply_text("اختر من القائمة:", reply_markup=_make_menu_kb())

# -----------------------------
# نقطة تشغيل
# -----------------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CallbackQueryHandler(menu_quiz, pattern="^menu_quiz$"))
    app.add_handler(CallbackQueryHandler(quiz_answer, pattern=r"^quiz_ans:\d+$"))
    app.add_handler(CallbackQueryHandler(quiz_next, pattern="^quiz_next$"))
    app.add_handler(CallbackQueryHandler(show_menu, pattern="^menu_home$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    port = int(os.getenv("PORT", "10000"))
    external = os.getenv("RENDER_EXTERNAL_URL")

    if external:
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=BOT_TOKEN,
            webhook_url=f"https://{external}/{BOT_TOKEN}",
        )
    else:
        app.run_polling()

if __name__ == "__main__":
    main()
