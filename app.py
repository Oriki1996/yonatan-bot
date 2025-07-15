# app.py - v22.0 - Production Ready with Enhanced Security and Advanced Fallback System
import os
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from flask import Flask, jsonify, render_template, request, Response, stream_with_context, session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from marshmallow import Schema, fields, ValidationError as MarshmallowValidationError
from models import db, Parent, Child, Conversation, Message, QuestionnaireResponse, init_app_db
import google.generativeai as genai
from sqlalchemy.exc import SQLAlchemyError
from uuid import uuid4
from config import config_by_name

# Import custom modules
from errors import *
from utils import *

# יבוא המערכת המתקדמת
try:
    from advanced_fallback_system import AdvancedFallbackSystem, ResponseContext
    ADVANCED_FALLBACK_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ לא ניתן לטעון את המערכת המתקדמת: {e}")
    ADVANCED_FALLBACK_AVAILABLE = False

# --- Environment Validation ---
def validate_environment():
    """בדיקת משתני סביבה חיוניים"""
    required_vars = {
        'SECRET_KEY': 'מפתח סודי לFlask',
        'GOOGLE_API_KEY': 'מפתח Google API'
    }
    
    missing = []
    for var, description in required_vars.items():
        if not os.environ.get(var):
            missing.append(f"{var} ({description})")
    
    if missing:
        print("❌ חסרים משתני סביבה:")
        for var in missing:
            print(f"   - {var}")
        if os.environ.get('FLASK_ENV') == 'production':
            raise ConfigurationError("משתני סביבה חיוניים חסרים בפרודקשן")
        else:
            print("⚠️ ממשיך במצב פיתוח ללא משתני סביבה")

# Validate environment
validate_environment()

# --- App Initialization & Config ---
env = os.environ.get('FLASK_ENV', 'production')
app = Flask(__name__)
app.config.from_object(config_by_name.get(env, config_by_name['production']))

# --- Security Configuration ---
csrf = CSRFProtect(app)
csrf.init_app(app)

# --- Logging Configuration ---
if not os.path.exists('logs'):
    os.makedirs('logs')

# הגדרת רמת לוגים
log_level = getattr(logging, os.environ.get('LOG_LEVEL', 'INFO').upper())
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/yonatan.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"Flask environment set to: {env}")

# --- Rate Limiting Configuration ---
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per day", "100 per hour"],
    storage_uri=os.environ.get('RATELIMIT_STORAGE_URL', 'memory://'),
    headers_enabled=True
)

# --- Database Initialization ---
init_app_db(app)
CORS(app, origins=["http://localhost:5000", "https://yonatan-bot.onrender.com"])

# --- AI Model Configuration ---
model = None
ai_model_available = False
try:
    api_key = app.config.get('GOOGLE_API_KEY')
    if not api_key:
        logger.error("GOOGLE_API_KEY לא נמצא בהגדרות! הצ'אט בוט יפעל במצב fallback.")
    else:
        genai.configure(api_key=api_key)
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            # בדיקה קצרה שהמודל עובד
            test_response = model.generate_content("בדיקה")
            if test_response and test_response.text:
                logger.info("✅ מודל Google AI הוגדר והופעל בהצלחה.")
                ai_model_available = True
            else:
                raise Exception("המודל לא מחזיר תגובה תקינה")
        except Exception as model_error:
            logger.error(f"❌ שגיאה בהפעלת מודל ה-AI: {model_error}")
            model = None
            ai_model_available = False
except Exception as e:
    logger.error(f"❌ שגיאה בהגדרת מודל ה-AI של Google: {e}")
    model = None
    ai_model_available = False

# --- Advanced Fallback System Initialization ---
advanced_fallback_system = None
advanced_fallback_available = False

if ADVANCED_FALLBACK_AVAILABLE:
    try:
        advanced_fallback_system = AdvancedFallbackSystem()
        advanced_fallback_available = True
        logger.info("🚀 מערכת Fallback מתקדמת הופעלה בהצלחה!")
    except Exception as e:
        logger.error(f"❌ שגיאה בהפעלת מערכת Fallback מתקדמת: {e}")
        advanced_fallback_system = None
        advanced_fallback_available = False
