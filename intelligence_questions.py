from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import random

# Placeholder for 300 intelligence questions
# In a real application, these would likely be loaded from a database or a file.
# Each question could be a dictionary with 'question', 'options', 'answer'

intelligence_questions_data = [
    {
        "question": "ما هو الشيء الذي كلما أخذت منه كبر؟",
        "options": ["الحفرة", "البئر", "الجبل", "البحر"],
        "answer": "الحفرة"
    },
    {
        "question": "ما هو الشيء الذي يمشي ويقف وليس له أرجل؟",
        "options": ["الساعة", "النهر", "السيارة", "القطار"],
        "answer": "الساعة"
    },
    {
        "question": "ما هو الشيء الذي له عين واحدة ولا يرى؟",
        "options": ["الإبرة", "العمود", "القلم", "المسمار"],
        "answer": "الإبرة"
    },
    {
        "question": "ما هو الشيء الذي يرتفع ولا ينزل؟",
        "options": ["الدخان", "العمر", "البالون", "الصاروخ"],
        "answer": "العمر"
    },
    {
        "question": "ما هو الشيء الذي يتكلم جميع لغات العالم؟",
        "options": ["صدى الصوت", "اللسان", "القاموس", "الترجمة"],
        "answer": "صدى الصوت"
    },
    {
        "question": "ما هو الشيء الذي له أسنان ولا يعض؟",
        "options": ["المشط", "المنشار", "الشوكة", "السكين"],
        "answer": "المشط"
    },
    {
        "question": "ما هو الشيء الذي كلما زاد نقص؟",
        "options": ["العمر", "المال", "الجهل", "الحفرة"],
        "answer": "العمر"
    },
    {
        "question": "ما هو الشيء الذي تسمعه ولا تراه؟",
        "options": ["الريح", "الصوت", "الصدى", "البرق"],
        "answer": "الريح"
    },
    {
        "question": "ما هو الشيء الذي يملك مدنًا ولا يملك بيوتًا، ويملك غابات ولا يملك أشجارًا، ويملك مياهًا ولا يملك أسماكًا؟",
        "options": ["الخريطة", "الكرة الأرضية", "الكتاب", "المحيط"],
        "answer": "الخريطة"
    },
    {
        "question": "ما هو الشيء الذي لا يبتل حتى لو دخل الماء؟",
        "options": ["الضوء", "الظل", "الهواء", "النار"],
        "answer": "الظل"
    },
]

# States for the conversation handler
SELECTING_INTELLIGENCE_ANSWER = 2

async def start_intelligence_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the intelligence questions quiz."""
    context.user_data["intelligence_score"] = 0
    context.user_data["intelligence_current_question_index"] = 0
    context.user_data["intelligence_questions"] = random.sample(intelligence_questions_data, min(5, len(intelligence_questions_data))) # Take 5 random questions for now
    await ask_intelligence_question(update, context)
    return SELECTING_INTELLIGENCE_ANSWER

async def ask_intelligence_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the current intelligence question to the user."""
    question_index = context.user_data["intelligence_current_question_index"]
    questions = context.user_data["intelligence_questions"]

    if question_index < len(questions):
        current_q = questions[question_index]
        question_text = f"سؤال الذكاء {question_index + 1}: {current_q["question"]}"
        keyboard = [[InlineKeyboardButton(option, callback_data=option)] for option in current_q["options"]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.effective_message.reply_text(question_text, reply_markup=reply_markup)
    else:
        await update.effective_message.reply_text(
            f"انتهى اختبار الذكاء! لقد أجبت على {context.user_data["intelligence_score"]} سؤالاً صحيحاً من أصل {len(questions)}."
        )
        context.user_data.clear() # Clear user data for this quiz
        return -1 # End the conversation

async def handle_intelligence_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Checks the user's answer and moves to the next intelligence question."""
    query = update.callback_query
    await query.answer()

    user_answer = query.data
    question_index = context.user_data["intelligence_current_question_index"]
    questions = context.user_data["intelligence_questions"]
    current_q = questions[question_index]

    if user_answer == current_q["answer"]:
        context.user_data["intelligence_score"] += 1
        await query.edit_message_text(text=f"إجابة صحيحة! النتيجة الحالية: {context.user_data["intelligence_score"]}")
    else:
        await query.edit_message_text(text=f"إجابة خاطئة. الإجابة الصحيحة هي: {current_q["answer"]}. النتيجة الحالية: {context.user_data['intelligence_score']}")

    context.user_data["intelligence_current_question_index"] += 1
    await ask_intelligence_question(update, context)
    return SELECTING_INTELLIGENCE_ANSWER

async def cancel_intelligence_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the intelligence quiz."""
    await update.message.reply_text("تم إلغاء اختبار الذكاء.")
    context.user_data.clear()
    return -1 # End the conversation
