# qiyas_200.py — اختبار قياس (200 سؤال) توليدي
import random
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# ---------- توليد سؤال واحد ----------
def gen_arith():
    a, b, c = random.randint(2, 15), random.randint(2, 12), random.randint(1, 10)
    # عشوائياً نختار تركيب
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
        # اختر b قاسم لـ a*c كي تكون نتيجة صحيحة
        c = random.randint(2, 12)
        a = random.randint(2, 12)
        val = (a * c) // b
        text = f"كم يساوي ({a} × {c}) ÷ {b}؟"
    opts = mk_opts(val)
    return {"q": text, "options": opts, "answer_idx": opts.index(val)}

def gen_percent():
    base = random.choice([80, 100, 120, 160, 200, 240, 300, 400])
    p = random.choice([10, 12, 20, 25, 30, 40, 50])
    val = base * p // 100
    text = f"كم يساوي {p}% من {base}؟"
    opts = mk_opts(val)
    return {"q": text, "options": opts, "answer_idx": opts.index(val)}

def gen_series():
    start = random.randint(1, 12)
    step  = random.randint(2, 9)
    n = random.randint(4, 6)
    seq = [start + i*step for i in range(n)]
    val = start + n*step
    text = f"ما العدد التالي في المتتالية: {', '.join(map(str, seq))} ؟"
    opts = mk_opts(val)
    return {"q": text, "options": opts, "answer_idx": opts.index(val)}

def gen_area_rect():
    L = random.randint(5, 20)
    W = random.randint(3, 15)
    val = L*W
    text = f"مساحة مستطيل طوله {L} وعرضه {W} تساوي؟"
    opts = mk_opts(val)
    return {"q": text, "options": opts, "answer_idx": opts.index(val)}

def gen_gcd():
    a = random.randint(12, 90)
    b = random.randint(12, 90)
    val = math.gcd(a, b)
    text = f"ما القاسم المشترك الأكبر للعددين {a} و {b}؟"
    opts = mk_opts(val, spreads=[-3,-2,-1,1,2,3], minval=1)
    return {"q": text, "options": opts, "answer_idx": opts.index(val)}

def gen_lcm():
    a = random.randint(4, 20)
    b = random.randint(4, 20)
    val = a*b // math.gcd(a, b)
    text = f"ما المضاعف المشترك الأصغر للعددين {a} و {b}؟"
    opts = mk_opts(val)
    return {"q": text, "options": opts, "answer_idx": opts.index(val)}

def gen_avg():
    n = random.randint(3, 6)
    nums = [random.randint(5, 40) for _ in range(n)]
    s = sum(nums)
    # اجعل المتوسط عدداً صحيحاً أحياناً
    if s % n != 0:
        # عدّل آخر رقم ليتقسم
        r = s % n
        nums[-1] += (n - r)
        s = sum(nums)
    val = s // n
    text = f"ما متوسط الأعداد التالية: {', '.join(map(str, nums))} ؟"
    opts = mk_opts(val)
    return {"q": text, "options": opts, "answer_idx": opts.index(val)}

def gen_speed_time():
    v = random.choice([40, 50, 60, 70, 80, 90, 100])
    t = random.choice([2, 3, 4, 5])
    val = v * t
    text = f"سيارة سرعتها {v} كم/ساعة تسير لمدة {t} ساعات. كم كيلومتراً تقطع؟"
    opts = mk_opts(val)
    return {"q": text, "options": opts, "answer_idx": opts.index(val)}

def gen_proportion():
    a, b = random.choice([(2,3),(3,4),(3,5),(4,5),(5,6)])
    rhs = random.choice([12, 15, 18, 20, 24, 30])
    # a:b = x:rhs  => x = rhs * a / b  (اختر rhs مناسب ليكون صحيح)
    # لو ما كان صحيح نعيد الاختيار
    for _ in range(10):
        if (rhs * a) % b == 0:
            x = (rhs * a) // b
            break
        rhs += 1
    val = x
    text = f"إذا كانت النسبة {a}:{b} = س:{rhs} فما قيمة س؟"
    opts = mk_opts(val)
    return {"q": text, "options": opts, "answer_idx": opts.index(val)}

GENERATORS = [
    gen_arith, gen_percent, gen_series, gen_area_rect,
    gen_gcd, gen_lcm, gen_avg, gen_speed_time, gen_proportion
]

def mk_opts(correct, spreads=None, minval=None):
    if spreads is None:
        spreads = [-12,-8,-5,-3,-2,-1,1,2,3,5,8,12]
    candidates = {correct}
    while len(candidates) < 4:
        delta = random.choice(spreads)
        val = correct + delta
        if minval is not None and val < minval:
            continue
        candidates.add(val)
    opts = list(candidates)
    random.shuffle(opts)
    return opts

# ---------- حالة المستخدم وإرسال الأسئلة ----------
def _ensure_session(context: ContextTypes.DEFAULT_TYPE):
    if "q200" not in context.user_data:
        # 200 سؤال مولّد
        questions = [random.choice(GENERATORS)() for _ in range(200)]
        context.user_data["q200"] = {"idx": 0, "score": 0, "qs": questions}
    return context.user_data["q200"]

async def start_qiyas_200_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("q200", None)
    _ensure_session(context)
    await _send_q(update, context)

async def _send_q(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = _ensure_session(context)
    if s["idx"] >= len(s["qs"]):
        total = len(s["qs"])
        score = s["score"]
        pct = round(score*100/total)
        await update.effective_message.reply_text(f"انتهى اختبار القياس! نتيجتك: {score}/{total} ({pct}%).")
        context.user_data.pop("q200", None)
        return
    cur = s["qs"][s["idx"]]
    buttons = [[InlineKeyboardButton(str(opt), callback_data=f"q200|{i}")]
               for i, opt in enumerate(cur["options"])]
    await update.effective_message.reply_text(
        f"سؤال {s['idx']+1} / {len(s['qs'])}:\n{cur['q']}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def handle_qiyas_200_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = _ensure_session(context)
    query = update.callback_query
    await query.answer()

    if s["idx"] >= len(s["qs"]):
        await query.edit_message_text("الجلسة انتهت. أرسل «اختبار قياس (200 سؤال)» للبدء من جديد.")
        context.user_data.pop("q200", None)
        return

    cur = s["qs"][s["idx"]]
    try:
        chosen = int(query.data.split("|",1)[1])
    except Exception:
        chosen = -1

    if chosen == cur["answer_idx"]:
        s["score"] += 1
        await query.edit_message_text(f"✔️ صحيح. نتيجتك: {s['score']}")
    else:
        correct = cur["options"][cur["answer_idx"]]
        await query.edit_message_text(f"❌ خطأ. الإجابة الصحيحة: {correct}. نتيجتك: {s['score']}")

    s["idx"] += 1
    await _send_q(update, context)
