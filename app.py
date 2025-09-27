# app.py — Qiyas Bot (Webhook/PTB v21) — بدون ملفات data
# -------------------------------------------------------
import os, logging, random, re, asyncio
from typing import List, Dict, Any, Optional, Tuple

from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.constants import ChatAction
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ================= إعدادات البيئة =================
BOT_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = (os.environ.get("WEBHOOK_URL") or "").rstrip("/")
PORT        = int(os.environ.get("PORT", "10000"))
AI_API_KEY  = os.environ.get("AI_API_KEY")
AI_MODEL    = os.environ.get("AI_MODEL", "gpt-4o-mini")

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN مفقود")
if not WEBHOOK_URL:
    raise RuntimeError("WEBHOOK_URL مفقود (مثال: https://your-app.onrender.com)")

# ================= لوق =================
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("qiyas-bot")

# ======================================================
#                 ذكاء عاطفي (مشجّع)
# ======================================================
EI_DEFAULT = True  # مفعّل افتراضياً

def get_ei(context): 
    return context.user_data.get("ei", EI_DEFAULT)

def set_ei(context, value: bool):
    context.user_data["ei"] = bool(value)

def ei_msg_correct(streak: int) -> str:
    msgs = [
        "👏 ممتاز! ثبّت هذا المستوى.",
        "🔥 أداء جميل! استمر.",
        "✅ إجابة موفقة — كفو.",
        "🌟 أحسنت! تركيزك واضح."
    ]
    bonus = f"\nسلسلة صحيحة متتالية: {streak} ✔️" if streak >= 3 else ""
    return random.choice(msgs) + bonus

def ei_msg_wrong(explain: str | None) -> str:
    soft = [
        "ولا يهمّك، جرّب اللي بعده بهدوء.",
        "👍 خذها خطوة خطوة، تركيزك أهم.",
        "💡 راجع الفكرة بهدوء وستتضح."
    ]
    tip = f"\nالشرح: {explain}" if explain else ""
    return random.choice(soft) + tip

# ======================================================
#                 مولِّدات الأسئلة
# ======================================================
def _choice4(correct: int | str, near: List[int | str]) -> Tuple[List[str], int]:
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

# ---- كمي ----
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

# ---- لفظي ----
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
        if random.random()<0.5:
            a,b = random.choice(SYN); c,d = random.choice(SYN)
            q = f"{a} : {b} :: {c} : ؟"; target = d
            pool = [d] + [x for _,x in SYN if x!=d][:3]
        else:
            a,b = random.choice(ANT); c,d = random.choice(ANT)
            q = f"{a} : {b} :: {c} : ؟"; target = d
            pool = [d] + [x for _,x in ANT if x!=d][:3]
        random.shuffle(pool)
        return {"question": q, "options": pool,
                "answer_index": pool.index(target),
                "explain": "العلاقة نفسها تُحافَظ عليها يمين التشبيه."}
    s, correct, opts_full = random.choice(COMP_SENT)
    opts = opts_full[:]; random.shuffle(opts)
    return {"question": s, "options": opts,
            "answer_index": opts.index(correct),
            "explain": f"الكلمة الأنسب: «{correct}»."}

# ---- ذكاء ----
AR_LETTERS = list("ابتثجحخدذرزسشصضطظعغفقكلمنهوي")  # مبسّط
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
    step = random.randint(1,3)
    start = random.randint(0, len(AR_LETTERS)-6)
    seq = [AR_LETTERS[start+i*step] for i in range(5)]
    nxt = AR_LETTERS[start+5*step]
    wrongs = [AR_LETTERS[(start+5*step+i)%len(AR_LETTERS)] for i in (1,2,3)]
    opts = [nxt] + wrongs; random.shuffle(opts)
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
    context.user_data["last_cat"] = cat  # لتمييز ردود الأزرار
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
        "/start القائمة\n/quant كمي\n/verbal لفظي\n/iq ذكاء\n/table جدول ضرب\n/ask_ai سؤالك\n/ei_on تشغيل التعاطف\n/ei_off إيقاف التعاطف"
    )

