# app.py — Qiyas Bot (بدون ملفات data) — Webhook/PTB v21
# -------------------------------------------------------
import os, logging, random, re, string
from typing import List, Dict, Any, Optional, Tuple

from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# -------- الإعدادات من Environment --------
BOT_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = (os.environ.get("WEBHOOK_URL") or "").rstrip("/")
PORT        = int(os.environ.get("PORT", "10000"))

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN مفقود")
if not WEBHOOK_URL:
    raise RuntimeError("WEBHOOK_URL مفقود (مثال: https://your-app.onrender.com)")

AI_API_KEY  = os.environ.get("AI_API_KEY")
AI_MODEL    = os.environ.get("AI_MODEL", "gpt-4o-mini")

# -------- لوق --------
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("qiyas-bot")

# ======================================================
#                 مولِّدات الأسئلة
# ======================================================

def _choice4(correct: int | str, near: List[int | str]) -> Tuple[List[str], int]:
    """يصنع 4 خيارات عشوائية ويعيد (options, answer_index)."""
    opts = [str(correct)]
    for x in near:
        sx = str(x)
        if sx not in opts:
            opts.append(sx)
        if len(opts) == 4:
            break
    while len(opts) < 4:
        v = random.randint(-50, 200)
        sv = str(v)
        if sv not in opts:
            opts.append(sv)
    random.shuffle(opts)
    return opts, opts.index(str(correct))

# ---- كمي (توليد لا نهائي تقريباً) ----
def gen_quant() -> Dict[str, Any]:
    t = random.choice(["arith", "linear", "percent", "pow", "mix"])
    if t == "arith":
        a, b = random.randint(-20, 90), random.randint(-20, 90)
        op = random.choice(["+", "-", "×", "÷"])
        if op == "+":
            val = a + b
            opts, ans = _choice4(val, [val+random.choice([-3,-2,-1,1,2,3]), val+10, val-10])
            q = f"احسب: {a} + {b} = ؟"
        elif op == "-":
            val = a - b
            opts, ans = _choice4(val, [val+random.choice([-3,-1,1,3]), val+7, val-7])
            q = f"احسب: {a} - {b} = ؟"
        elif op == "×":
            a, b = random.randint(2, 20), random.randint(2, 15)
            val = a * b
            opts, ans = _choice4(val, [val+a, val-b, val+10])
            q = f"احسب: {a} × {b} = ؟"
        else:  # ÷
            b = random.randint(2, 12)
            val = random.randint(2, 12)
            a = b * val
            opts, ans = _choice4(val, [val+1, val-1, val+2])
            q = f"احسب: {a} ÷ {b} = ؟"
        return {"question": q, "options": opts, "answer_index": ans,
                "explain": "عمليات حسابية أساسية."}

    if t == "linear":
        a = random.randint(2, 9)
        x = random.randint(-10, 12)
        b = random.randint(-10, 12)
        c = a*x + b
        q = f"إذا كان {a}س + {b} = {c}، فما قيمة س؟"
        opts, ans = _choice4(x, [x+1, x-1, x+2])
        return {"question": q, "options": opts, "answer_index": ans,
                "explain": f"س = ( {c} - {b} ) ÷ {a} = {x}"}

    if t == "percent":
        y = random.randint(20, 200)
        x = random.choice([5,10,12,15,20,25,30,40,50])
        val = round(y * x / 100)
        q = f"ما {x}% من {y} ؟"
        opts, ans = _choice4(val, [val+5, val-5, val+10])
        return {"question": q, "options": opts, "answer_index": ans,
                "explain": f"{x}% × {y} = {y*x/100:g}"}

    if t == "pow":
        base = random.randint(2, 15)
        exp  = random.choice([2, 3])
        val  = base ** exp
        q = f"قيمة {base}^{exp} = ؟"
        near = [val+base, val-base, val+2]
        opts, ans = _choice4(val, near)
        return {"question": q, "options": opts, "answer_index": ans,
                "explain": f"{base}^{exp} = {val}"}

    # mix: مسافة = سرعة × زمن
    v = random.randint(30, 120)
    t = random.randint(1, 6)
    d = v * t
    q = f"سيارة سرعتها {v} كم/س، سارت {t} ساعات. ما المسافة؟"
    opts, ans = _choice4(d, [d-10, d+10, d+v])
    return {"question": q, "options": opts, "answer_index": ans,
            "explain": "المسافة = السرعة × الزمن."}

