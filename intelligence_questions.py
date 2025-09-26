from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import random

intelligence_questions_data = [
    {"question": "ما الشيء الذي كلما أخذت منه كبر؟", "options": ["الحفرة","البئر","الجبل","البحر"], "answer": "الحفرة"},
    {"question": "ما الشيء الذي يمشي ويقف وليس له أرجل؟", "options": ["الساعة","النهر","السيارة","القطار"], "answer": "الساعة"},
    {"question": "له عين واحدة ولا يرى؟", "options": ["الإبرة","العمود","القلم","المسمار"], "answer": "الإبرة"},
    {"question": "ما الذي يرتفع ولا ينزل؟", "options": ["الدخان","العمر","البالون","الصاروخ"], "answer": "العمر"},
    {"question": "ما الذي يتكلم جميع اللغات؟", "options": ["صدى الصوت","اللسان","القاموس","الترجمة"], "answer": "صدى الصوت"},
]

SELECTING_INTELLIGENCE_ANSWER = 2

async def start_intelligence_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["i_score"] = 0
    context.user_data["i_idx"] = 0
    context.user_data["i_qs"] = random.sample(intelligence_questions_data, min(5, len(intelligence_questions_data)))
    await ask_intelligence_question(update, context)
    return SELECTING_INTELLIGENCE_ANSWER

async def ask_intelligence_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    i  = context.user_data["i_idx"]
    qs = context.user_data["i_qs"]
    if i < len(qs):
        q = qs[i]
        kb = [[InlineKeyboardButton(opt, callback_data=opt)] for opt in q["options"]]
        await update.effective_message.reply_text(
            f"سؤال الذكاء {i+1}: {q['question']}",
            reply_markup=InlineKeyboardMarkup(kb)
        )
    else:
        await update.effective_message.reply_text(
            f"انتهى اختبار الذكاء! نتيجتك: {context.user_data['i_score']} من {len(qs)}"
        )
        context.user_data.clear()

async def handle_intelligence_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    qcb = update.callback_query
    await qcb.answer()
    i  = context.user_data["i_idx"]
    qs = context.user_data["i_qs"]
    q  = qs[i]

    if qcb.data == q["answer"]:
        context.user_data["i_score"] += 1
        await qcb.edit_message_text(f"صحيح ✅ | نتيجتك الآن: {context.user_data['i_score']}")
    else:
        await qcb.edit_message_text(f"خطأ ❌ | الصحيحة: {q['answer']} | نتيجتك: {context.user_data['i_score']}")

    context.user_data["i_idx"] += 1
    await ask_intelligence_question(update, context)
    return SELECTING_INTELLIGENCE_ANSWER
