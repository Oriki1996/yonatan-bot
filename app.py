# app.py - v17.0 - API החדש ושיפורים
import os
import logging
import json
from flask import Flask, jsonify, render_template, request, Response, stream_with_context
from flask_cors import CORS
from models import db, Parent, Child, Conversation, Message, QuestionnaireResponse, init_app_db
import google.generativeai as genai
from sqlalchemy.exc import SQLAlchemyError
from uuid import uuid4
from datetime import datetime
from config import config_by_name # Import the config dictionary

# --- App Initialization & Config ---
# Determine the environment and load the appropriate configuration
env = os.environ.get('FLASK_ENV', 'development')
app = Flask(__name__)
app.config.from_object(config_by_name[env])

# Initialize logging after config is loaded
logging.basicConfig(level=logging.INFO if not app.config['DEBUG'] else logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info(f"Flask environment set to: {env}")

# Initialize extensions
init_app_db(app)
CORS(app)

# --- AI Model Configuration ---
model = None
try:
    api_key = app.config.get('GOOGLE_API_KEY')
    if not api_key:
        logger.warning("GOOGLE_API_KEY לא נמצא. הצ'אט בוט לא יפעל כראוי.")
    else:
        genai.configure(api_key=api_key)
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            # בדיקה קצרה שהמודל עובד
            test_response = model.generate_content("בדיקה")
            if test_response:
                logger.info("מודל Google AI הוגדר והופעל בהצלחה.")
        except Exception as model_error:
            logger.error(f"שגיאה בהפעלת מודל ה-AI: {model_error}")
except Exception as e:
    logger.error(f"שגיאה בהגדרת מודל ה-AI של Google: {e}")

# --- In-Memory Session Storage ---
chat_sessions = {}

# --- CBT System Prompt ---
CBT_SYSTEM_PROMPT = """
אתה "יונתן", פסיכו-בוט חינוכי דיגיטלי, המבוסס על עקרונות טיפול קוגניטיבי-התנהגותי (CBT).
תפקידך הוא לסייע להורים למתבגרים. אתה אמפתי, מקצועי, ופרקטי.
המשתמש הוא הורה. פרטיו, פרטי ילדו, ותשובותיו לשאלון ראשוני יסופקו לך.

הנחיות הפעולה שלך:
1.  **הודעת פתיחה חכמה:** אם הודעת המשתמש היא "START_CONVERSATION", תפקידך הוא להתחיל את השיחה. פנה להורה בשמו, ציין את האתגר המרכזי מהשאלון, והצע לו מיד שתי דרכים להתחיל. למשל: "שלום אורי, אני מבין שהאתגר הוא **תקשורת וריבים**. בוא נתחיל. [ספר לי על מקרה ספציפי] או [שנבין קודם מושג מפתח]?".
2.  **מסגור CBT:** הסבר בקצרה את מודל אפר"ת. כשאתה מסביר מושג מפתח, השתמש בתחביר מיוחד כדי ליצור כרטיס ויזואלי: `CARD[כותרת הכרטיס|גוף ההסבר. אפשר להשתמש ב-**הדגשות**.]`.
3.  **חקירה סוקרטית:** השתמש בשאלות פתוחות כדי לעזור להורה לחקור את המחשבות האוטומטיות שלו.
4.  **הצעת כלים אינטראקטיביים:** הצע כלים פרקטיים והפוך אותם לבחירות באמצעות סוגריים מרובעים. למשל: "מה דעתך שננסה את [טבלת המחשבות] או שנעדיף [ניסוי התנהגותי]?". אל תציע יותר מ-2-3 אפשרויות בכל פעם.
5.  **שמירה על מיקוד:** אם ההורה גולש לנושאים אחרים, הכר בכך בעדינות והחזר אותו למסלול.
6.  **שפה דינמית:** גוון את תגובותיך. אל תפתח כל הודעה באותה הדרך. היה תמציתי והשתמש בפסקאות קצרות.
"""

# --- נקודת קצה לבדיקת בריאות המערכת ---
@app.route('/api/health', methods=['GET'])
def api_health():
    """נקודת קצה לבדיקת תקינות המערכת"""
    health_status = {
        "status": "ok",
        "api_running": True,
        "database_connected": False,
        "ai_model_configured": model is not None,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # בדיקת חיבור למסד הנתונים
    try:
        db.session.execute("SELECT 1")
        health_status["database_connected"] = True
    except Exception as e:
        health_status["database_error"] = str(e)
    
    # בדיקת המודל
    if model:
        try:
            test_response = model.generate_content("בדיקה")
            health_status["ai_model_working"] = bool(test_response)
        except Exception as e:
            health_status["ai_model_working"] = False
            health_status["ai_model_error"] = str(e)
    
    status_code = 200 if health_status["database_connected"] and health_status.get("ai_model_working", False) else 500
    return jsonify(health_status), status_code

# --- API Endpoints ---
@app.route('/api/init', methods=['POST'])
def init_session():
    session_id = str(uuid4())
    try:
        parent = Parent(id=session_id, name="אורח", gender="לא צוין")
        db.session.add(parent)
        db.session.commit()
        logger.info(f"סשן חדש נוצר עם מזהה: {session_id}")
        return jsonify({"session_id": session_id, "status": "new_user"})
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"שגיאת מסד נתונים באתחול: {e}")
        return jsonify({"error": "לא ניתן לאתחל סשן"}), 500

@app.route('/api/questionnaire', methods=['POST'])
def handle_questionnaire():
    data = request.json
    session_id = data.get('session_id')
    if not session_id: return jsonify({"error": "מזהה סשן חסר"}), 400
    try:
        parent = db.session.get(Parent, session_id)
        if not parent: return jsonify({"error": "מזהה סשן לא תקין"}), 404
        parent.name = data.get('parent_name')
        parent.gender = data.get('parent_gender')
        child = Child(name=data.get('child_name'), age=int(data.get('child_age')), gender=data.get('child_gender'), parent_id=session_id)
        db.session.add(child)
        db.session.flush()
        response = QuestionnaireResponse(parent_id=session_id, child_id=child.id, response_data=json.dumps(data, ensure_ascii=False))
        db.session.add(response)
        db.session.commit()
        logger.info(f"נתוני שאלון נשמרו עבור סשן: {session_id}")
        return jsonify({"status": "success"})
    except (SQLAlchemyError, KeyError, ValueError) as e:
        db.session.rollback()
        logger.error(f"שגיאה בשמירת שאלון: {e}")
        return jsonify({"error": "לא ניתן לשמור את נתוני השאלון"}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    session_id = data.get('session_id')
    user_message = data.get('message')

    if not all([session_id, user_message]):
        return jsonify({"error": "חסרים נתונים."}), 400
    
    if not model:
        return jsonify({"error": "מודל ה-AI לא מוגדר במערכת."}), 503

    try:
        if session_id not in chat_sessions:
            logger.info(f"יוצר סשן צ'אט חדש עבור session_id: {session_id}")
            parent = db.session.get(Parent, session_id)
            if not parent: 
                logger.error(f"לא נמצא משתמש עם session_id: {session_id}")
                return jsonify({"error": "המשתמש לא נמצא"}), 404
                
            child = Child.query.filter_by(parent_id=session_id).first()
            questionnaire = QuestionnaireResponse.query.filter_by(parent_id=session_id).first()
            
            context = f"--- CONTEXT ---\nParent Name: {parent.name}\nChild Name: {child.name if child else 'N/A'}\nChild Age: {child.age if child else 'N/A'}\nInitial Questionnaire Answers: {json.loads(questionnaire.response_data) if questionnaire else 'N/A'}\n--- END CONTEXT ---"
            
            db_conversation = Conversation.query.filter_by(parent_id=session_id).first()
            history = []
            if db_conversation:
                messages = Message.query.filter_by(conversation_id=db_conversation.id).order_by(Message.timestamp.asc()).all()
                for msg in messages:
                    role = 'user' if msg.sender_type == 'user' else 'model'
                    history.append({'role': role, 'parts': [{'text': msg.content}]})

            try:
                chat_sessions[session_id] = model.start_chat(
                    history=history,
                    system_instruction=f"{CBT_SYSTEM_PROMPT}\n{context}"
                )
                logger.info(f"סשן צ'אט נוצר בהצלחה עבור {session_id}")
            except Exception as e:
                logger.error(f"שגיאה ביצירת סשן צ'אט: {e}")
                return jsonify({"error": f"לא ניתן ליצור סשן צ'אט: {str(e)}"}), 500
        
        active_chat = chat_sessions[session_id]
        
        if user_message != "START_CONVERSATION":
            db_conversation = Conversation.query.filter_by(parent_id=session_id).first()
            if not db_conversation:
                child = Child.query.filter_by(parent_id=session_id).first()
                db_conversation = Conversation(parent_id=session_id, child_id=child.id if child else None, topic="General")
                db.session.add(db_conversation)
                db.session.commit()
                db.session.refresh(db_conversation)
            user_msg_db = Message(conversation_id=db_conversation.id, sender_type='user', content=user_message)
            db.session.add(user_msg_db)
            db.session.commit()
            logger.info(f"הודעת משתמש נשמרה עבור סשן {session_id}")

        try:
            stream = active_chat.send_message(user_message, stream=True)
            logger.info(f"הודעה נשלחה למודל ה-AI עבור סשן {session_id}")
        except Exception as e:
            logger.error(f"שגיאה בשליחת הודעה למודל: {e}")
            return jsonify({"error": f"שגיאה בשליחת הודעה למודל: {str(e)}"}), 500

        def generate_and_save():
            full_response_text = []
            try:
                for chunk in stream:
                    if chunk.text:
                        full_response_text.append(chunk.text)
                        yield chunk.text
            except Exception as e:
                error_message = f"אני מתנצל, התרחשה שגיאה במהלך יצירת התשובה: {str(e)}"
                logger.error(f"שגיאה במהלך סטרימינג: {e}")
                yield error_message
                full_response_text.append(error_message)
            
            final_text = "".join(full_response_text)
            
            # שמירה למסד הנתונים רק אם יש טקסט
            if final_text.strip():
                try:
                    db_conv = Conversation.query.filter_by(parent_id=session_id).first()
                    if db_conv:
                        ai_msg_db = Message(conversation_id=db_conv.id, sender_type='bot', content=final_text)
                        db.session.add(ai_msg_db)
                        db.session.commit()
                        logger.info(f"תשובת בוט נשמרה עבור סשן {session_id}")
                except Exception as db_err:
                    logger.error(f"שגיאה בשמירת תשובה למסד הנתונים: {db_err}")

        return Response(stream_with_context(generate_and_save()), mimetype='text/plain')

    except Exception as e:
        logger.error(f"שגיאה כללית בנקודת קצה chat: {e}", exc_info=True)
        return jsonify({"error": f"שגיאה פנימית במערכת: {str(e)}"}), 500

@app.route('/api/reset_session', methods=['POST'])
def reset_session():
    """אפשרות לאיפוס סשן במקרה של תקלה"""
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({"error": "חסר מזהה סשן"}), 400
    
    try:
        # ניקוי הסשן מהזיכרון
        if session_id in chat_sessions:
            del chat_sessions[session_id]
            logger.info(f"סשן {session_id} נוקה מהזיכרון")
        
        return jsonify({"status": "success", "message": "הסשן אופס בהצלחה"})
    except Exception as e:
        logger.error(f"שגיאה באיפוס סשן: {e}")
        return jsonify({"error": f"שגיאה באיפוס סשן: {str(e)}"}), 500

# --- Frontend Serving ---
@app.route('/')
def serve_main_landing():
    return render_template('index.html')

@app.route('/<page_name>.html')
def serve_other_html(page_name):
    try:
        return render_template(f'{page_name}.html')
    except Exception:
        return "Page not found", 404

if __name__ == '__main__':
    # This block is for local development only
    # Gunicorn will not run this
    app.run()