# qiyas_200.py — اختبار قياس كبير/غير محدود (توليدي + خفيف)
import random, math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# ===== توليد سؤال واحد في كل مرّة =====
def _mk_opts(correct, spreads=None, minval=None):
    if spreads is None:
        spreads = [-12,-8,-5,-3,-2,-1,1,2,3,5,8,12]
    cands = {int(correct)}
    while len(cands) < 4:
        val = int(correct) + random.choice(spreads)
        if minval is not None and val < minval:
            continue
        cands.add(val)
    opts = list(cands)
    random.shuffle(opts)
    return opts

def _gen_arith():
    a, b, c = random.randint(2, 15), random.randint(2, 12), random.randint(1, 10)
    kind = random.choice(["(a+b)*c", "a*b+c", "a*b-c", "a*c//b"])
    if kind == "(a+b)*c":
        val = (a + b) * c
        text = f"كم يساوي ({a} + {b}) × {c}؟"
    elif kind == "a*b+c":
        val = a * b + c
        text = f"كم يساوي {a} × {b} + {c}؟"
    elif kind == "a*b-c":
        val = a * b - c
        text = f"كم يساوي {a} × {b} − {c}؟"
    else:
        c = random.randint(2, 12)
        a = random.randint(2, 12)
        b = random.randint(2, 12)
        val = (a * c) // max(1, math.gcd(a*c, b)) * (b // max(1, math.gcd(a*c, b)))  # يضمن القسمة الصحيحة غالباً
        text = f"كم يساوي ({a} × {c}) ÷ {b}؟"
    opts = _mk_opts(val)
    return {"q": text, "opts": opts, "ans": opts.index(int(val))}

def _gen_percent():
    base = random.choice([80, 100, 120, 160, 200, 240, 300, 400, 500, 800])
    p = random.choice([10, 12, 20, 25, 30, 33, 40, 50])
    val = round(base * p / 100)
    text = f"كم يساوي {p}% من {base}؟"
    opts = _mk_opts(val)
    return {"q": text, "opts": opts, "ans": opts.index(int(val))}

def _gen_series():
    start = random.randint(1, 20)
    step  = random.randint(2, 9)
    n = random.randint(4, 6)
    seq = [start + i*step for i in range(n)]
    val = start + n*step
    text = f"ما العدد التالي في المتتالية: {', '.join(map(str, seq))} ؟"
    opts = _mk_opts(val)
    return {"q": text, "opts": opts, "ans": opts.index(int(val))}

def _gen_area_rect():
    L = random.randint(5, 30)
    W = random.randint(3, 20)
    val = L*W
    text = f"مساحة مستطيل طوله {L} وعرضه {W} تساوي؟"
    opts = _mk_opts(val)
    return {"q": text, "opts": opts, "ans": opts.index(int(val))}

def _gen_gcd():
    a = random.randint(12, 140)
    b = random.randint(12, 140)
    val = math.gcd(a, b)
    text = f"ما القاسم المشترك الأكبر للعددين {a} و {b}؟"
    opts = _mk_opts(val, spreads=[-3,-2,-1,1,2,3], minval=1)
    return {"q": text, "opts": opts, "ans": opts.index(int(val))}

def _gen_lcm():
    a = random.randint(4, 24)
    b = random.randint(4, 24)
    val = a*b // math.gcd(a, b)
    text = f"ما المضاعف المشترك الأصغر للعددين {a} و {b}؟"
    opts = _mk_opts(val)
    return {"q": text, "opts": opts, "ans": opts.index(int(val))}

def _gen_avg():
    n = random.randint(3, 7)
    nums = [random.randint(5, 45) for _ in range(n)]
    s = sum(nums)
    if s % n != 0:
        nums[-1] += (n - (s % n))
        s = sum(nums)
    val = s // n
    text = f"ما متوسط الأعداد: {', '.join(map(str, nums))} ؟"
    opts = _mk_opts(val)
    return {"q": text, "opts": opts, "ans": opts.index(int(val))}

def _gen_speed_time():
    v = random.choice([36, 40, 50, 60, 72, 80, 90, 100])
    t = random.choice([2, 3, 4, 5, 6])
    val = v * t
    text = f"سيارة سرعتها {v} كم/س لمدّة {t} ساعات. كم كيلومتراً تقطع؟"
    opts = _mk_opts(val)
    return {"q": text, "opts": opts, "ans": opts.index(int(val))}