else:
    logger.warning("⚠️ מערכת Fallback מתקדמת לא זמינה")

# --- Session Configuration ---
SESSION_TIMEOUT = timedelta(minutes=int(os.environ.get('SESSION_TIMEOUT', '30')))
chat_sessions = {}
session_contexts = {}

# --- Input Validation Schemas ---
class ChatMessageSchema(Schema):
    session_id = fields.Str(required=True, validate=lambda x: validate_session_id(x))
    message = fields.Str(required=True, validate=lambda x: 0 < len(x) <= 5000)

class QuestionnaireSchema(Schema):
    session_id = fields.Str(required=True, validate=lambda x: validate_session_id(x))
    parent_name = fields.Str(required=True, validate=lambda x: validate_name(x))
    parent_gender = fields.Str(required=True, validate=lambda x: x in ['אבא', 'אמא', 'אחר'])
    child_name = fields.Str(required=True, validate=lambda x: validate_name(x))
    child_age = fields.Int(required=True, validate=lambda x: validate_age(x))
    child_gender = fields.Str(required=True, validate=lambda x: x in ['בן', 'בת', 'אחר'])
    main_challenge = fields.Str(required=True, validate=lambda x: len(x) > 0)
    previous_attempts = fields.Str(missing='')
    additional_info = fields.Str(missing='')

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
def validate_session(session_id: str) -> bool:
    """בדוק שהסשן קיים במערכת"""
    if not session_id or not validate_session_id(session_id):
        return False
    try:
        parent = db.session.get(Parent, session_id)
        return parent is not None
    except Exception as e:
        logger.error(f"Error validating session {session_id}: {e}")
        return False

def ensure_db_connection() -> bool:
    """וודא שיש חיבור לבסיס הנתונים"""
    try:
        db.session.execute(db.text("SELECT 1"))
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return False

def get_session_context(session_id: str) -> ResponseContext:
    """קבלת קונטקסט הסשן מהזיכרון או מבסיס הנתונים"""
    if session_id in session_contexts:
        return session_contexts[session_id]
    
    # טעינה מבסיס הנתונים
    try:
        parent = db.session.get(Parent, session_id)
        child = Child.query.filter_by(parent_id=session_id).first()
        questionnaire = QuestionnaireResponse.query.filter_by(parent_id=session_id).first()
        
        if questionnaire:
            questionnaire_data = json.loads(questionnaire.response_data)
        else:
            questionnaire_data = {}
        
        context = ResponseContext(
            parent_name=parent.name if parent else "הורה יקר",
            child_name=child.name if child else "המתבגר שלך",
            child_age=child.age if child else 15,
            main_challenge=questionnaire_data.get('main_challenge', 'תקשורת וריבים'),
            child_gender=child.gender if child else "לא צוין"
        )
        
        session_contexts[session_id] = context
        return context
        
    except Exception as e:
        logger.error(f"Error loading session context: {e}")
        return ResponseContext()

def detect_quota_exceeded_error(error_str: str) -> bool:
    """זיהוי שגיאות quota"""
    quota_indicators = [
        "429", "quota", "exceeded", "rate limit", "too many requests",
        "resource_exhausted", "quota_exceeded", "rate_limit_exceeded"
    ]
    error_lower = error_str.lower()
    return any(indicator in error_lower for indicator in quota_indicators)

def get_system_mode() -> str:
    """קביעת מצב המערכת הנוכחי"""
    if ai_model_available and model:
        return "full_ai"
    elif advanced_fallback_available:
        return "advanced_fallback_mode"
    else:
        return "degraded"

def cleanup_expired_sessions():
    """נקה סשנים שפג תוקפם"""
    current_time = datetime.now()
    expired_sessions = []
    
    for session_id, session_data in chat_sessions.items():
        last_activity = session_data.get('last_activity', current_time)
        if current_time - last_activity > SESSION_TIMEOUT:
            expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        if session_id in chat_sessions:
            del chat_sessions[session_id]
        if session_id in session_contexts:
            del session_contexts[session_id]
    
    if expired_sessions:
        logger.info(f"נוקו {len(expired_sessions)} סשנים שפג תוקפם")

