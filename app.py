import os
import sqlite3
import uvicorn
from openai import OpenAI
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

os.environ["GROQ_API_KEY"] = "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"

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY")
)

app = FastAPI()

def init_db():
    conn = sqlite3.connect("whatsapp_bot.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            phone_number TEXT PRIMARY KEY,
            bot_status TEXT DEFAULT 'active'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_bot_status(phone):
    conn = sqlite3.connect("whatsapp_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT bot_status FROM users WHERE phone_number = ?", (phone,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "active"

def set_bot_status(phone, status):
    conn = sqlite3.connect("whatsapp_bot.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (phone_number, bot_status) 
        VALUES (?, ?) 
        ON CONFLICT(phone_number) DO UPDATE SET bot_status = ?
    ''', (phone, status, status))
    conn.commit()
    conn.close()

chat_histories = {}

def get_airline_response(user_question, phone):
    if phone not in chat_histories:
        chat_histories[phone] = []
    
    # تنظيف ذاكرة المحادثة إذا طالت أكثر من اللازم لمنع تكرار مواضيع قديمة
    if len(chat_histories[phone]) > 6:
        chat_histories[phone] = chat_histories[phone][-4:]
        
    context = ""
    try:
        with open("knowledge.txt", "r", encoding="utf-8") as f:
            context = f.read()
    except FileNotFoundError:
        context = "شركة ضيوف الديار للسياحة والسفر."
    
    system_instruction = (
        "أنت موظف خدمة عملاء في شركة 'ضيوف الديار للسياحة والسفر'.\n"
        "تحدث باللهجة العراقية البيضاء الدارجة.\n"
        "تعليمات حازمة:\n"
        "1. التزم فقط بما يسأل عنه المستخدم حالياً.\n"
        "2. يمنع منعاً باتاً ذكر أي عروض أو رحلات (مثل بيروت) ما لم يسأل المستخدم عنها بالاسم.\n"
        "3. إذا كان سؤال المستخدم عن الدوام أو التواجد، أجب عن ذلك فقط ولا تضف شيئاً آخراً.\n"
        "4. كن مقتضباً ومهنياً.\n"
        f"المعلومات المتوفرة بالشركة:\n{context}"
    )
    
    messages = [{"role": "system", "content": system_instruction}]
    for msg in chat_histories[phone]:
        messages.append(msg)
    messages.append({"role": "user", "content": user_question})
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile", 
        messages=messages,
        temperature=0.0 # تم تغييرها لـ 0.0 ليكون البوت حرفياً ولا يألف من عنده
    )
    
    bot_reply = response.choices[0].message.content
    chat_histories[phone].append({"role": "user", "content": user_question})
    chat_histories[phone].append({"role": "assistant", "content": bot_reply})
    return bot_reply

@app.get("/", response_class=HTMLResponse)
def home():
    return "سيرفر ضيوف الديار يعمل بنجاح!"

@app.post("/whatsapp-webhook")
def whatsapp_webhook(text: str = Form(...), phone: str = Form(...), sender: str = Form(...)):
    keywords = ["اقساط", "الأقساط", "موظف", "احكي ويا موظف", "حسابات"]
    current_status = get_bot_status(phone)
    
    if sender == "staff":
        if text.strip() == "تفعيل":
            set_bot_status(phone, "active")
            return {"bot_reply": "تم إعادة تفعيل البوت.", "system_log": "تم إعادة تفعيل البوت."}
        return {"system_log": "رسالة موظف."}

    if any(key in text for key in keywords):
        set_bot_status(phone, "paused")
        return {"bot_reply": "تدلل عيوني، حولتك للموظف المختص.", "system_log": "تم قفل البوت."}
        
    if current_status == "paused":
        return {"system_log": "البوت متوقف."}
        
    reply = get_airline_response(text, phone)
    return {"bot_reply": reply, "system_log": "تم الرد بنجاح."}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)