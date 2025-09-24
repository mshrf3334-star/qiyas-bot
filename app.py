import os, json, random, time
from flask import Flask, request, jsonify
import requests

# ========= الإعدادات =========
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL   = os.getenv("AI_MODEL", "gpt-4o-mini")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
SESSION = {}  # حالة المستخدمين بالذاكرة {chat_id: {...}}

app = Flask(__name__)

# ========= أدوات تيليجرام =========
def tg(method, payload):
    r = requests.post(f"{TG_API}/{method}", json=payload, timeout=15)
    return r.json() if r.ok else {"ok": False, "error": r.text}

def reply_kb(rows):
    return {"keyboard": rows, "resize_keyboard": True}

def inline_kb(rows):
    return {"inline_keyboard": rows}

def send_text(chat_id, text, **kw):
    return tg("sendMessage", {"chat_id": chat_id, "text": text, **kw})

def edit_text(chat_id, msg_id, text, **kw):
    return tg("editMessageText", {"chat_id": chat_id, "message_id": msg_id, "text": text, **kw})

# ========= بيانات قياس =========
def load_bank():
    path = os.path.join(os.getcwd(), "data.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            # نتأكد من البنية
            qs = []
            for q in data:
                if "question" in q and "choices" in q and "answer_index" in q:
                    qs.append(q)
            return qs
        except Exception:
            return []
BANK = load_bank()

# ========= ذكاء اصطناعي =========
def ai_chat(prompt, history=None):
    if not AI_API_KEY:
        return "⚠️ لم يتم ضبط مفتاح OpenAI (المتغيّر AI_API_KEY)."
    headers = {"Authorization": f"Bearer {AI_API_KEY}",
               "Content-Type": "application/json"}
    messages = [{"role": "system", "content": "أنت مساعد تعليمي مختصر وواضح."}]
    if history:
        messages += history
    messages.append({"role": "user", "content": prompt})
    body = {
        "model": AI_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 600
    }
    try:
        r = requests.post("https://api.openai.com/v1/chat/completions",
                          headers=headers, json=body, timeout=30)
        j = r.json()
        return j["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"⚠️ خطأ في طلب الذكاء الاصطناعي: {e}"

# ========= منيو رئيسي =========
MAIN_MENU = reply_kb([
    ["🧮 جدول الضرب", "🤖 الذكاء الاصطناعي"],
    ["📝 قياس: اختبر نفسك"]
])

def go_home(chat_id):
    send_text(chat_id, "اختر من القائمة ↓", reply_markup=MAIN_MENU)

# ========= جدول الضرب =========
def start_mult(chat_id):
    SESSION[chat_id] = {"mode": "mult", "score": 0, "n": None, "q": 0}
    send_text(chat_id,
              "🧮 جدول الضرب:\nأرسل رقم (2→12) للتدريب عليه، أو أرسل كلمة: عشوائي",
              reply_markup=reply_kb([["عشوائي"],["الرجوع ⬅️"]]))

def ask_mult(chat_id):
    st = SESSION.get(chat_id, {})
    if st.get("mode") != "mult":
        return
    n = st.get("n")
    a = random.randint(2, 12)
    st["current"] = (a, n)
    st["q"] += 1
    SESSION[chat_id] = st
    send_text(chat_id, f"سؤال {st['q']}: كم حاصل {a} × {n} ؟", reply_markup=reply_kb([["الرجوع ⬅️"]]))

def check_mult(chat_id, txt):
    st = SESSION.get(chat_id, {})
    if "current" not in st: 
        return
    a, n = st["current"]
    try:
        val = int(txt)
    except:
        send_text(chat_id, "أرسل رقمًا (الإجابة).")
        return
    correct = a * n
    if val == correct:
        st["score"] += 1
        send_text(chat_id, "✅ صحيح!")
    else:
        send_text(chat_id, f"❌ خطأ. الصحيح: {correct}")
    SESSION[chat_id] = st
    if st["q"] >= 10:
        send_text(chat_id, f"انتهى التدريب: نتيجتك {st['score']}/10")
        go_home(chat_id)
        SESSION.pop(chat_id, None)
    else:
        ask_mult(chat_id)

# ========= اختبار قياس =========
def start_quiz(chat_id):
    if not BANK:
        send_text(chat_id, "⚠️ لا يوجد بنك أسئلة (الملف data.json غير موجود).")
        return
    qs = random.sample(BANK, k=min(10, len(BANK)))
    SESSION[chat_id] = {
        "mode": "quiz",
        "idx": 0,
        "score": 0,
        "qs": qs
    }
    ask_quiz(chat_id)

def ask_quiz(chat_id):
    st = SESSION.get(chat_id, {})
    i = st.get("idx", 0)
    qs = st.get("qs", [])
    if i >= len(qs):
        send_text(chat_id, f"تم الاختبار: نتيجتك {st['score']}/{len(qs)}")
        go_home(chat_id)
        SESSION.pop(chat_id, None)
        return
    q = qs[i]
    buttons = []
    for k, choice in enumerate(q["choices"]):
        buttons.append([{"text": choice, "callback_data": f"quiz:{k}"}])
    send_text(
        chat_id,
        f"📝 سؤال {i+1}/{len(qs)}\n{q['question']}",
        reply_markup={"inline_keyboard": buttons}
    )

def handle_quiz_callback(chat_id, msg_id, data):
    st = SESSION.get(chat_id, {})
    if st.get("mode") != "quiz": 
        return
    i = st.get("idx", 0)
    q = st["qs"][i]
    pick = int(data.split(":")[1])
    correct = q["answer_index"]

    if pick == correct:
        st["score"] += 1
        txt = f"✅ صحيح!\n{q['explanation']}"
    else:
        txt = f"❌ خطأ.\n{q['explanation']}"
    edit_text(chat_id, msg_id, txt)
    st["idx"] += 1
    SESSION[chat_id] = st
    time.sleep(0.3)
    ask_quiz(chat_id)

# ========= ذكاء اصطناعي (دردشة) =========
def start_ai(chat_id):
    SESSION[chat_id] = {"mode": "ai", "history": []}
    send_text(chat_id, "🤖 أرسل سؤالك أو اكتب 'الرجوع' للعودة للقائمة.", reply_markup=reply_kb([["الرجوع ⬅️"]]))

def handle_ai(chat_id, txt):
    st = SESSION.get(chat_id, {"mode":"ai","history":[]})
    hist = st.get("history", [])
    # نحافظ على تاريخ قصير
    hist = hist[-6:]
    answer = ai_chat(txt, history=hist)
    hist += [{"role":"user","content":txt},{"role":"assistant","content":answer}]
    st["history"] = hist
    SESSION[chat_id] = st
    send_text(chat_id, answer)

# ========= Webhook =========
@app.route("/", methods=["GET"])
def index():
    return "OK", 200

@app.route("/setwebhook", methods=["GET"])
def setwebhook():
    base = request.url_root.rstrip("/")
    url = f"{base}/webhook"
    res = tg("setWebhook", {"url": url})
    return jsonify(res)

@app.route("/webhook", methods=["POST"])
def webhook():
    upd = request.get_json(force=True, silent=True) or {}
    # رسائل
    if "message" in upd:
        m = upd["message"]
        chat_id = m["chat"]["id"]
        txt = m.get("text", "") or ""

        if txt == "/start":
            send_text(chat_id, "مرحبًا! 👋", reply_markup=MAIN_MENU)
            return "ok"

        if txt in ["الرجوع", "الرجوع ⬅️", "/menu"]:
            SESSION.pop(chat_id, None)
            go_home(chat_id)
            return "ok"

        if txt.startswith("/قياس") or txt == "📝 قياس: اختبر نفسك":
            start_quiz(chat_id); return "ok"

        if txt == "🧮 جدول الضرب":
            start_mult(chat_id); return "ok"

        st = SESSION.get(chat_id)

        # في وضع جدول الضرب
        if st and st.get("mode")=="mult":
            if txt.strip()=="عشوائي":
                st["n"] = random.randint(2,12)
                st["q"] = 0; st["score"] = 0
                SESSION[chat_id] = st
                send_text(chat_id, f"اخترنا لك: {st['n']}. جاهز؟")
                ask_mult(chat_id)
                return "ok"
            # رقم المستخدم
            if st.get("n") is None:
                try:
                    n = int(txt)
                    if n < 2 or n > 12: raise ValueError
                    st["n"] = n; st["q"]=0; st["score"]=0
                    SESSION[chat_id] = st
                    send_text(chat_id, f"تمام! سنطرح 10 أسئلة على جدول {n}.")
                    ask_mult(chat_id)
                except:
                    send_text(chat_id, "أرسل رقمًا بين 2 و 12 أو اكتب عشوائي.")
                return "ok"
            # إجابة سؤال
            check_mult(chat_id, txt)
            return "ok"

        # الذكاء الاصطناعي
        if txt == "🤖 الذكاء الاصطناعي" or txt.startswith("/ai"):
            start_ai(chat_id); return "ok"
        if st and st.get("mode")=="ai":
            handle_ai(chat_id, txt); return "ok"

        # الافتراضي: أظهر المنيو
        go_home(chat_id)
        return "ok"

    # أزرار Inline
    if "callback_query" in upd:
        cq = upd["callback_query"]
        data = cq.get("data","")
        chat_id = cq["message"]["chat"]["id"]
        msg_id = cq["message"]["message_id"]
        if data.startswith("quiz:"):
            handle_quiz_callback(chat_id, msg_id, data)
        # نجاوب على callback عشان ما تدور الساعة
        tg("answerCallbackQuery", {"callback_query_id": cq["id"]})
        return "ok"

    return "ok"
