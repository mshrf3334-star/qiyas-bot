# ... أعلى الملف كما هو

TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"]["text"]

        ai_reply = None
        if AI_API_KEY:
            headers = {
                "Authorization": f"Bearer {AI_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": os.getenv("AI_MODEL", "gpt-4o-mini"),
                "messages": [
                    {"role": "system", "content": "أنت مساعد ذكي للتدريب على اختبارات القدرات (Qiyas)."},
                    {"role": "user", "content": user_text}
                ]
            }
            try:
                r = requests.post(OPENAI_URL, headers=headers, json=payload, timeout=20)
                if r.status_code == 200:
                    result = r.json()
                    ai_reply = result["choices"][0]["message"]["content"].strip()
                else:
                    # طباعة مفيدة في اللوق لمعرفة السبب (401/429/500...)
                    print("OpenAI error:", r.status_code, r.text)
                    ai_reply = "⚠️ تعذر الاتصال بالذكاء الاصطناعي (تحقق من المفتاح/الموديل)."
            except Exception as e:
                print("OpenAI exception:", e)
                ai_reply = "⚠️ صار خطأ أثناء الاتصال بالذكاء الاصطناعي."
        else:
            ai_reply = "⚠️ مفتاح الذكاء الاصطناعي غير مضبوط (AI_API_KEY)."

        # تلغرام يقبل حتى 4096 حرف؛ نقص الرسالة لو طالت
        if len(ai_reply) > 4096:
            ai_reply = ai_reply[:4090] + " ..."

        requests.post(TELEGRAM_URL, json={"chat_id": chat_id, "text": ai_reply})

    return "ok", 200
