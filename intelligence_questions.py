from __future__ import annotations

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import random

# ========= بنك أسئلة (عيّنة) =========
intelligence_questions_data = [
    {"question": "ما هو الشيء الذي كلما أخذت منه كبر؟", "options": ["الحفرة", "البئر", "الجبل", "البحر"], "answer": "الحفرة"},
    {"question": "ما هو الشيء الذي يمشي ويقف وليس له أرجل؟", "options": ["الساعة", "النهر", "السيارة", "القطار"], "answer": "الساعة"},
    {"question": "ما هو الشيء الذي له عين واحدة ولا يرى؟", "options": ["الإبرة", "العمود", "القلم", "المسمار"], "answer": "الإبرة"},
    {"question": "ما هو الشيء الذي يرتفع ولا ينزل؟", "options": ["الدخان", "العمر", "البالون", "الصاروخ"], "answer": "العمر"},
    {"question": "ما هو الشيء الذي يتكلم جميع لغات العالم؟", "options": ["صدى الصوت", "اللسان", "القاموس", "الترجمة"], "answer": "صدى الصوت"},
    {"question": "ما هو الشيء الذي له أسنان ولا يعض؟", "options": ["المشط", "المنشار", "الشوكة", "السكين"], "answer": "المشط"},
    {"question": "ما هو الشيء الذي كلما زاد نقص؟", "options": ["العمر", "المال", "الجهل", "الحفرة"], "answer": "العمر"},
    {"question": "ما هو الشيء الذي تسمعه ولا تراه؟", "options": ["الريح", "الصوت", "الصدى", "البرق"], "answer": "الريح"},
    {"question": "ما هو الشيء الذي يملك مدنًا ولا يملك بيوتًا، ويملك غابات ولا يملك أشجارًا، ويملك مياهًا ولا يملك أسماكًا؟",
     "options": ["الخريطة", "الكرة الأرضية", "الكتاب", "المحيط"], "answer": "الخريطة"},
    {"question": "ما هو الشيء الذي لا يبتل حتى لو دخل الماء؟", "options": ["الضوء", "الظل", "الهواء", "النار"], "answer": "الظل"},
]

# حالة المحادثة
SELECTING_INTELLIGENCE_ANSWER = 2


# ===== Helpers =====
def _pick_questions(n: int) -> list[dict]:
    return random.sample(intelligence_questions_data, min(n, len(intelligence_questions_data)))


async def _send_current_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    idx = context.user_data.get("intelligence_current_question_index", 0)
    questions: list[dict] = context.user_data.get("intelligence_questions", [])

    if idx >= len(questions):
        score = context.user_data.get("intelligence_score", 0)
        total = len(questions)
        await update.effective_chat.send_message(
            f"انتهى اختبار الذكاء! نتيجتك: {score} من {total}."
        )
        context.user_data.clear()
        return False

    q = questions[idx]
    options = list(q["options"])
    # random.shuffle(options)  # لو تبغى خلط ترتيب الخيارات

    keyboard = [[InlineKeyboardButton(opt, callback_data=opt)] for opt in options]
    await update.effective_chat.send_message(
        text=f"سؤال الذكاء {idx + 1}: {q['question']}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True,
    )
    return True


# ===== Entry & Handlers =====
async def start_intelligence_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    context.user_data["intelligence_score"] = 0
    context.user_data["intelligence_current_question_index"] = 0
    context.user_data["intelligence_questions"] = _pick_questions(5)

    await update.effective_message.reply_text("بدأ اختبار الذكاء ✅")
    await _send_current_question(update, context)
    return SELECTING_INTELLIGENCE_ANSWER


async def handle_intelligence_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()

    if "intelligence_questions" not in context.user_data:
        await update.effective_chat.send_message("لا يوجد اختبار نشط. اكتب /intelligence لبدء اختبار جديد.")
        return ConversationHandler.END

    idx = context.user_data.get("intelligence_current_question_index", 0)
    questions: list[dict] = context.user_data.get("intelligence_questions", [])
    if idx >= len(questions):
        await update.effective_chat.send_message("انتهى الاختبار. اكتب /intelligence لبدء اختبار جديد.")
        context.user_data.clear()
        return ConversationHandler.END

    current_q = questions[idx]
    user_answer = query.data if query else (update.message.text if update.message else "")

    if user_answer == current_q["answer"]:
        context.user_data["intelligence_score"] = context.user_data.get("intelligence_score", 0) + 1
        await query.edit_message_text(
            f"✅ إجابة صحيحة! نتيجتك الحالية: {context.user_data['intelligence_score']}"
        )
    else:
        await query.edit_message_text(
            f"❌ إجابة خاطئة. الصحيحة: {current_q['answer']}. "
            f"نتيجتك الحالية: {context.user_data.get('intelligence_score', 0)}"
        )

    context.user_data["intelligence_current_question_index"] = idx + 1
    has_more = await _send_current_question(update, context)
    if not has_more:
        return ConversationHandler.END

    return SELECTING_INTELLIGENCE_ANSWER


async def cancel_intelligence_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.effective_message.reply_text("تم إلغاء اختبار الذكاء.")
    return ConversationHandler.END
