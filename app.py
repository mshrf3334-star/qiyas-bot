# app.py — Webhook-only Telegram bot on Render (Robust text router)
import os
import re
import logging
from typing import Tuple

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# ميزات فرعية
from multiplication import ask_for_number  # نستخدم الرسالة الإرشادية فقط
from cognitive_questions import start_cognitive_quiz, handle_cognitive_callback
from intelligence_questions import start_intelligence_quiz, handle_intelligence_callback
from ask_qiyas_ai import ask_qiyas_ai_handler
from qiyas_200 import (
    start_qiyas_200_quiz, handle_qiyas_200_start, handle_qiyas_200_callback
)

# ================= إعدادات البيئة =================
BOT_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = (os.environ.get("WEBHOOK_URL") or "").rstrip("/")
PORT        = int(os.environ.get("PORT", "10000"))

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN مفقود")
if not WEBHOOK_URL:
    raise RuntimeError("WEBHOOK_URL مفقود (ضع رابط خدمة Render العامة)")

# ================= لوجينغ =================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("qiyas-bot")

# ================= أدوات مساعدة =================
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
EN_DIGITS     = "0123456789"
TRANS_TABLE   = str.maketrans(ARABIC_DIGITS, EN_DIGITS)

def normalize_text(s: str) -> str:
    # حروف × وx وX و* كلها تُعامل كرمز ضرب موحد
    s = s.replace("×", "x").replace("X", "x").replace("*", "x")
    # استبدال الأرقام العربية بالإنجليزية
    s = s.translate(TRANS_TABLE)
    # حذف مسافات زائدة ورموز تحكم خفية إن وجدت
    return re.sub(r"[\u200e\u200f\u202a-\u202e]", "", s).strip()

def parse_mul_expr(s: str) -> Tuple[bool, int, int]:
    """
    يحاول قراءة تعبير ضرب مثل 7x9 (أو ٧×٩).
    يعيد (True, a, b) لو نجح؛ وإلا (False, 0, 0)
    """
    s = normalize_text(s)
    m = re.fullmatch(r"(\d+)\s*x\s*(\d+)", s)
    if not m:
        return False, 0, 0
    return True, int(m.group(1)), int(m.group(2))

def render_table(n: int, upto: int = 12) -> str:
    lines = [f"🧮 جدول ضرب {n}:"]
    for i in range(1, upto + 1):
        lines.append(f"{n} × {i} = {n * i}")
    return "\n".join(lines)

# ================= واجهة المستخدم =================
def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("جدول الضرب")],
            [KeyboardButton("اختبر قدراتك (500 سؤال)")],
            [KeyboardButton("أسئلة الذكاء (300 سؤال)")],
            [KeyboardButton("اختبار قياس (200 سؤال)")],
            [KeyboardButton("اسأل قياس (ذكاء اصطناعي)")],
        ],
        resize_keyboard=True,
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html("مرحباً! اختر من القائمة 👇", reply_markup=main_keyboard())

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "الأوامر: /multiplication /cognitive /intelligence /ask_ai",
        reply_markup=main_keyboard()
    )

# موجّه نصي صارم: أي رسالة نصية تمر من هنا
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    raw = update.message.text or ""
    txt = normalize_text(raw)

    # 1) أزرار القائمة (نطابق بالاحتواء بدل التطابق الكامل)
    if "جدول الضرب" in raw:
        # رسالة طلب رقم (من الملف الفرعي) + تهيئة حالة انتظار
        context.user_data["await_table_number"] = True
        await ask_for_number(update, context)
        return

    if "اختبر قدراتك" in raw:
        await start_cognitive_quiz(update, context); return

    if "أسئلة الذكاء" in raw:
        await start_intelligence_quiz(update, context); return

    if "اختبار قياس" in raw:
        await start_qiyas_200_quiz(update, context); return

    if "اسأل قياس" in raw:
        await update.message.reply_text("اكتب سؤالك بالأمر: /ask_ai سؤالك هنا"); return

    # 2) تعبير ضرب مباشر مثل 7x9 أو ٧×٩
    ok, a, b = parse_mul_expr(raw)
    if ok:
        await update.message.reply_text(f"{a} × {b} = {a*b}")
        return

    # 3) إذا كان ينتظر جدول ضرب ورقم فقط (عربي/إنجليزي)
    if context.user_data.get("await_table_number"):
        num_txt = normalize_text(raw)
        if re.fullmatch(r"\d{1,3}", num_txt):
            n = int(num_txt)
            context.user_data.pop("await_table_number", None)
            await update.message.reply_text(render_table(n))
            return
        else:
            await update.message.reply_text("الرجاء إدخال رقم صحيح (مثال: 7).")
            return

    # 4) لو ما طابق أي شيء:
    await update.message.reply_text("اختر من القائمة أو اكتب /help.", reply_markup=main_keyboard())

async def unknown_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أمر غير معروف. استخدم /help", reply_markup=main_keyboard())

# ================= إعداد التطبيق =================
def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()

    # أوامر أساسية
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("multiplication", ask_for_number))
    app.add_handler(CommandHandler("ask_ai", ask_qiyas_ai_handler))

    # الرد على كل النصوص عبر موجّه واحد
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    # CallbackQuery للاختبارات
    app.add_handler(CallbackQueryHandler(handle_cognitive_callback,    pattern=r"^cog\|"))
    app.add_handler(CallbackQueryHandler(handle_intelligence_callback, pattern=r"^iq\|"))
    app.add_handler(CallbackQueryHandler(handle_qiyas_200_start,       pattern=r"^q200start\|"))
    app.add_handler(CallbackQueryHandler(handle_qiyas_200_callback,    pattern=r"^q200\|"))

    # أوامر غير معروفة
    app.add_handler(MessageHandler(filters.COMMAND, unknown_cmd))
    return app

# ================= تشغيل Webhook =================
def main():
    app = build_app()
    log.info("Starting Webhook at %s", WEBHOOK_URL)
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,                          # path سري
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",    # العنوان الخارجي الكامل
        drop_pending_updates=True,
    )

if __name__ == "__main__":
    main()