def generate_and_save_with_advanced_fallback(stream, session_id: str, user_message: str):
    """גנרציה עם fallback מתקדם אוטומטי במקרה של שגיאה"""
    full_response_text = []
    is_fallback_used = False
    
    try:
        for chunk in stream:
            if chunk.text:
                full_response_text.append(chunk.text)
                yield chunk.text
                
    except Exception as e:
        error_str = str(e)
        logger.error(f"שגיאה במהלך סטרימינג: {e}")
        
        # בדיקה אם זו שגיאת quota או שגיאה אחרת
        if detect_quota_exceeded_error(error_str):
            logger.info("זוהתה שגיאת quota - עובר למצב fallback מתקדם")
        else:
            logger.error(f"שגיאה לא צפויה במהלך סטרימינג: {e}")
        
        # מחיקת תוכן קיים אם יש
        if full_response_text:
            full_response_text.clear()
        
        # קבלת תשובה מהמערכת המתקדמת
        if advanced_fallback_system:
            try:
                context = get_session_context(session_id)
                questionnaire_data = None
                
                # נסה לקבל נתוני שאלון
                try:
                    questionnaire = QuestionnaireResponse.query.filter_by(parent_id=session_id).first()
                    if questionnaire:
                        questionnaire_data = json.loads(questionnaire.response_data)
                except:
                    pass
                
                fallback_response = advanced_fallback_system.get_fallback_response(
                    user_message, session_id, questionnaire_data
                )
                full_response_text.append(fallback_response)
                is_fallback_used = True
                yield fallback_response
                
            except Exception as fallback_error:
                logger.error(f"שגיאה במערכת fallback מתקדמת: {fallback_error}")
                error_message = "אני מתנצל, המערכת עמוסה כרגע. אנא נסה שוב מאוחר יותר."
                full_response_text.append(error_message)
                yield error_message
        else:
            error_message = "אני מתנצל, המערכת לא זמינה כרגע. אנא נסה שוב מאוחר יותר."
            full_response_text.append(error_message)
            yield error_message
    
    final_text = "".join(full_response_text)
    
    # שמירה למסד הנתונים (רק אם יש תוכן)
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
                
                if is_fallback_used:
                    logger.info(f"תשובת fallback מתקדמת נשמרה עבור סשן {session_id}")
                else:
                    logger.info(f"תשובת בוט נשמרה עבור סשן {session_id}")
                    
        except Exception as db_err:
            logger.error(f"שגיאה בשמירת תשובה למסד הנתונים: {db_err}")

# --- Security Middleware ---
@app.before_request
def security_checks():
    """בדיקות אבטחה לפני כל בקשה"""
    # ניקוי סשנים פגי תוקף
    cleanup_expired_sessions()
    
    # בדיקת גודל הבקשה
    if not validate_request_size():
        raise ValidationError("בקשה גדולה מדי")
    
    # בדיקת בקשה חשודה
    if is_suspicious_request():
        log_security_event("suspicious_request", {
            "ip": get_client_ip(),
            "user_agent": get_user_agent(),
            "path": request.path
        })
        # לא חוסמים אוטומטית, רק מתעדים
    
    # בדיקת CSRF למתודות POST
    if request.method == "POST" and not request.path.startswith('/api/'):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            raise SecurityError("בקשה חשודה נחסמה")

# --- Error Handlers ---
@app.errorhandler(BotError)
def handle_bot_error(error):
    """טיפול בשגיאות הבוט"""
    logger.error(f"Bot Error: {error}")
    return jsonify(error.to_dict()), error.status_code

@app.errorhandler(MarshmallowValidationError)
def handle_validation_error(error):
    """טיפול בשגיאות validation"""
    logger.warning(f"Validation Error: {error.messages}")
    return jsonify({
        "error": "נתונים לא תקינים",
        "details": error.messages
    }), 400

