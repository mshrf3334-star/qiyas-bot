# cognitive_questions.py — أزرار آمنة بـ CallbackQuery
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import random

# أمثلة — يمكنك تكبير القائمة لاحقًا
QUESTIONS = [
    {"q": "ما هو حاصل ضرب 7 × 8؟", "options": ["54", "56", "63", "49"], "answer_idx": 1},
    {"q": "إذا كان لديك 5 تفاحات وأكلت 2، فكم تبقى؟", "options": ["2", "3", "4", "5"], "answer_idx": 1},
    {"q": "ما هو اليوم الذي يأتي بعد الأربعاء؟", "options": ["الثلاثاء", "الخميس", "الجمعة", "السبت"], "answer_idx": 1},
    {"q": "أي من هذه الحيوانات يبيض؟", "options": ["القطة", "الكلب", "الدجاجة", "البقرة"], "answer_idx": 2},
    {"q": "ما هو لون السماء في يوم صافٍ؟", "options": ["أخضر", "أحمر", "أزرق", "أصفر"], "answer_idx": 2},
]

def _ensure_quiz(context: ContextTypes.DEFAULT_TYPE) -> dict:
    if "cog_quiz" not in context.user_data:
        context.user_data["cog_quiz"] = {
            "score": 0,
            "idx": 0,
            "qs": random.sample(QUESTIONS, min(5, len(QUESTIONS))),
        }
    return context.user_data["cog_quiz"]

async def start_cognitive_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("cog_quiz", None)
    _ensure_quiz(context)
    await _send_cog_question(update, context)

async def _send_cog_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = _ensure_quiz(context)
    if q["idx"] >= len(q["qs"]):
        await update.effective_message.reply_text(
            f"انتهى الاختبار! نتيجتك: {q['score']} من {len(q['qs'])}."
        )
        context.user_data.pop("cog_quiz", None)
        return

    cur = q["qs"][q["idx"]]
    buttons = [
        [InlineKeyboardButton(opt, callback_data=f"cog|{i}")]
        for i, opt in enumerate(cur["options"])
    ]
    await update.effective_message.reply_text(
        f"السؤال {q['idx']+1}: {cur['q']}",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

async def handle_cognitive_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = _ensure_quiz(context)
    query = update.callback_query
    await query.answer()

    # إذا فُقدت الحالة بعد إعادة تشغيل البوت
    if q["idx"] >= len(q["qs"]):
        await query.edit_message_text("الجلسة انتهت. ارسل «اختبر قدراتك (500 سؤال)» للبدء من جديد.")
        context.user_data.pop("cog_quiz", None)
        return

    cur = q["qs"][q["idx"]]
    try:
        chosen = int(query.data.split("|", 1)[1])
    except Exception:
        chosen = -1

    if chosen == cur["answer_idx"]:
        q["score"] += 1
        await query.edit_message_text(f"✔️ إجابة صحيحة! نتيجتك الآن: {q['score']}")
    else:
        correct = cur["options"][cur["answer_idx"]]
        await query.edit_message_text(f"❌ إجابة خاطئة. الصحيحة: {correct}. نتيجتك الآن: {q['score']}")

    q["idx"] += 1
    # أرسل السؤال التالي برسالة جديدة
    await _send_cog_question(update, context)
