from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import random

# Placeholder for 500 cognitive questions
# In a real application, these would likely be loaded from a database or a file.
# Each question could be a dictionary with 'question', 'options', 'answer'

cognitive_questions_data = [
    {
        "question": "ما هو حاصل ضرب 7 × 8؟",
        "options": ["54", "56", "63", "49"],
        "answer": "56"
    },
    {
        "question": "إذا كان لديك 5 تفاحات وأكلت 2، فكم تفاحة بقيت لديك؟",
        "options": ["2", "3", "4", "5"],
        "answer": "3"
    },
    {
        "question": "ما هو اليوم الذي يأتي بعد الأربعاء؟",
        "options": ["الثلاثاء", "الخميس", "الجمعة", "السبت"],
        "answer": "الخميس"
    },
    {
        "question": "أي من هذه الحيوانات يبيض؟",
        "options": ["القطة", "الكلب", "الدجاجة", "البقرة"],
        "answer": "الدجاجة"
    },
    {
        "question": "ما هو لون السماء في يوم صافٍ؟",
        "options": ["أخضر", "أحمر", "أزرق", "أصفر"],
        "answer": "أزرق"
    },
    {
        "question": "ما هو الشهر الأول في السنة الميلادية؟",
        "options": ["فبراير", "مارس", "يناير", "أبريل"],
        "answer": "يناير"
    },
    {
        "question": "كم عدد أصابع اليد الواحدة؟",
        "options": ["3", "4", "5", "6"],
        "answer": "5"
    },
    {
        "question": "ما هو عكس كلمة 'كبير'؟",
        "options": ["طويل", "صغير", "واسع", "قصير"],
        "answer": "صغير"
    },
    {
        "question": "ما هو الصوت الذي يصدره الكلب؟",
        "options": ["مواء", "نباح", "صهيل", "زئير"],
        "answer": "نباح"
    },
    {
        "question": "ما هي عاصمة المملكة العربية السعودية؟",
        "options": ["جدة", "الرياض", "مكة", "الدمام"],
        "answer": "الرياض"
    },
]

# States for the conversation handler
SELECTING_ANSWER = 1

async def start_cognitive_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the cognitive questions quiz."""
    context.user_data['score'] = 0
    context.user_data['current_question_index'] = 0
    context.user_data['questions'] = random.sample(cognitive_questions_data, min(5, len(cognitive_questions_data))) # Take 5 random questions for now
    await ask_question(update, context)
    return SELECTING_ANSWER

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the current question to the user."""
    question_index = context.user_data['current_question_index']
    questions = context.user_data['questions']

    if question_index < len(questions):
        current_q = questions[question_index]
        question_text = f"السؤال {question_index + 1}: {current_q['question']}"
        keyboard = [[InlineKeyboardButton(option, callback_data=option)] for option in current_q['options']]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.effective_message.reply_text(question_text, reply_markup=reply_markup)
    else:
        await update.effective_message.reply_text(
            f"انتهى الاختبار! لقد أجبت على {context.user_data['score']} سؤالاً صحيحاً من أصل {len(questions)}."
        )
        context.user_data.clear() # Clear user data for this quiz
        return -1 # End the conversation

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Checks the user's answer and moves to the next question."""
    query = update.callback_query
    await query.answer()

    user_answer = query.data
    question_index = context.user_data['current_question_index']
    questions = context.user_data['questions']
    current_q = questions[question_index]

    if user_answer == current_q['answer']:
        context.user_data['score'] += 1
        await query.edit_message_text(text=f"إجابة صحيحة! النتيجة الحالية: {context.user_data['score']}")
    else:
        await query.edit_message_text(text=f"إجابة خاطئة. الإجابة الصحيحة هي: {current_q['answer']}. النتيجة الحالية: {context.user_data['score']}")

    context.user_data['current_question_index'] += 1
    await ask_question(update, context)
    return SELECTING_ANSWER

async def cancel_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the quiz."""
    await update.message.reply_text("تم إلغاء اختبار القدرات.")
    context.user_data.clear()
    return -1 # End the conversation
