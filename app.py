# app.py - v18.0 - Production Ready with Fixes
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
from config import config_by_name

# --- App Initialization & Config ---
env = os.environ.get('FLASK_ENV', 'production')
app = Flask(__name__)
app.config.from_object(config_by_name.get(env, config_by_name['production']))

# Initialize logging
logging.basicConfig(
    level=logging.INFO if not app.config.get('DEBUG', False) else logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info(f"Flask environment set to: {env}")
logger.info(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI'][:20]}...")

# Initialize extensions
init_app_db(app)
CORS(app)

# --- AI Model Configuration ---
model = None
try:
    api_key = app.config.get('GOOGLE_API_KEY')
    if not api_key:
        logger.error("GOOGLE_API_KEY לא נמצא בהגדרות! הצ'אט בוט לא יפעל.")
    else:
        genai.configure(api_key=api_key)
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            # בדיקה קצרה שהמודל עובד
            test_response = model.generate_content("בדיקה")
            if test_response and test_response.text:
                logger.info("מודל Google AI הוגדר והופעל בהצלחה.")
            else:
                raise Exception("המודל לא מחזיר תגובה תקינה")
        except Exception as model_error:
            logger.error(f"שגיאה בהפעלת מודל ה-AI: {model_error}")
            model = None
except Exception as e:
    logger.error(f"שגיאה בהגדרת מודל ה-AI של Google: {e}")
    model = None

# --- In-Memory Session Storage ---
chat_sessions = {}

# --- CBT System Prompt ---
CBT_SYSTEM_PROMPT = """
אתה "יונתן", פסיכו-בוט חינוכי דיגיטלי, המבוסס על עקרונות טיפול קוגניטיבי-התנהגותי (CBT).
תפקידך הוא לסייע להורים למתבגרים. אתה אמפתי, מקצועי, ופרקטי.
המשתמש הוא הורה. פרטיו, פרטי ילדו, ותשובותיו לשאלון ראשוני יסופקו לך.

הנחיות הפעולה שלך:
1. **הודעת פתיחה חכמה:** אם הודעת המשתמש היא "START_CONVERSATION", תפקידך הוא להתחיל את השיחה. פנה להורה בשמו, ציין את האתגר המרכזי מהשאלון, והצע לו מיד שתי דרכים להתחיל.
2. **מסגור CBT:** הסבר בקצרה את מודל אפר"ת. כשאתה מסביר מושג מפתח, השתמש בתחביר: `CARD[כותרת|תוכן]`.
3. **חקירה סוקרטית:** השתמש בשאלות פתוחות לחקור מחשבות אוטומטיות.
4. **הצעת כלים:** הצע כלים בסוגריים מרובעים כמו [טבלת המחשבות].
5. **שמירה על מיקוד:** החזר לנושא בעדינות אם יש סטייה.
6. **שפה דינמית:** גוון את תגובותיך, היה תמציתי.
"""

# --- Helper Functions ---
def validate_session(session_id):
    """בדוק שהסשן קיים במערכת"""
    if not session_id:
        return False
    try:
        parent = db.session.get(Parent, session_id)
        return parent is not None
    except Exception as e:
        logger.error(f"Error validating session {session_id}: {e}")
        return False

def ensure_db_connection():
    """וודא שיש חיבור לבסיס הנתונים"""
    try:
        db.session.execute(db.text("SELECT 1"))
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return False

# --- API Endpoints ---
@app.route('/api/health', methods=['GET'])
def api_health():
    """נקודת קצה לבדיקת תקינות המערכת"""
    health_status = {
        "status": "ok",
        "api_running": True,
        "database_connected": False,
        "ai_model_configured": model is not None,
        "ai_model_working": False,
        "timestamp": datetime.utcnow().isoformat(),
        "environment": env
    }
    
    # בדיקת חיבור למסד הנתונים
    health_status["database_connected"] = ensure_db_connection()
    
    # בדיקת המודל
    if model:
        try:
            test_response = model.generate_content("בדיקה")
            health_status["ai_model_working"] = bool(test_response and test_response.text)
        except Exception as e:
            logger.error(f"AI model test error: {e}")
            health_status["ai_model_working"] = False
            health_status["ai_model_error"] = str(e)
    
    # קביעת סטטוס כללי
    all_systems_ok = (
        health_status["database_connected"] and 
        health_status["ai_model_configured"] and 
        health_status["ai_model_working"]
    )
    
    if not all_systems_ok:
        health_status["status"] = "degraded"
    
    status_code = 200 if all_systems_ok else 503
    return jsonify(health_status), status_code

@app.route('/api/init', methods=['POST'])
def init_session():
    """אתחול סשן חדש"""
    session_id = str(uuid4())
    try:
        # בדיקה שבסיס הנתונים מחובר
        if not ensure_db_connection():
            return jsonify({"error": "שגיאה בחיבור לבסיס הנתונים"}), 503
        
        parent = Parent(id=session_id, name="אורח", gender="לא צוין")
        db.session.add(parent)
        db.session.commit()
        logger.info(f"סשן חדש נוצר עם מזהה: {session_id}")
        return jsonify({"session_id": session_id, "status": "new_user"})
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"שגיאת מסד נתונים באתחול: {e}")
        return jsonify({"error": "לא ניתן לאתחל סשן"}), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"שגיאה כללית באתחול: {e}")
        return jsonify({"error": "שגיאה פנימית במערכת"}), 500