# ---- لفظي (مرادفات/أضداد/تناظر/إكمال) ----
SYN = [
    ("يجابه","يواجه"), ("جلّي","واضح"), ("ينأى","يبتعد"),
    ("يبتكر","يبدع"), ("محنة","ابتلاء"), ("ساطع","لامع"),
]
ANT = [
    ("مؤقّت","دائم"), ("قوي","ضعيف"), ("وضوح","غموض"),
    ("سهل","صعب"), ("قديم","حديث"), ("قريب","بعيد"),
]
COMP_SENT = [
    ("الطالب ____ في الاختبار النهائي.", "تفوق", ["تفوّق","تأخّر","تهاون","انسحب"]),
    ("كان القرار ____ بعد دراسة مستفيضة.", "صائب",  ["صائب","عشوائي","مُلتبس","متسرّع"]),
    ("يجب _____ الوقت لتحقيق الأهداف.", "استثمار",["إهدار","تضييع","استثمار","تجميد"]),
]
def gen_verbal() -> Dict[str, Any]:
    kind = random.choice(["syn","ant","analogy","cloze"])
    if kind == "syn":
        a,b = random.choice(SYN)
        wrongs = [w for _,w in SYN if w!=b][:6] + [x for _,x in ANT][:6]
        random.shuffle(wrongs)
        opts = [b] + wrongs[:3]
        random.shuffle(opts)
        return {"question": f"مرادف «{a}» هو:", "options": opts,
                "answer_index": opts.index(b), "explain": f"مرادف «{a}» = «{b}»."}
    if kind == "ant":
        a,b = random.choice(ANT)
        wrongs = [w for _,w in ANT if w!=b][:6] + [x for _,x in SYN][:6]
        random.shuffle(wrongs)
        opts = [b] + wrongs[:3]
        random.shuffle(opts)
        return {"question": f"ضدّ «{a}» هو:", "options": opts,
                "answer_index": opts.index(b), "explain": f"ضدّ «{a}» = «{b}»."}
    if kind == "analogy":
        # A:B :: C:?
        if random.random()<0.5:
            a,b = random.choice(SYN)
            c,d = random.choice(SYN)
            q = f"{a} : {b} :: {c} : ؟"
            target = d
            pool = [d] + [x for _,x in SYN if x!=d][:3]
        else:
            a,b = random.choice(ANT)
            c,d = random.choice(ANT)
            q = f"{a} : {b} :: {c} : ؟"
            target = d
            pool = [d] + [x for _,x in ANT if x!=d][:3]
        random.shuffle(pool)
        return {"question": q, "options": pool,
                "answer_index": pool.index(target),
                "explain": "العلاقة نفسها تُحافِظ عليها يمين التشبيه."}
    # cloze
    s, correct, opts_full = random.choice(COMP_SENT)
    opts = opts_full[:]
    random.shuffle(opts)
    return {"question": s, "options": opts,
            "answer_index": opts.index(correct),
            "explain": f"الكلمة الأنسب: «{correct}»."}

