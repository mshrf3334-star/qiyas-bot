# intelligence_questions.py — مثل السابق لكن بمُعرّف "iq|"
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import random

QUESTIONS = [
    {"q": "ما هو الشيء الذي كلما أخذت منه كبر؟", "options": ["الحفرة", "البئر", "الجبل", "البحر"], "answer_idx": 0},
    {"q": "ما هو الشيء الذي يمشي ويقف وليس له أرجل؟", "options": ["الساعة", "النهر", "السيارة", "القطار"], "answer_idx": 0},
    {"q": "له عين واحدة ولا يرى؟", "options": ["الإبرة", "العمود", "القلم", "المسمار"], "answer_idx": 0},
    {"q": "ما هو الشيء الذي يرتفع ولا ينزل؟", "options": ["الدخان", "العمر", "البالون", "الصاروخ"], "answer_idx": 1},
    {"q": "ما الذي يتكلم جميع لغات العالم؟", "options": ["صدى الصوت", "اللسان", "القاموس", "الترجمة"], "answer_idx": 0},
]

def _ensure_quiz(context: ContextTypes.DEFAULT_TYPE) -> dict:
    if "iq_quiz" not in context.user_data:
        context.user_data["iq_quiz"] = {
            "score": 0,
            "idx": 0,
            "qs": random.sample(QUESTIONS, min(5, len(QUESTIONS))),
        }
    return context.user_data["iq_quiz"]

async def start_intelligence_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("iq_quiz", None)
    _ensure_quiz(context)
    await _send_iq_question(update, context)

async def _send_iq_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = _ensure_quiz(context)
    if q["idx"] >= len(q["qs"]):
        await update.effective_message.reply_text(
            f"انتهى اختبار الذكاء! نتيجتك: {q['score']} من {len(q['qs'])}."
        )
        context.user_data.pop("iq_quiz", None)
        return

    cur = q["qs"][q["idx"]]
    buttons = [
        [InlineKeyboardButton(opt, callback_data=f"iq|{i}")]
        for i, opt in enumerate(cur["options"])
    ]
    await update.effective_message.reply_text(
        f"سؤال الذكاء {q['idx']+1}: {cur['q']}",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

async def handle_intelligence_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = _ensure_quiz(context)
    query = update.callback_query
    await query.answer()

    if q["idx"] >= len(q["qs"]):
        await query.edit_message_text("الجلسة انتهت. ارسل «أسئلة الذكاء (300 سؤال)» للبدء من جديد.")
        context.user_data.pop("iq_quiz", None)
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
    await _send_iq_question(update, context)
