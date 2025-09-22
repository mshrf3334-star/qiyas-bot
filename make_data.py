# make_data.py
# يولّد ملف data.json يحوي 500 سؤال (جمع/طرح/ضرب/قسمة/نِسَب/متوسط/متتاليات) بالعربية

import json, random
random.seed(42)

def four_choices(correct):
    # يصنع 3 مشتتات قريبة من الإجابة الصحيحة
    s = set([correct])
    step = max(1, abs(correct)//20)  # خطوة للتباعد معقولة
    for delta in [step, -step, step*2, -step*2, step*3, -step*3, step+1, -(step+1)]:
        if len(s) == 4: break
        s.add(correct + delta)
    # في حال الأعداد كسريّة، حوّلها لعدد بمرتين بعد الفاصلة
    def norm(x):
        return round(x, 2) if isinstance(x, float) and not x.is_integer() else int(x) if float(x).is_integer() else round(x, 2)
    opts = list(map(norm, s))
    random.shuffle(opts)
    # تأكد 4 اختيارات
    while len(opts) < 4:
        opts.append(int(correct) + random.randint(1,9))
    return opts[:4]

def mcq(qid, qtype, question, correct, explanation, tags):
    choices = four_choices(correct)
    # answer_index = موضع الصحيح داخل choices
    try:
        idx = choices.index(int(correct))
    except:
        idx = choices.index(round(correct,2))
    return {
        "id": qid,
        "type": qtype,
        "question": question,
        "choices": [str(c) for c in choices],
        "answer_index": idx,
        "explanation": explanation,
        "tags": tags
    }

questions = []
qid = 1

# 1) جمع وطرح (100 سؤال)
for a in range(11, 61, 5):          # 11..60
    for b in range(9, 41, 7):       # 9..40
        if qid > 100: break
        s = a + b
        questions.append(mcq(qid, "math", f"ما ناتج {a} + {b}؟", s, f"{a}+{b}={s}.", ["رياضيات","جمع"]))
        qid += 1
    if qid > 100: break

for a in range(90, 49, -4):         # 90..50
    for b in range(5, 31, 5):       # 5..30
        if qid > 150: break
        d = a - b
        questions.append(mcq(qid, "math", f"ما ناتج {a} - {b}؟", d, f"{a}-{b}={d}.", ["رياضيات","طرح"]))
        qid += 1
    if qid > 150: break

# 2) جدول الضرب/الضرب العام (120 سؤال)
for a in range(6, 16):      # 6..15
    for b in range(6, 16):  # 6..15
        if qid > 270: break
        p = a*b
        questions.append(mcq(qid, "math", f"ما ناتج {a} × {b}؟", p, f"{a}×{b}={p}.", ["رياضيات","ضرب"]))
        qid += 1
    if qid > 270: break

# 3) قسمة بدون كسور (80 سؤال)
pairs = []
for a in range(12, 100):
    b = random.randint(2, 12)
    if a % b == 0:
        pairs.append((a,b))
random.shuffle(pairs)
for a,b in pairs[:80]:
    if qid > 350: break
    q = a // b
    questions.append(mcq(qid, "math", f"ما ناتج {a} ÷ {b}؟", q, f"{a}÷{b}={q}.", ["رياضيات","قسمة"]))
    qid += 1

# 4) نسب/زيادات مئوية (50 سؤال)
percent_list = [5,10,12,15,20,25,30,40,50]
bases = list(range(120, 980, 17))
random.shuffle(bases)
for base in bases[:50]:
    if qid > 400: break
    p = random.choice(percent_list)
    inc = round(base * p/100)
    newv = base + inc
    questions.append(mcq(qid, "math", f"زِيدَ عدد من {base} بنسبة {p}٪، فما القيمة الجديدة؟", newv,
                         f"الزيادة={inc}؛ الجديد={newv}.", ["رياضيات","نسب"]))
    qid += 1

# 5) متوسط 5 أعداد (50 سؤال)
def avg5(nums):
    return round(sum(nums)/5, 1)
sets = []
while len(sets) < 50:
    nums = [random.randint(10,99) for _ in range(5)]
    sets.append(nums)
for nums in sets:
    if qid > 450: break
    a = avg5(nums)
    questions.append(mcq(qid, "math", f"ما متوسط الأعداد {', '.join(map(str, nums))}؟", a,
                         f"المتوسط={sum(nums)}/{5}={a}.", ["رياضيات","متوسط"]))
    qid += 1

# 6) متتاليات حسابية وهندسية (50 سؤال)
# حسابية: d ثابت
for start in range(2, 20, 3):
    d = random.randint(2,9)
    seq = [start + i*d for i in range(5)]
    nxt = seq[-1] + d
    if qid > 475: break
    questions.append(mcq(qid, "logic", f"أكمل: {', '.join(map(str,seq))}, ___", nxt,
                         f"حسابية d={d}؛ التالي={nxt}.", ["منطق","متتاليات"]))
    qid += 1

# هندسية: r ثابت
for start in [2,3,4,5,6]:
    r = random.choice([2,3,4,5])
    seq = [start*(r**i) for i in range(5)]
    nxt = seq[-1]*r
    if qid > 500: break
    questions.append(mcq(qid, "logic", f"أكمل: {', '.join(map(str,seq))}, ___", nxt,
                         f"هندسية r={r}؛ التالي={nxt}.", ["منطق","متتاليات"]))
    qid += 1

# لو أقل من 500 لأي سبب، نكمل بأسئلة جمع بسيطة
a,b = 31, 47
while qid <= 500:
    s = a + b
    questions.append(mcq(qid, "math", f"ما ناتج {a} + {b}؟", s, f"{a}+{b}={s}.", ["رياضيات","جمع"]))
    qid += 1
    a += 1; b += 2

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(questions, f, ensure_ascii=False, indent=2)

print("✅ تم إنشاء data.json وفيه", len(questions), "سؤال.")