# ---- ذكاء (متتاليات رقمية/حروف/نمط متناوب) ----
AR_LETTERS = list("ابتثجحخدذرزسشصضطظعغفقكلمنهوي")  # تبسيط
def gen_iq() -> Dict[str, Any]:
    k = random.choice(["arith_seq","geom_seq","alt_seq","letter_seq"])
    if k == "arith_seq":
        a = random.randint(1,15); d = random.randint(2,9); n = [a+i*d for i in range(5)]
        ans = n[-1] + d
        opts, idx = _choice4(ans, [ans+d, ans-d, ans+2])
        return {"question": f"أكمل المتتالية: {', '.join(map(str,n))}, ؟",
                "options": opts, "answer_index": idx, "explain": f"فرق ثابت = {d}"}
    if k == "geom_seq":
        a = random.randint(1,6); r = random.choice([2,3,4]); n = [a*(r**i) for i in range(4)]
        ans = n[-1]*r
        opts, idx = _choice4(ans, [ans*r, ans//r if ans%r==0 else ans-1, ans+r])
        return {"question": f"أكمل: {', '.join(map(str,n))}, ؟",
                "options": opts, "answer_index": idx, "explain": f"متضاعف بنسبة {r}"}
    if k == "alt_seq":
        a = random.randint(5,20); d1 = random.randint(2,6); d2 = random.randint(7,12)
        seq = [a, a+d1, a+d1+d2, a+2*d1+d2, a+2*d1+2*d2]
        ans = a+3*d1+2*d2
        opts, idx = _choice4(ans, [ans+d1, ans+d2, ans-1])
        return {"question": f"نمط متناوب (+{d1}, +{d2}): {', '.join(map(str,seq))}, ؟",
                "options": opts, "answer_index": idx, "explain": "يزيد مرّة d1 ثم d2 بالتناوب."}
    # letter sequence
    step = random.randint(1,3)
    start = random.randint(0, len(AR_LETTERS)-6)
    seq = [AR_LETTERS[start+i*step] for i in range(5)]
    nxt = AR_LETTERS[start+5*step]
    wrongs = [AR_LETTERS[(start+5*step+i)%len(AR_LETTERS)] for i in (1,2,3)]
    opts = [nxt] + wrongs
    random.shuffle(opts)
    return {"question": f"أكمل: {'، '.join(seq)}, ؟",
            "options": opts, "answer_index": opts.index(nxt),
            "explain": f"زيادة ثابتة بالحروف بمقدار {step}."}

# ======================================================
#                    محرّك الاختبار
# ======================================================
class QuizSession:
    def __init__(self, generator, limit:int):
        self.gen = generator
        self.total = limit
        self.idx = 0
        self.correct = 0
        self.items: List[Dict[str,Any]] = []

    def _ensure(self):
        while len(self.items) <= self.idx and len(self.items) < self.total:
            self.items.append(self.gen())

    def current(self) -> Optional[Dict[str,Any]]:
        self._ensure()
        return self.items[self.idx] if self.idx < self.total else None

    def check(self, choice:int) -> Dict[str,Any]:
        q = self.current()
        if not q: return {"done": True}
        ok = (choice == q["answer_index"])
        if ok: self.correct += 1
        self.idx += 1
        return {"ok": ok, "answer_index": q["answer_index"], "explain": q.get("explain")}

def fmt_progress(i:int, total:int) -> str:
    blocks = 10
    fill = int((i/total)*blocks)
    return "■"*fill + "□"*(blocks-fill) + f" {i}/{total}"

def q_text(q:Dict[str,Any], idx:int, total:int, label:str) -> Tuple[str, InlineKeyboardMarkup]:
    letters = ["أ","ب","ج","د","هـ","و","ز","ح"]
    opts = q["options"]
    kb = [[InlineKeyboardButton(f"{letters[i]}) {opts[i]}", callback_data=f"ans|{i}")]
          for i in range(len(opts))]
    text = f"🧠 {label}\nالسؤال {idx+1} من {total}\n{fmt_progress(idx,total)}\n\n{q['question']}"
    return text, InlineKeyboardMarkup(kb)

def session_get(context: ContextTypes.DEFAULT_TYPE, cat:str) -> QuizSession:
    store = context.user_data.setdefault("sessions", {})
    s = store.get(cat)
    if s and isinstance(s, QuizSession):
        return s
    limit = 500 if cat in ("quant","verbal") else 300
    gen = gen_quant if cat=="quant" else gen_verbal if cat=="verbal" else gen_iq
    s = QuizSession(gen, limit)
    store[cat] = s
    return s

async def send_next(update:Update, context:ContextTypes.DEFAULT_TYPE, cat:str, label:str):
    s = session_get(context, cat)
    q = s.current()
    if not q:
        await update.effective_message.reply_text(
            f"انتهى الاختبار ✅\nالنتيجة: {s.correct}/{s.total}",
            reply_markup=ReplyKeyboardMarkup(MAIN_BTNS, resize_keyboard=True)
        )
        context.user_data["sessions"].pop(cat, None)
        return
    txt, kb = q_text(q, s.idx, s.total, label)
    # نوسم الرسالة بنوع الاختبار لتمييز الرد القادم
    context.user_data["last_cat"] = cat
    await update.effective_message.reply_text(txt, reply_markup=kb)

# ======================================================
#                     واجهة الاستخدام
# ======================================================
MAIN_BTNS = [
    [KeyboardButton("جدول الضرب")],
    [KeyboardButton("قدرات كمي (500 سؤال)")],
    [KeyboardButton("قدرات لفظي (500 سؤال)")],
    [KeyboardButton("أسئلة الذكاء (300 سؤال)")],
    [KeyboardButton("اسأل قياس (ذكاء اصطناعي)")],
]
MAIN_KB = ReplyKeyboardMarkup(MAIN_BTNS, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحبًا! اختر من القائمة 👇", reply_markup=MAIN_KB)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start القائمة\n/quant كمي\n/verbal لفظي\n/iq ذكاء\n/table جدول ضرب\n/ask_ai سؤالك"
    )

def clean_num(text: str) -> Optional[int]:
    if not text: return None
    t = text.strip().lower().replace("×","x").replace("✕","x").replace("＊","*")
    m = re.search(r"(-?\d+)\s*[x*]?\s*(-?\d+)?", t)
    if m:
        return int(m.group(1))
    m2 = re.fullmatch(r"\s*(-?\d+)\s*", t)
    return int(m2.group(1)) if m2 else None

def mult_table(n:int, upto:int=12) -> str:
    rows = [f"📐 جدول ضرب {n}:"]
    for i in range(1,upto+1):
        rows.append(f"{n} × {i} = {n*i}")
    return "\n".join(rows)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = (update.message.text or "").strip()
    low = t.lower()

    if "جدول الضرب" in t:
        await update.message.reply_text("أرسل رقمًا (مثل 7) أو صيغة (7×7 / 7x7)."); return
    if "كمي" in t:
        context.user_data.get("sessions", {}).pop("quant", None)
        await update.message.reply_text("سيبدأ اختبار الكمي (حتى ٥٠٠). بالتوفيق! 💪")
        await send_next(update, context, "quant", "قدرات كمي"); return
    if "لفظي" in t:
        context.user_data.get("sessions", {}).pop("verbal", None)
        await update.message.reply_text("سيبدأ اختبار اللفظي (حتى ٥٠٠). ركّز 👀")
        await send_next(update, context, "verbal", "قدرات لفظي"); return
    if "الذكاء" in t:
        context.user_data.get("sessions", {}).pop("iq", None)
        await update.message.reply_text("سيبدأ اختبار الذكاء (حتى ٣٠٠).")
        await send_next(update, context, "iq", "أسئلة الذكاء"); return
    if "اسأل قياس" in t:
        await update.message.reply_text("اكتب سؤالك بعد الأمر:\n/ask_ai كيف أستعد لاختبار القدرات؟"); return

    n = clean_num(t)
    if n is not None:
        await update.message.reply_text(mult_table(n)); return

    await update.message.reply_text("اختر من القائمة أو /help", reply_markup=MAIN_KB)

# أوامر مختصرة
async def cmd_quant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.get("sessions", {}).pop("quant", None)
    await send_next(update, context, "quant", "قدرات كمي")

async def cmd_verbal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.get("sessions", {}).pop("verbal", None)
    await send_next(update, context, "verbal", "قدرات لفظي")

async def cmd_iq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.get("sessions", {}).pop("iq", None)
    await send_next(update, context, "iq", "أسئلة الذكاء")

# استلام الإجابة من الأزرار
async def cb_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    m = re.fullmatch(r"ans\|(\d+)", data)
    if not m:
        return
    choice = int(m.group(1))
    cat = context.user_data.get("last_cat")  # تم ضبطها عند إرسال السؤال
    if cat not in ("quant","verbal","iq"):
        await query.edit_message_text("انتهت الجلسة. ابدأ من جديد /start")
        return
    s = session_get(context, cat)
    res = s.check(choice)
    right_letter = ["أ","ب","ج","د","هـ","و","ز","ح"][res["answer_index"]]
    if res["ok"]:
        msg = f"✔️ صحيح! ({s.correct}/{s.total})"
    else:
        explain = f"\nالشرح: {res.get('explain')}" if res.get("explain") else ""
        msg = f"❌ خطأ.\nالإجابة الصحيحة: {right_letter}{explain}"
    await query.edit_message_text(msg)
    # أرسل التالي
    label = "قدرات كمي" if cat=="quant" else "قدرات لفظي" if cat=="verbal" else "أسئلة الذكاء"
    await send_next(update, context, cat, label)

# ذكاء اصطناعي (اختياري)
async def ask_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "")
    q = txt.split(" ", 1)[1].strip() if txt.startswith("/ask_ai") and " " in txt else None
    if not q:
        await update.message.reply_text("اكتب سؤالك بعد الأمر:\n/ask_ai كيف أذاكر القدرات؟")
        return
    if not AI_API_KEY:
        await update.message.reply_text("لم يتم إعداد AI_API_KEY. أضِفه في Render.")
        return
    try:
        from openai import OpenAI
        client = OpenAI(api_key=AI_API_KEY)
        resp = client.chat.completions.create(
            model=AI_MODEL,
            messages=[{"role":"system","content":"أنت مدرّس قدرات خبير."},
                      {"role":"user","content": q}],
            temperature=0.4,
        )
        ans = resp.choices[0].message.content.strip()
        await update.message.reply_text(ans)
    except Exception as e:
        log.exception("AI error: %s", e)
        await update.message.reply_text("تعذّر الاتصال حالياً.")

# -------- تشغيل (Webhook فقط) --------
def build() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("quant", cmd_quant))
    app.add_handler(CommandHandler("verbal", cmd_verbal))
    app.add_handler(CommandHandler("iq", cmd_iq))
    app.add_handler(CommandHandler("table", lambda u,c: u.message.reply_text("أرسل الرقم أو 7×7")))
    app.add_handler(CommandHandler("ask_ai", ask_ai))

    app.add_handler(CallbackQueryHandler(cb_answer, pattern=r"^ans\|"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    return app

def main():
    app = build()
    log.info("Webhook on %s", WEBHOOK_URL)
    app.run_webhook(
        listen="0.0.0.0", port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
        drop_pending_updates=True,
    )

if __name__ == "__main__":
    main()
