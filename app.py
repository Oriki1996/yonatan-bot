# app.py - יונתן Chatbot Server (גרסה 3.1 - תיקון באג אמנזיה)

from flask import Flask, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import os
import logging
import datetime
import random
from models import SessionManager
import google.generativeai as genai

# --- הגדרות ואבטחה ---
load_dotenv()
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

# --- הגדרת לוגים ---
os.makedirs('data', exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler('data/yonatan_sessions.log', encoding='utf-8'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

# --- פרומפט המערכת של יונתן (גרסה 3.1 - עם הנחיית הקשר) ---
YONATAN_SYSTEM_PROMPT_TEMPLATE = """
אתה "יונתן," פסיכולוג חינוכי וירטואלי.

# הוראת על:
תפקידך הוא להמשיך שיחה קיימת עם הורה בשם {name}. התייחס תמיד להיסטוריית השיחה המצורפת ואל תתחיל את השיחה מחדש אלא אם המשתמש מבקש זאת במפורש. פנה אל המשתמש בלשון {pronoun}.

# כללי התנהגות קריטיים:
1.  **המשכיות:** המשך את השיחה באופן טבעי מהנקודה בה היא נפסקה. אל תציג את עצמך שוב.
2.  **זיהוי סתירות:** אם ההודעה החדשה סותרת מידע קודם, שאל להבהרה.
3.  **מבנה ותבנית:** עליך לעצב את תשובתך אך ורק לפי מבנה הכותרות הבא.

# מבנה התשובה המחייב:
## 💙 הבנה אישית
[1-2 משפטים של אמפתיה והכרה ברגש המשתמע מההודעה האחרונה ומההקשר הכללי]
## 🔍 בואו נבין את המצב
[2-3 שאלות המשך ממוקדות להבנת המצב לעומק]
## 🛠️ הכלי המרכזי (אחד בלבד)
[הצג רק כלי מעשי אחד הרלוונטי לשלב הנוכחי בשיחה. אם אין צורך, כתוב "בשלב זה אין צורך בכלי חדש.".]
## 🎯 המשך המעקב
[מה השלב הבא או מה לנסות עד השיחה הבאה]
## 🚨 מתי לפנות לעזרה מקצועית
[תזכורת קצרה במידת הצורך]
"""

# --- פרומפטים לתגובות מיוחדות ---
INSULT_RESPONSE_PROMPT = "אתה 'יונתן', בוט עזר. המשתמש העליב אותך. הגב באמפתיה, קצרות, ובצורה לא מתגוננת. אמור משהו כמו 'אני מבין שאתה מתוסכל. המטרה שלי היא לעזור. אולי נוכל לנסות שוב?'. אל תשתמש בתבנית הכותרות."
FRUSTRATION_RESPONSE_PROMPT = "אתה 'יונתן', בוט עזר. המשתמש מביע תסכול כלפיך או כלפי התהליך. הכר בתסכול שלו, שאל אותו מה מפריע לו וכיצד תוכל לעזור טוב יותר. אל תציע כלים חדשים כרגע."
CLARIFICATION_PROMPT = "אתה 'יונתן', בוט עזר. המשתמש מבולבל או שאל שאלה קצרה מאוד. הבהר את הנקודה האחרונה שאמרת בקצרה ושאל אותו מה לא היה ברור."

# --- הגדרת אפליקציה ורכיבים מרכזיים ---
app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day", "50 per hour"])
model = None
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("✅ מודל הבינה המלאכותית הוגדר בהצלחה")
    except Exception as e:
        logger.error(f"❌ שגיאה בהגדרת מודל הבינה המלאכותית: {e}")
else:
    logger.error("❌ מפתח ה-API של גוגל לא נמצא!")
session_manager = SessionManager()

# --- פונקציית המיון ---
def classify_user_intent(user_message):
    if not model: return 'genuine_query'
    try:
        triage_prompt = f"""
        נתח את הודעת המשתמש הבאה וסווג את הכוונה המרכזית. השב אך ורק עם אחת מהמילים הבאות:
        'insult', 'frustration', 'clarification_request', 'genuine_query'.
        הודעת המשתמש: "{user_message}"
        """
        response = model.generate_content(triage_prompt)
        intent = response.text.strip().lower()
        valid_intents = ['insult', 'frustration', 'clarification_request', 'genuine_query']
        if intent in valid_intents:
            logger.info(f"Intent classified as: {intent}")
            return intent
        return 'genuine_query'
    except Exception as e:
        logger.error(f"Error in classify_user_intent: {e}")
        return 'genuine_query'

# --- לוגיקת השרת ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/user-details', methods=['POST'])
def user_details():
    # קוד זה נשאר ללא שינוי מהגרסה הקודמת
    data = request.json
    session_id, name, gender = data.get('session_id'), data.get('name'), data.get('gender')
    if not all([session_id, name, gender]): return jsonify({"error": "Missing data"}), 400
    if session_id not in session_manager.active_sessions: session_manager.create_session(session_id)
    profile = session_manager.parent_profiles[session_id]
    profile.name, profile.gender = name, gender
    logger.info(f"User details for {session_id}: Name={name}, Gender={gender}")
    return jsonify({"status": "success"})

@app.route('/api/chat', methods=['POST'])
@limiter.limit("20 per minute")
def chat():
    try:
        data = request.json
        history = data.get('history', [])
        session_id = data.get('session_id', 'default')
        if not history: return jsonify({"response": "לא התקבלה הודעה"}), 400
        
        user_message = history[-1]['parts'][0]['text']
        
        intent = classify_user_intent(user_message)

        prompt_map = {
            'insult': INSULT_RESPONSE_PROMPT,
            'frustration': FRUSTRATION_RESPONSE_PROMPT,
            'clarification_request': CLARIFICATION_PROMPT,
            'genuine_query': YONATAN_SYSTEM_PROMPT_TEMPLATE
        }
        prompt_to_use = prompt_map.get(intent)

        profile = session_manager.parent_profiles.get(session_id)
        user_name = profile.name if profile and profile.name else "משתמש"
        pronoun_map = {'male': 'זכר', 'female': 'נקבה'}
        user_pronoun = pronoun_map.get(profile.gender, "זכר/נקבה") if profile and profile.gender else "זכר/נקבה"

        final_prompt = prompt_to_use.format(name=user_name, pronoun=user_pronoun) if '{name}' in prompt_to_use else prompt_to_use
        
        bot_response = "שגיאה פנימית."
        if model:
            try:
                chat_history_for_model = [{'role': 'user' if msg['role'] == 'user' else 'model', 'parts': msg['parts']} for msg in history]
                chat_session = model.start_chat(history=chat_history_for_model)
                response = chat_session.send_message(final_prompt)
                bot_response = response.text
            except Exception as e:
                logger.error(f"שגיאה בתקשורת עם מודל הבינה המלאכותית: {e}")
                bot_response = "נתקלתי בקושי טכני, אנא נסה/י שוב."

        return jsonify({"response": bot_response})

    except Exception as e:
        logger.error(f"שגיאה כללית חמורה בשרת: {e}", exc_info=True)
        return jsonify({"response": "מצטער, אירעה שגיאה חמורה."}), 500

# --- הקוד שמפעיל את השרת ---
if __name__ == '__main__':
    if not GOOGLE_API_KEY:
        print("❌ מפתח ה-API של גוגל לא נמצא!")
        exit(1)
    
    print("🌊 ========== יונתן - פסיכולוג חינוכי וירטואלי (גרסה 3.1) ==========")
    print("✅ מודל הבינה המלאכותית: נטען")
    print("✅ הגבלת קצב: פעיל")
    print("🚀 השרת פועל על: http://localhost:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True)