@app.errorhandler(429)
def handle_rate_limit(error):
    """טיפול בrate limiting"""
    logger.warning(f"Rate limit exceeded: {get_client_ip()}")
    return jsonify({
        "error": "יותר מדי בקשות, נסה שוב מאוחר יותר",
        "retry_after": "60"
    }), 429

@app.errorhandler(404)
def not_found(error):
    """טיפול בדפים לא נמצאו"""
    return jsonify({"error": "נתיב לא נמצא"}), 404

@app.errorhandler(500)
def internal_error(error):
    """טיפול בשגיאות פנימיות"""
    error_id = create_error_id()
    logger.error(f"Internal error {error_id}: {error}")
    return jsonify({
        "error": "שגיאה פנימית במערכת",
        "error_id": error_id
    }), 500

# --- API Endpoints ---
@app.route('/api/health', methods=['GET'])
def api_health():
    """נקודת קצה לבדיקת תקינות המערכת עם fallback מתקדם"""
    health_status = {
        "status": "ok",
        "api_running": True,
        "database_connected": False,
        "ai_model_configured": model is not None,
        "ai_model_working": False,
        "advanced_fallback_available": advanced_fallback_available,
        "advanced_fallback_working": False,
        "system_mode": get_system_mode(),
        "timestamp": datetime.utcnow().isoformat(),
        "environment": env,
        "session_count": len(chat_sessions)
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
            
            # בדיקה אם זו שגיאת quota
            if detect_quota_exceeded_error(str(e)):
                health_status["quota_exceeded"] = True
                health_status["fallback_active"] = True
    
    # בדיקת מערכת fallback מתקדמת
    if advanced_fallback_system:
        try:
            test_fallback = advanced_fallback_system.get_fallback_response(
                "בדיקה",
                session_id="health_check_session",
                questionnaire_data={
                    "parent_name": "test_parent",
                    "child_name": "test_child",
                    "child_age": 15,
                    "main_challenge": "תקשורת וריבים"
                }
            )
            health_status["advanced_fallback_working"] = bool(test_fallback and len(test_fallback) > 0)
            
        except Exception as e:
            logger.error(f"Advanced fallback system test error: {e}")
            health_status["advanced_fallback_working"] = False
            health_status["advanced_fallback_error"] = str(e)
    
    # קביעת סטטוס כללי
    core_systems_ok = health_status["database_connected"]
    ai_or_fallback_ok = health_status["ai_model_working"] or health_status["advanced_fallback_working"]
    
    all_systems_ok = core_systems_ok and ai_or_fallback_ok
    
    if not all_systems_ok:
        if core_systems_ok and health_status["advanced_fallback_working"]:
            health_status["status"] = "advanced_fallback_mode"
        else:
            health_status["status"] = "degraded"
    
    status_code = 200 if all_systems_ok or health_status["status"] == "advanced_fallback_mode" else 503
    return jsonify(health_status), status_code

@app.route('/api/init', methods=['POST'])
@limiter.limit("5 per minute")
def init_session():
    """אתחול סשן חדש"""
    session_id = generate_secure_session_id()
    
    try:
        # בדיקה שבסיס הנתונים מחובר
        if not ensure_db_connection():
            raise DatabaseError("שגיאה בחיבור לבסיס הנתונים")
        
        parent = Parent(id=session_id, name="אורח", gender="לא צוין")
        db.session.add(parent)
        db.session.commit()
        
        # יצירת CSRF token
        csrf_token = generate_csrf_token()
        session['csrf_token'] = csrf_token
        
        logger.info(f"✅ סשן חדש נוצר עם מזהה: {session_id}")
        
        return jsonify({
            "session_id": session_id,
            "status": "new_user",
            "system_mode": get_system_mode(),
            "advanced_fallback_available": advanced_fallback_available,
            "csrf_token": csrf_token
        })
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"שגיאת מסד נתונים באתחול: {e}")
        raise DatabaseError("לא ניתן לאתחל סשן")
    except Exception as e:
        db.session.rollback()
        logger.error(f"שגיאה כללית באתחול: {e}")
        raise BotError("שגיאה פנימית במערכת")