@app.route('/api/questionnaire', methods=['POST'])
def handle_questionnaire():
    """טיפול בנתוני השאלון"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "נתונים חסרים"}), 400
            
        session_id = data.get('session_id')
        if not session_id or not validate_session(session_id):
            return jsonify({"error": "מזהה סשן לא תקין"}), 404
            
        parent = db.session.get(Parent, session_id)
        if not parent:
            return jsonify({"error": "משתמש לא נמצא"}), 404
            
        # עדכון נתוני ההורה
        parent.name = data.get('parent_name', 'לא צוין')
        parent.gender = data.get('parent_gender', 'לא צוין')
        
        # יצירת ילד
        child = Child(
            name=data.get('child_name', 'לא צוין'),
            age=int(data.get('child_age', 0)),
            gender=data.get('child_gender', 'לא צוין'),
            parent_id=session_id
        )
        db.session.add(child)
        db.session.flush()
        
        # שמירת תשובות השאלון
        response = QuestionnaireResponse(
            parent_id=session_id,
            child_id=child.id,
            response_data=json.dumps(data, ensure_ascii=False)
        )
        db.session.add(response)
        db.session.commit()
        
        logger.info(f"נתוני שאלון נשמרו עבור סשן: {session_id}")
        return jsonify({"status": "success"})
        
    except (KeyError, ValueError, TypeError) as e:
        db.session.rollback()
        logger.error(f"שגיאה בנתוני השאלון: {e}")
        return jsonify({"error": "נתונים לא תקינים"}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"שגיאה בשמירת שאלון: {e}")
        return jsonify({"error": "לא ניתן לשמור את נתוני השאלון"}), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"שגיאה כללית בשאלון: {e}")
        return jsonify({"error": "שגיאה פנימית במערכת"}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """נקודת קצה לצ'אט"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "נתונים חסרים"}), 400
            
        session_id = data.get('session_id')
        user_message = data.get('message')

        if not session_id or not user_message:
            return jsonify({"error": "חסרים נתונים חובה"}), 400
        
        if not validate_session(session_id):
            return jsonify({"error": "סשן לא תקין או פג תוקף"}), 404
        
        if not model:
            return jsonify({"error": "מודל ה-AI לא זמין כעת"}), 503

        # יצירת או קבלת סשן צ'אט
        if session_id not in chat_sessions:
            logger.info(f"יוצר סשן צ'אט חדש עבור session_id: {session_id}")
            
            # קבלת קונטקסט המשתמש
            parent = db.session.get(Parent, session_id)
            child = Child.query.filter_by(parent_id=session_id).first()
            questionnaire = QuestionnaireResponse.query.filter_by(parent_id=session_id).first()
            
            context = f"""--- CONTEXT ---
Parent Name: {parent.name if parent else 'N/A'}
Child Name: {child.name if child else 'N/A'}
Child Age: {child.age if child else 'N/A'}
Initial Questionnaire: {json.loads(questionnaire.response_data) if questionnaire else 'N/A'}
--- END CONTEXT ---"""
            
            # קבלת היסטורית הודעות קיימת
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
                return jsonify({"error": "לא ניתן ליצור סשן צ'אט"}), 500
        
        active_chat = chat_sessions[session_id]
        
        # שמירת הודעת המשתמש (אם זה לא START_CONVERSATION)
        if user_message != "START_CONVERSATION":
            try:
                db_conversation = Conversation.query.filter_by(parent_id=session_id).first()
                if not db_conversation:
                    child = Child.query.filter_by(parent_id=session_id).first()
                    db_conversation = Conversation(
                        parent_id=session_id,
                        child_id=child.id if child else None,
                        topic="General"
                    )
                    db.session.add(db_conversation)
                    db.session.commit()
                    db.session.refresh(db_conversation)
                
                user_msg_db = Message(
                    conversation_id=db_conversation.id,
                    sender_type='user',
                    content=user_message
                )
                db.session.add(user_msg_db)
                db.session.commit()
                logger.info(f"הודעת משתמש נשמרה עבור סשן {session_id}")
            except Exception as e:
                logger.error(f"שגיאה בשמירת הודעת משתמש: {e}")
                # ממשיכים למרות השגיאה

        # שליחת הודעה למודל
        try:
            stream = active_chat.send_message(user_message, stream=True)
            logger.info(f"הודעה נשלחה למודל ה-AI עבור סשן {session_id}")
        except Exception as e:
            logger.error(f"שגיאה בשליחת הודעה למודל: {e}")
            return jsonify({"error": "לא ניתן לשלוח הודעה למודל"}), 500

        def generate_and_save():
            full_response_text = []
            try:
                for chunk in stream:
                    if chunk.text:
                        full_response_text.append(chunk.text)
                        yield chunk.text
            except Exception as e:
                error_message = f"אני מתנצל, התרחשה שגיאה: {str(e)}"
                logger.error(f"שגיאה במהלך סטרימינג: {e}")
                yield error_message
                full_response_text.append(error_message)
            
            final_text = "".join(full_response_text)
            
            # שמירה למסד הנתונים
            if final_text.strip():
                try:
                    db_conv = Conversation.query.filter_by(parent_id=session_id).first()
                    if db_conv:
                        ai_msg_db = Message(
                            conversation_id=db_conv.id,
                            sender_type='bot',
                            content=final_text
                        )
                        db.session.add(ai_msg_db)
                        db.session.commit()
                        logger.info(f"תשובת בוט נשמרה עבור סשן {session_id}")
                except Exception as db_err:
                    logger.error(f"שגיאה בשמירת תשובה למסד הנתונים: {db_err}")

        return Response(
            stream_with_context(generate_and_save()),
            mimetype='text/plain',
            headers={'Cache-Control': 'no-cache'}
        )

    except Exception as e:
        logger.error(f"שגיאה כללית בנקודת קצה chat: {e}", exc_info=True)
        return jsonify({"error": "שגיאה פנימית במערכת"}), 500

