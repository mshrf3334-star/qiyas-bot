from telegram import Update
from telegram.ext import ContextTypes

# ملاحظة: الدالة ترجع 0 لأنه لازم يطابق قيمة الحالة ASK_FOR_NUMBER في app.py
ASK_STATE = 0

_AR2EN = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def _to_int(text: str) -> int | None:
    """يحاول استخراج عدد صحيح من النص (يدعم أرقام عربية وإنجليزية)."""
    txt = (text or "").strip().translate(_AR2EN)
    if txt.startswith(("+", "-")) and txt[1:].isdigit():
        return int(txt)
    if txt.isdigit():
        return int(txt)
    # التقط أول رقم داخل النص إن وجد
    num = ""
    for ch in txt:
        if ch.isdigit() or (ch in "+-" and not num):
            num += ch
        elif num:
            break
    return int(num) if num and (num.lstrip("+-").isdigit()) else None


async def multiplication_table_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """يشغّل ميزة جدول الضرب ويطلب الرقم من المستخدم."""
    await update.message.reply_text("أرسل الرقم الذي تريد جدول الضرب له (مثال: 7).")
    return ASK_STATE  # يجب أن يساوي ASK_FOR_NUMBER في app.py (0)


async def generate_multiplication_table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """يُنشئ جدول الضرب للرقم المُرسل."""
    n = _to_int(update.message.text)
    if n is None:
        await update.message.reply_text("الرجاء إدخال رقم صحيح فقط (مثال: 7).")
        return ASK_STATE

    # حد بسيط للسلامة
    if abs(n) > 9999:
        await update.message.reply_text("الرقم كبير جدًا. جرّب رقمًا أصغر ✋.")
        return ASK_STATE

    lines = [f"{n} × {i} = {n * i}" for i in range(1, 11)]  # من 1 إلى 10
    table = "\n".join(lines)
    await update.message.reply_text(table)

    # نُبقي المحادثة في نفس الحالة لتكرار الطلب بسهولة
    await update.message.reply_text("أرسل رقمًا آخر أو اكتب /start للعودة للقائمة.")
    return ASK_STATE