@app.route('/api/questionnaire', methods=['POST'])
@limiter.limit("10 per minute")
def handle_questionnaire():
    """טיפול בנתוני השאלון"""
    try:
        # Validation
        schema = QuestionnaireSchema()
        data = schema.load(request.get_json())
        
        session_id = data['session_id']
        
        if not validate_session(session_id):
            raise SessionNotFoundError("מזהה סשן לא תקין")
            
        parent = db.session.get(Parent, session_id)
        if not parent:
            raise ParentNotFoundError("משתמש לא נמצא")
        
        # Sanitization
        data['parent_name'] = sanitize_input(data['parent_name'])
        data['child_name'] = sanitize_input(data['child_name'])
        data['previous_attempts'] = sanitize_input(data.get('previous_attempts', ''))
        data['additional_info'] = sanitize_input(data.get('additional_info', ''))
        
        # עדכון נתוני ההורה
        parent.name = data['parent_name']
        parent.gender = data['parent_gender']
        
        # יצירת ילד
        child = Child(
            name=data['child_name'],
            age=data['child_age'],
            gender=data['child_gender'],
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
        
        # יצירת קונטקסט הסשן
        context = ResponseContext(
            parent_name=parent.name,
            child_name=child.name,
            child_age=child.age,
            main_challenge=data['main_challenge'],
            child_gender=child.gender
        )
        session_contexts[session_id] = context
        
        logger.info(f"✅ נתוני שאלון נשמרו עבור סשן: {session_id}")
        return jsonify({
            "status": "success",
            "system_mode": get_system_mode()
        })
        
    except MarshmallowValidationError as e:
        raise ValidationError("נתונים לא תקינים", error_details=e.messages)
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"שגיאה בשמירת שאלון: {e}")
        raise DatabaseError("לא ניתן לשמור את נתוני השאלון")
    except Exception as e:
        db.session.rollback()
        logger.error(f"שגיאה כללית בשאלון: {e}")
        raise BotError("שגיאה פנימית במערכת")

