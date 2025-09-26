from __future__ import annotations

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import random

# =========================
# بنك أسئلة (عينة - كبّرها براحتك)
# =========================
cognitive_questions_data = [
    {"question": "ما هو حاصل ضرب 7 × 8؟", "options": ["54", "56", "63", "49"], "answer": "56"},
    {"question": "إذا كان لديك 5 تفاحات وأكلت 2، فكم تفاحة بقيت لديك؟", "options": ["2", "3", "4", "5"], "answer": "3"},
    {"question": "ما هو اليوم الذي يأتي بعد الأربعاء؟", "options": ["الثلاثاء", "الخميس", "الجمعة", "السبت"], "answer": "الخميس"},
    {"question": "أي من هذه الحيوانات يبيض؟", "options": ["القطة", "الكلب", "الدجاجة", "البقرة"], "answer": "الدجاجة"},
    {"question": "ما هو لون السماء في يوم صافٍ؟", "options": ["أخضر", "أحمر", "أزرق", "أصفر"], "answer": "أزرق"},
    {"question": "ما هو الشهر الأول في السنة الميلادية؟", "options": ["فبراير", "مارس", "يناير", "أبريل"], "answer": "يناير"},
    {"question": "كم عدد أصابع اليد الواحدة؟", "options": ["3", "4", "5", "6"], "answer": "5"},
    {"question": "ما هو عكس كلمة 'كبير'؟", "options": ["طويل", "صغير", "واسع", "قصير"], "answer": "صغير"},
    {"question": "ما هو الصوت الذي يصدره الكلب؟", "options": ["مواء", "نباح", "صهيل", "زئير"], "answer": "نباح"},
    {"question": "ما هي عاصمة المملكة العربية السعودية؟", "options": ["جدة", "الرياض", "مكة", "الدمام"], "answer": "الرياض"},
]

# حالة المحادثة
SELECTING_ANSWER = 1


# ========== دوال مساعدة ==========
def _pick_questions(n: int) -> list[dict]:
    """اختر n أسئلة عشوائية من البنك."""
    if n >= len(cognitive_questions_data):
        return random.sample(cognitive_questions_data, len(cognitive_questions_data))
    return random.sample(cognitive_questions_data, n)


async def _send_current_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    يرسل السؤال الحالي. يرجع True إذا تم الإرسال،
    و False إذا انتهت الأسئلة وتم إعلان النتيجة.
    """
    idx = context.user_data.get("current_question_index", 0)
    questions: list[dict] = context.user_data.get("questions", [])

    if idx >= len(questions):
        # انتهى الاختبار
        score = context.user_data.get("score", 0)
        total = len(questions)
        await update.effective_chat.send_message(
            f"انتهى الاختبار! نتيجتك: {score} من {total}."
        )
        # تنظيف
        context.user_data.clear()
        return False

    q = questions[idx]
    # ممكن تخلط ترتيب الخيارات لو حبيت:
    options = list(q["options"])
    # random.shuffle(options)

    keyboard = [[InlineKeyboardButton(opt, callback_data=opt)] for opt in options]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.effective_chat.send_message(
        text=f"السؤال {idx + 1}: {q['question']}",
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )
    return True


# ========== نقاط دخول/تعامل ==========
async def start_cognitive_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء الاختبار."""
    # إعادة تهيئة الحالة
    context.user_data.clear()
    context.user_data["score"] = 0
    context.user_data["current_question_index"] = 0
    context.user_data["questions"] = _pick_questions(5)  # عدّل العدد إذا رغبت

    await update.effective_message.reply_text("بدأ الاختبار ✅")
    await _send_current_question(update, context)
    return SELECTING_ANSWER


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """التعامل مع اختيار المستخدم (Inline keyboard)."""
    query = update.callback_query
    if query:
        await query.answer()

    # تأكد أن بيانات الاختبار موجودة
    if "questions" not in context.user_data:
        await update.effective_chat.send_message("لا يوجد اختبار نشط. اكتب /cognitive لبدء اختبار جديد.")
        return ConversationHandler.END

    idx = context.user_data.get("current_question_index", 0)
    questions: list[dict] = context.user_data.get("questions", [])
    if idx >= len(questions):
        # لا يوجد سؤال حالي (انتهى)
        await update.effective_chat.send_message("انتهى الاختبار. اكتب /cognitive لبدء اختبار جديد.")
        context.user_data.clear()
        return ConversationHandler.END

    current_q = questions[idx]
    user_answer = query.data if query else (update.message.text if update.message else "")

    if user_answer == current_q["answer"]:
        context.user_data["score"] = context.user_data.get("score", 0) + 1
        await query.edit_message_text(f"✅ إجابة صحيحة! نتيجتك الحالية: {context.user_data['score']}")
    else:
        await query.edit_message_text(f"❌ إجابة خاطئة. الصحيحة: {current_q['answer']}. نتيجتك الحالية: {context.user_data.get('score', 0)}")

    # انتقل للسؤال التالي
    context.user_data["current_question_index"] = idx + 1
    has_more = await _send_current_question(update, context)
    if not has_more:
        return ConversationHandler.END

    return SELECTING_ANSWER


async def cancel_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إلغاء الاختبار."""
    context.user_data.clear()
    await update.effective_message.reply_text("تم إلغاء اختبار القدرات.")
    return ConversationHandler.END
