from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import random

cognitive_questions_data = [
    {"question": "ما هو حاصل ضرب 7 × 8؟", "options": ["54","56","63","49"], "answer": "56"},
    {"question": "إذا كان لديك 5 تفاحات وأكلت 2، فكم بقي؟", "options": ["2","3","4","5"], "answer": "3"},
    {"question": "ما اليوم الذي يأتي بعد الأربعاء؟", "options": ["الثلاثاء","الخميس","الجمعة","السبت"], "answer": "الخميس"},
    {"question": "أي من هذه الحيوانات يبيض؟", "options": ["القطة","الكلب","الدجاجة","البقرة"], "answer": "الدجاجة"},
    {"question": "لون السماء في يوم صافٍ؟", "options": ["أخضر","أحمر","أزرق","أصفر"], "answer": "أزرق"},
]

SELECTING_ANSWER = 1

async def start_cognitive_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["score"] = 0
    context.user_data["idx"] = 0
    context.user_data["qs"] = random.sample(cognitive_questions_data, min(5, len(cognitive_questions_data)))
    await ask_question(update, context)
    return SELECTING_ANSWER

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    i = context.user_data["idx"]
    qs = context.user_data["qs"]
    if i < len(qs):
        q = qs[i]
        kb = [[InlineKeyboardButton(opt, callback_data=opt)] for opt in q["options"]]
        await update.effective_message.reply_text(
            f"السؤال {i+1}: {q['question']}",
            reply_markup=InlineKeyboardMarkup(kb)
        )
    else:
        await update.effective_message.reply_text(
            f"انتهى الاختبار! نتيجتك: {context.user_data['score']} من {len(qs)}"
        )
        context.user_data.clear()

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    qcb = update.callback_query
    await qcb.answer()
    i  = context.user_data["idx"]
    qs = context.user_data["qs"]
    q  = qs[i]
    if qcb.data == q["answer"]:
        context.user_data["score"] += 1
        await qcb.edit_message_text(f"صحيح ✅ | نتيجتك الآن: {context.user_data['score']}")
    else:
        await qcb.edit_message_text(f"خطأ ❌ | الإجابة الصحيحة: {q['answer']}")

    context.user_data["idx"] += 1
    await ask_question(update, context)
    return SELECTING_ANSWER
