# multiplication.py — مُحلّل أرقام صارم، يقبل 7x7 و٧×٩ وأرقام عربية
import re
from telegram import Update
from telegram.ext import ContextTypes

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
X_CHARS = "x×X*"

def normalize_digits(text: str) -> str:
    return (text or "").translate(ARABIC_DIGITS)

async def ask_for_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["awaiting_multiplication_number"] = True
    await update.effective_message.reply_text("أدخل الرقم الذي تريد جدول الضرب له (مثال: 7 أو ٩).")

async def handle_possible_number_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """يشغّل فقط إذا كنا ننتظر رقم جدول الضرب، وإلا يمرّر الرسالة لغيره."""
    if not context.user_data.get("awaiting_multiplication_number"):
        return  # ليس في وضع الانتظار — لا نفعل شيئًا، ليست ميزتنا

    text = normalize_digits(update.effective_message.text).strip()

    # لو كتب المستخدم تعبيرًا مثل 7x7 أعطه ناتج الضرب ثم اطلب رقم الجدول مجددًا
    m_expr = re.fullmatch(r"\s*(-?\d+)\s*[" + re.escape(X_CHARS) + r"]\s*(-?\d+)\s*\Z", text)
    if m_expr:
        a, b = int(m_expr.group(1)), int(m_expr.group(2))
        await update.effective_message.reply_text(f"{a} × {b} = {a*b}\n\nأرسل رقمًا لعرض جدول ضربه:")
        return

    # التقط أول عدد صحيح في النص
    m_num = re.search(r"-?\d+", text)
    if not m_num:
        await update.effective_message.reply_text("الرجاء إدخال رقم صحيح (مثال: 5 أو ٨).")
        return

    n = int(m_num.group(0))
    lines = [f"{n} × {i} = {n*i}" for i in range(1, 11)]
    await update.effective_message.reply_text("\n".join(lines))

    # انتهينا — ألغِ وضع الانتظار
    context.user_data.pop("awaiting_multiplication_number", None)