@app.route('/api/chat', methods=['POST'])
@limiter.limit("30 per minute")
def chat():
    """נקודת קצה לצ'אט עם תמיכה ב-fallback מתקדם"""
    try:
        # Validation
        schema = ChatMessageSchema()
        data = schema.load(request.get_json())
        
        session_id = data['session_id']
        user_message = sanitize_input(data['message'])
        
        if not validate_session(session_id):
            raise SessionNotFoundError("סשן לא תקין או פג תוקף")
        
        # בדיקה מיוחדת: אם אין מודל AI ואין מערכת fallback
        if not model and not advanced_fallback_system:
            logger.error("אין מודל AI ואין מערכת fallback זמינה")
            raise BotError("המערכת לא זמינה כרגע")

        # אם אין מודל AI, עבור ישירות ל-fallback מתקדם
        if not model or not ai_model_available:
            logger.info("מודל AI לא זמין - עובר ישירות למצב fallback מתקדם")
            
            # שמירת הודעת המשתמש
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
                except Exception as e:
                    logger.error(f"שגיאה בשמירת הודעת משתמש: {e}")
            
            # קבלת תשובת fallback מתקדמת
            if advanced_fallback_system:
                try:
                    questionnaire_data = None
                    try:
                        questionnaire = QuestionnaireResponse.query.filter_by(parent_id=session_id).first()
                        if questionnaire:
                            questionnaire_data = json.loads(questionnaire.response_data)
                    except:
                        pass
                        
                    fallback_response = advanced_fallback_system.get_fallback_response(
                        user_message, session_id, questionnaire_data
                    )
                    
                    logger.info(f"✅ תשובת fallback מתקדמת נוצרה עבור סשן {session_id}")
                    
                except Exception as fb_error:
                    logger.error(f"שגיאה במערכת fallback מתקדמת: {fb_error}")
                    raise FallbackSystemError("מערכת הגיבוי לא זמינה")
            else:
                raise BotError("המערכת לא זמינה כרגע")
            
            def generate_advanced_fallback():
                yield fallback_response
                
                # שמירה למסד הנתונים
                try:
                    db_conv = Conversation.query.filter_by(parent_id=session_id).first()
                    if db_conv:
                        ai_msg_db = Message(
                            conversation_id=db_conv.id,
                            sender_type='bot',
                            content=fallback_response
                        )
                        db.session.add(ai_msg_db)
                        db.session.commit()
                        logger.info(f"✅ תשובת fallback מתקדמת (ללא AI) נשמרה עבור סשן {session_id}")
                except Exception as db_err:
                    logger.error(f"שגיאה בשמירת תשובת fallback: {db_err}")
            
            return Response(
                stream_with_context(generate_advanced_fallback()),
                mimetype='text/plain',
                headers={'Cache-Control': 'no-cache'}
            )

        # המשך התהליך הרגיל עם AI + fallback מתקדם
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
                chat_sessions[session_id] = {
                    'chat': model.start_chat(
                        history=history,
                        system_instruction=f"{CBT_SYSTEM_PROMPT}\n{context}"
                    ),
                    'last_activity': datetime.now()
                }
                logger.info(f"✅ סשן צ'אט נוצר בהצלחה עבור {session_id}")
            except Exception as e:
                logger.error(f"שגיאה ביצירת סשן צ'אט: {e}")
                raise AIModelError("לא ניתן ליצור סשן צ'אט")
        
        active_chat = chat_sessions[session_id]['chat']
        
        # עדכון זמן פעילות
        chat_sessions[session_id]['last_activity'] = datetime.now()
        
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
                logger.info(f"✅ הודעת משתמש נשמרה עבור סשן {session_id}")
            except Exception as e:
                logger.error(f"שגיאה בשמירת הודעת משתמש: {e}")

        # שליחת הודעה למודל עם טיפול חכם בשגיאות
        try:
            stream = active_chat.send_message(user_message, stream=True)
            logger.info(f"✅ הודעה נשלחה למודל ה-AI עבור סשן {session_id}")
        except Exception as e:
            logger.error(f"שגיאה בשליחת הודעה למודל: {e}")
            
            # בדיקה אם זו שגיאת quota או אחרת
            error_str = str(e)
            if detect_quota_exceeded_error(error_str):
                logger.info("זוהתה שגיאת quota בשליחת הודעה - עובר למצב fallback מתקדם")
                raise QuotaExceededError("המערכת עמוסה, אנא נסה שוב מאוחר יותר")
            else:
                raise AIModelError("לא ניתן לשלוח הודעה למודל")

        return Response(
            stream_with_context(generate_and_save_with_advanced_fallback(stream, session_id, user_message)),
            mimetype='text/plain',
            headers={'Cache-Control': 'no-cache'}
        )

    except MarshmallowValidationError as e:
        raise ValidationError("נתונים לא תקינים", error_details=e.messages)
    except Exception as e:
        logger.error(f"שגיאה כללית בנקודת קצה chat: {e}", exc_info=True)
        # אל תחשוף שגיאה טכנית למשתמש
        raise BotError("שגיאה פנימית במערכת")

@app.route('/api/reset_session', methods=['POST'])
@limiter.limit("5 per minute")
def reset_session():
    """איפוס סשן צ'אט"""
    try:
        schema = ChatMessageSchema()
        data = schema.load(request.get_json())
        session_id = data['session_id']
        
        if not validate_session(session_id):
            raise SessionNotFoundError("סשן לא תקין")
        
        # ניקוי הסשן מהזיכרון
        if session_id in chat_sessions:
            del chat_sessions[session_id]
            logger.info(f"✅ סשן צ'אט {session_id} נוקה מהזיכרון")
        
        if session_id in session_contexts:
            del session_contexts[session_id]
            logger.info(f"✅ קונטקסט סשן {session_id} נוקה מהזיכרון")
        
        # איפוס היסטוריית הfallback במערכת fallback
        if advanced_fallback_system and session_id in advanced_fallback_system.conversation_state:
            del advanced_fallback_system.conversation_state[session_id]
            logger.info(f"✅ היסטוריית fallback לסשן {session_id} נוקתה")
        
        return jsonify({
            "status": "success",
            "message": "הסשן אופס בהצלחה"
        })
        
    except MarshmallowValidationError as e:
        raise ValidationError("נתונים לא תקינים", error_details=e.messages)
    except Exception as e:
        logger.error(f"שגיאה באיפוס סשן: {e}")
        raise BotError("שגיאה באיפוס סשן")