# ====== جدول الضرب ======
def parse_mul_expr(s: str) -> Tuple[bool, int, int]:
    s = s.replace("×","x").replace("X","x").replace("*","x")
    m = re.fullmatch(r"\s*(-?\d+)\s*x\s*(-?\d+)\s*", s)
    if not m:
        return False, 0, 0
    return True, int(m.group(1)), int(m.group(2))

def mult_table(n:int, upto:int=12) -> str:
    rows = [f"📐 جدول ضرب {n}:"]
    for i in range(1,upto+1):
        rows.append(f"{n} × {i} = {n*i}")
    return "\n".join(rows)

def clean_number_only(text: str) -> Optional[int]:
    t = text.strip()
    m = re.fullmatch(r"(-?\d+)", t)
    return int(m.group(1)) if m else None

# ====== موجّه النص ======
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = (update.message.text or "").strip()
    low = t.lower()

    if "جدول الضرب" in t:
        await update.message.reply_text("أرسل رقمًا (مثل 7) لجدول كامل، أو صيغة (7×7 / 7x7) لناتج فوري."); return
    if "كمي" in t:
        context.user_data.get("sessions", {}).pop("quant", None)
        context.user_data["streak"] = 0
        await update.message.reply_text("سيبدأ اختبار الكمي (حتى ٥٠٠). بالتوفيق! 💪")
        await send_next(update, context, "quant", "قدرات كمي"); return
    if "لفظي" in t:
        context.user_data.get("sessions", {}).pop("verbal", None)
        context.user_data["streak"] = 0
        await update.message.reply_text("سيبدأ اختبار اللفظي (حتى ٥٠٠). ركّز 👀")
        await send_next(update, context, "verbal", "قدرات لفظي"); return
    if "الذكاء" in t:
        context.user_data.get("sessions", {}).pop("iq", None)
        context.user_data["streak"] = 0
        await update.message.reply_text("سيبدأ اختبار الذكاء (حتى ٣٠٠).")
        await send_next(update, context, "iq", "أسئلة الذكاء"); return
    if "اسأل قياس" in t:
        await update.message.reply_text("اكتب سؤالك بعد الأمر:\n/ask_ai كيف أستعد لاختبار القدرات؟"); return

    # تعبير ضرب مباشر
    ok, a, b = parse_mul_expr(t)
    if ok:
        await update.message.reply_text(f"{a} × {b} = {a*b}"); return

    # رقم فقط → جدول كامل
    n = clean_number_only(t)
    if n is not None:
        await update.message.reply_text(mult_table(n)); return

    await update.message.reply_text("اختر من القائمة أو /help", reply_markup=MAIN_KB)

# ====== أوامر مختصرة ======
async def cmd_quant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.get("sessions", {}).pop("quant", None)
    context.user_data["streak"] = 0
    await send_next(update, context, "quant", "قدرات كمي")

async def cmd_verbal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.get("sessions", {}).pop("verbal", None)
    context.user_data["streak"] = 0
    await send_next(update, context, "verbal", "قدرات لفظي")

async def cmd_iq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.get("sessions", {}).pop("iq", None)
    context.user_data["streak"] = 0
    await send_next(update, context, "iq", "أسئلة الذكاء")

async def cmd_ei_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_ei(context, True)
    await update.message.reply_text("تم تفعيل الذكاء العاطفي ✅")

async def cmd_ei_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_ei(context, False)
    await update.message.reply_text("تم إيقاف الذكاء العاطفي ⛔️")