@app.route('/api/reset_session', methods=['POST'])
def reset_session():
    """איפוס סשן צ'אט"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "נתונים חסרים"}), 400
            
        session_id = data.get('session_id')
        if not session_id:
            return jsonify({"error": "חסר מזהה סשן"}), 400
        
        # ניקוי הסשן מהזיכרון
        if session_id in chat_sessions:
            del chat_sessions[session_id]
            logger.info(f"סשן {session_id} נוקה מהזיכרון")
        
        return jsonify({"status": "success", "message": "הסשן אופס בהצלחה"})
    except Exception as e:
        logger.error(f"שגיאה באיפוס סשן: {e}")
        return jsonify({"error": "שגיאה באיפוס סשן"}), 500

# --- Frontend Serving ---
@app.route('/')
def serve_main_landing():
    """דף הבית"""
    return render_template('index.html')

@app.route('/<page_name>.html')
def serve_other_html(page_name):
    """דפים סטטיים נוספים"""
    try:
        return render_template(f'{page_name}.html')
    except Exception as e:
        logger.error(f"לא ניתן לטעון דף {page_name}: {e}")
        return "Page not found", 404

# --- Error Handlers ---
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "נתיב לא נמצא"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"שגיאה פנימית: {error}")
    return jsonify({"error": "שגיאה פנימית במערכת"}), 500

if __name__ == '__main__':
    # הרצה לפיתוח בלבד - Gunicorn ישתמש באפליקציה ישירות
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000,
        threaded=True
    )