@app.route('/api/session_analysis/<session_id>', methods=['GET'])
@limiter.limit("10 per minute")
def get_session_analysis(session_id: str):
    """ניתוח פאטרנס השיחה (לצורכי דיבוג ושיפור)"""
    try:
        if not validate_session(session_id):
            raise SessionNotFoundError("סשן לא תקין")
        
        if advanced_fallback_system:
            analysis = advanced_fallback_system.analyze_conversation_pattern(session_id)
            return jsonify(analysis)
        else:
            raise BotError("מערכת ניתוח לא זמינה")
            
    except Exception as e:
        logger.error(f"שגיאה בניתוח סשן: {e}")
        raise BotError("שגיאה בניתוח")

@app.route('/api/session_summary/<session_id>', methods=['GET'])
@limiter.limit("10 per minute")
def get_session_summary(session_id: str):
    """קבלת סיכום אישי של השיחה"""
    try:
        if not validate_session(session_id):
            raise SessionNotFoundError("סשן לא תקין")
        
        if advanced_fallback_system:
            context = get_session_context(session_id)
            summary = advanced_fallback_system.generate_personalized_summary(session_id, context)
            return jsonify({"summary": summary})
        else:
            raise BotError("מערכת סיכום לא זמינה")
            
    except Exception as e:
        logger.error(f"שגיאה בסיכום סשן: {e}")
        raise BotError("שגיאה בסיכום")

# --- Frontend Serving ---
@app.route('/')
def serve_main_landing():
    """דף הבית"""
    return render_template('index.html')

@app.route('/<page_name>.html')
def serve_other_html(page_name):
    """דפים סטטיים נוספים"""
    # בדיקת אבטחה - רק שמות קבצים תקינים
    if not re.match(r'^[a-zA-Z0-9_-]+$', page_name):
        return "Page not found", 404
        
    try:
        return render_template(f'{page_name}.html')
    except Exception as e:
        logger.error(f"לא ניתן לטעון דף {page_name}: {e}")
        return "Page not found", 404

# --- App Info ---
@app.route('/api/info', methods=['GET'])
def get_app_info():
    """מידע על המערכת"""
    return jsonify({
        "name": "יונתן הפסיכו-בוט",
        "version": "22.0",
        "system_mode": get_system_mode(),
        "features": {
            "ai_model": ai_model_available,
            "advanced_fallback": advanced_fallback_available,
            "database": ensure_db_connection(),
            "rate_limiting": True,
            "csrf_protection": True,
            "input_validation": True
        },
        "cbt_techniques": list(advanced_fallback_system.cbt_techniques.keys()) if advanced_fallback_system else [],
        "challenge_categories": list(advanced_fallback_system.challenge_database.keys()) if advanced_fallback_system else [],
        "session_timeout_minutes": int(SESSION_TIMEOUT.total_seconds() / 60),
        "max_message_length": 5000
    })

# --- Cleanup on Shutdown ---
@app.teardown_appcontext
def cleanup_resources(exception):
    """ניקוי משאבים"""
    if exception:
        logger.error(f"App context teardown with exception: {exception}")
        db.session.rollback()
    else:
        db.session.commit()

if __name__ == '__main__':
    # הרצה לפיתוח בלבד - Gunicorn ישתמש באפליקציה ישירות
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000,
        threaded=True
    )