# ====== استلام الإجابة من الأزرار ======
async def cb_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    m = re.fullmatch(r"ans\|(\d+)", (query.data or ""))
    if not m: return
    choice = int(m.group(1))

    cat = context.user_data.get("last_cat")
    if cat not in ("quant","verbal","iq"):
        await query.edit_message_text("انتهت الجلسة. ابدأ من جديد /start"); return

    s = session_get(context, cat)
    res = s.check(choice)
    right_letter = ["أ","ب","ج","د","هـ","و","ز","ح"][res["answer_index"]]
    streak = context.user_data.get("streak", 0)

    if res["ok"]:
        streak += 1
        context.user_data["streak"] = streak
        msg = f"✔️ صحيح! ({s.correct}/{s.total})"
        if get_ei(context):
            msg += "\n" + ei_msg_correct(streak)
    else:
        context.user_data["streak"] = 0
        msg = f"❌ خطأ.\nالإجابة الصحيحة: {right_letter}"
        if get_ei(context):
            msg += "\n" + ei_msg_wrong(res.get("explain"))

    await query.edit_message_text(msg)
    label = "قدرات كمي" if cat=="quant" else "قدرات لفظي" if cat=="verbal" else "أسئلة الذكاء"
    await send_next(update, context, cat, label)

# ====== ذكاء اصطناعي ======
async def ask_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "")
    q = None
    if txt.startswith("/ask_ai") and " " in txt:
        q = txt.split(" ", 1)[1].strip()
    elif update.message and update.message.reply_to_message:
        q = (update.message.reply_to_message.text or "").strip()

    if not q:
        await update.message.reply_text("اكتب سؤالك بعد الأمر:\n/ask_ai كيف أذاكر القدرات؟\nأو ردّ بالأمر على رسالة فيها السؤال.")
        return
    if not AI_API_KEY:
        await update.message.reply_text("⚠️ لم يتم ضبط AI_API_KEY في الخادم (Render).")
        return

    try:
        await update.effective_chat.send_action(ChatAction.TYPING)
        from openai import OpenAI
        client = OpenAI(api_key=AI_API_KEY)

        def _call():
            return client.chat.completions.create(
                model=AI_MODEL,
                temperature=0.4,
                messages=[
                    {"role":"system","content":"أنت مدرّس قدرات خبير ومشجّع. أجب بالعربية بوضوح وخطوات مختصرة، وقدّم تطمينًا لطيفًا للطالب."},
                    {"role":"user","content": q}
                ],
            )

        resp = await asyncio.wait_for(asyncio.to_thread(_call), timeout=25)
        answer = (resp.choices[0].message.content or "").strip() or "لم أستطع توليد إجابة الآن."
        for i in range(0, len(answer), 4000):
            await update.message.reply_text(answer[i:i+4000])

    except asyncio.TimeoutError:
        await update.message.reply_text("⏱️ انتهت المهلة. جرّب سؤالاً أقصر أو أعد المحاولة.")
    except Exception as e:
        msg = str(e)
        if "401" in msg or "Unauthorized" in msg or "Incorrect API key" in msg:
            hint = "تحقّق من AI_API_KEY (يبدأ بـ sk-)."
        elif "model" in msg and ("not found" in msg or "does not exist" in msg):
            hint = f"اسم الموديل غير صحيح. جرّب: {AI_MODEL}"
        elif "429" in msg or "rate limit" in msg:
            hint = "تجاوزت حد الاستخدام. انتظر قليلاً ثم أعد المحاولة."
        else:
            hint = "تعذّر الاتصال بالخدمة."
        await update.message.reply_text(f"❌ خطأ في /ask_ai:\n{msg}\nالاقتراح: {hint}")

# ================= تشغيل (Webhook فقط) =================
def build() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("quant", cmd_quant))
    app.add_handler(CommandHandler("verbal", cmd_verbal))
    app.add_handler(CommandHandler("iq", cmd_iq))
    app.add_handler(CommandHandler("table", lambda u,c: u.message.reply_text("أرسل رقمًا (7) لجدول، أو 7×9 للحساب الفوري")))
    app.add_handler(CommandHandler("ei_on", cmd_ei_on))
    app.add_handler(CommandHandler("ei_off", cmd_ei_off))
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