def _gen_proportion():
    a, b = random.choice([(2,3),(3,4),(3,5),(4,5),(5,6),(7,8)])
    rhs = random.choice([12, 15, 18, 20, 24, 30, 36, 40])
    for _ in range(10):
        if (rhs * a) % b == 0:
            x = (rhs * a) // b
            break
        rhs += 1
    val = x
    text = f"إذا كانت النسبة {a}:{b} = س:{rhs} فما قيمة س؟"
    opts = _mk_opts(val)
    return {"q": text, "opts": opts, "ans": opts.index(int(val))}

GENERATORS = [
    _gen_arith, _gen_percent, _gen_series, _gen_area_rect,
    _gen_gcd, _gen_lcm, _gen_avg, _gen_speed_time, _gen_proportion
]

def _make_question():
    return random.choice(GENERATORS)()

# ===== حالة الجلسة (خفيفة) =====
def _ensure_session(context: ContextTypes.DEFAULT_TYPE):
    s = context.user_data.get("q200")
    if not s:
        s = {"asked": 0, "score": 0, "limit": 200, "cur": None}  # افتراضي 200
        context.user_data["q200"] = s
    return s

# ===== شاشة اختيار الحجم =====
async def start_qiyas_200_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # إعادة تعيين الجلسة
    context.user_data.pop("q200", None)
    buttons = [
        [
            InlineKeyboardButton("200 سؤال", callback_data="q200start|200"),
            InlineKeyboardButton("400 سؤال", callback_data="q200start|400"),
        ],
        [
            InlineKeyboardButton("800 سؤال", callback_data="q200start|800"),
            InlineKeyboardButton("1600 سؤال", callback_data="q200start|1600"),
        ],
        [InlineKeyboardButton("غير محدود", callback_data="q200start|inf")],
    ]
    await update.effective_message.reply_text(
        "اختر حجم اختبار القياس:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def handle_qiyas_200_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, raw = query.data.split("|", 1)
    s = _ensure_session(context)
    s["asked"] = 0
    s["score"] = 0
    s["limit"] = None if raw == "inf" else int(raw)
    s["cur"]   = None
    await query.edit_message_text(f"بدأنا! حجم الاختبار: {'غير محدود' if s['limit'] is None else s['limit']} سؤال.")
    await _send_q(update, context)

# ===== إرسال سؤال / إنهاء =====
async def _send_q(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = _ensure_session(context)
    # تحقق من الانتهاء
    if s["limit"] is not None and s["asked"] >= s["limit"]:
        total, score = s["asked"], s["score"]
        pct = round(score*100/max(1,total))
        await update.effective_message.reply_text(f"انتهى الاختبار! نتيجتك: {score}/{total} ({pct}%).")
        context.user_data.pop("q200", None)
        return

    # نولّد السؤال الحالي فقط
    cur = _make_question()
    s["cur"] = cur
    counter = f"{s['asked']+1}/{s['limit']}" if s["limit"] else f"{s['asked']+1}/∞"
    rows = [[InlineKeyboardButton(str(opt), callback_data=f"q200|{i}")]
            for i, opt in enumerate(cur["opts"])]
    rows.append([InlineKeyboardButton("إنهاء", callback_data="q200|end")])
    await update.effective_message.reply_text(
        f"سؤال {counter}:\n{cur['q']}",
        reply_markup=InlineKeyboardMarkup(rows)
    )

async def handle_qiyas_200_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = _ensure_session(context)
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "q200|end":
        total, score = s["asked"], s["score"]
        pct = round(score*100/max(1,total))
        await query.edit_message_text(f"تم الإنهاء. نتيجتك: {score}/{total} ({pct}%).")
        context.user_data.pop("q200", None)
        return

    # ما عندنا سؤال محفوظ؟ أعد الإرسال
    if not s.get("cur"):
        await query.edit_message_text("استأنفنا الجلسة. نرسل لك السؤال التالي الآن…")
        await _send_q(update, context)
        return

    cur = s["cur"]
    try:
        chosen = int(data.split("|",1)[1])
    except Exception:
        chosen = -1

    if chosen == cur["ans"]:
        s["score"] += 1
        await query.edit_message_text(f"✔️ صحيح. نتيجتك: {s['score']}")
    else:
        correct = cur["opts"][cur["ans"]]
        await query.edit_message_text(f"❌ خطأ. الصحيح: {correct}. نتيجتك: {s['score']}")

    s["asked"] += 1
    s["cur"] = None
    await _send_q(update, context)
