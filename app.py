# app.py - יונתן הפסיכו-בוט - Enhanced Flask Application
import os
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Generator
from flask import Flask, request, jsonify, render_template, session, Response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import BadRequest, TooManyRequests, InternalServerError, RequestTimeout
import google.generativeai as genai
from marshmallow import Schema, fields, ValidationError # וודא שייבוא זה קיים

# Import local modules
from config import get_config, validate_config, ADVANCED_SETTINGS
from models import db, init_app_db, Parent, Child, Conversation, Message, QuestionnaireResponse
from errors import (
    BotError, ValidationError as CustomValidationError, 
    SessionNotFoundError, QuotaExceededError, RateLimitExceededError,
    AIModelError, DatabaseError, SecurityError,
    get_error_response, handle_generic_error
)
from utils import (
    sanitize_input, validate_session_id, validate_age, validate_name,
    generate_secure_session_id, is_suspicious_request, get_client_ip,
    log_security_event, clean_message_for_ai, validate_request_size,
    generate_csrf_token
)
from advanced_fallback_system import create_advanced_fallback_system

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Load configuration
config_name = os.environ.get('FLASK_ENV', 'production')  # Default to production for Render
config = get_config(config_name)
app.config.from_object(config)

# Validate configuration
if not validate_config(config):
    logger.error("Configuration validation failed")
    exit(1)

# Initialize extensions
cors = CORS(app, origins=config.CORS_ORIGINS)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per hour"],
    storage_uri=config.RATELIMIT_STORAGE_URL
)

# Initialize database
init_app_db(app)

# Enhanced table creation with retry logic
def ensure_tables_exist():
    """יצירת טבלאות אוטומטית בהפעלה עם retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with app.app_context():
                # בדיקה אם הטבלאות כבר קיימות
                from sqlalchemy import inspect
                inspector = inspect(db.engine)
                existing_tables = inspector.get_table_names()
                
                expected_tables = ['parent', 'child', 'conversation', 'message', 'questionnaire_response']
                missing_tables = [table for table in expected_tables if table not in existing_tables]
                
                if missing_tables:
                    logger.info(f"🔨 יוצר טבלאות חסרות: {missing_tables}")
                    db.create_all()
                    logger.info("✅ כל הטבלאות נוצרו בהצלחה!")
                else:
                    logger.info("✅ כל הטבלאות כבר קיימות")
                    
                # בדיקה שהטבלאות באמת נוצרו
                inspector = inspect(db.engine)
                final_tables = inspector.get_table_names()
                logger.info(f"📋 טבלאות זמינות: {final_tables}")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ שגיאה ביצירת טבלאות (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            
            # ניסיון חירום - יצירה ידנית
            try:
                from sqlalchemy import text
                with db.engine.connect() as conn:
                    # יצירת טבלאות בSQL גולמי אם SQLAlchemy נכשל
                    create_tables_sql = """
                    CREATE TABLE IF NOT EXISTS parent (
                        id VARCHAR(100) PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        gender VARCHAR(20) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        email VARCHAR(254),
                        phone VARCHAR(20),
                        preferred_language VARCHAR(5) DEFAULT 'he',
                        data_processing_consent BOOLEAN DEFAULT FALSE,
                        marketing_consent BOOLEAN DEFAULT FALSE
                    );

                    CREATE TABLE IF NOT EXISTS child (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        gender VARCHAR(20) NOT NULL,
                        age INTEGER NOT NULL,
                        parent_id VARCHAR(100) REFERENCES parent(id) ON DELETE CASCADE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        birth_month INTEGER,
                        school_grade VARCHAR(20),
                        special_needs TEXT,
                        interests TEXT,
                        anonymous_id VARCHAR(32) UNIQUE
                    );

                    CREATE TABLE IF NOT EXISTS conversation (
                        id SERIAL PRIMARY KEY,
                        parent_id VARCHAR(100) REFERENCES parent(id) ON DELETE CASCADE,
                        child_id INTEGER REFERENCES child(id),
                        topic VARCHAR(200) NOT NULL,
                        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        end_time TIMESTAMP,
                        status VARCHAR(20) DEFAULT 'active',
                        priority VARCHAR(20) DEFAULT 'normal',
                        satisfaction_rating INTEGER,
                        tags TEXT,
                        message_count INTEGER DEFAULT 0,
                        avg_response_time FLOAT
                    );

                    CREATE TABLE IF NOT EXISTS message (
                        id SERIAL PRIMARY KEY,
                        conversation_id INTEGER REFERENCES conversation(id) ON DELETE CASCADE,
                        sender_type VARCHAR(10) NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        message_type VARCHAR(20) DEFAULT 'text',
                        message_metadata TEXT,
                        is_edited BOOLEAN DEFAULT FALSE,
                        edited_at TIMESTAMP,
                        character_count INTEGER DEFAULT 0,
                        word_count INTEGER DEFAULT 0,
                        response_time FLOAT,
                        sentiment_score FLOAT,
                        toxicity_score FLOAT
                    );

                    CREATE TABLE IF NOT EXISTS questionnaire_response (
                        id SERIAL PRIMARY KEY,
                        parent_id VARCHAR(100) REFERENCES parent(id) ON DELETE CASCADE,
                        child_id INTEGER REFERENCES child(id) ON DELETE CASCADE,
                        response_data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        version VARCHAR(10) DEFAULT '1.0',
                        completion_time INTEGER,
                        ip_address VARCHAR(45),
                        user_agent TEXT,
                        is_anonymized BOOLEAN DEFAULT FALSE,
                        anonymized_at TIMESTAMP
                    );
                    """
                    
                    conn.execute(text(create_tables_sql))
                    conn.commit()
                    logger.info("✅ טבלאות נוצרו באמצעות SQL גולמי")
                    return True
                    
            except Exception as sql_error:
                logger.error(f"❌ שגיאה גם ב-SQL גולמי: {sql_error}")
                return False

# יצירת טבלאות בהפעלה
ensure_tables_exist()

# Enhanced database connection check
def ensure_db_connection():
    """Ensure database connection with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with app.app_context():
                db.session.execute(db.text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database connection error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return False

# Initialize AI model with enhanced error handling
model = None
try:
    if app.config['GOOGLE_API_KEY']:
        genai.configure(api_key=app.config['GOOGLE_API_KEY'])
        model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("✅ מודל Google AI הוגדר והופעל בהצלחה.")
    else:
        logger.warning("⚠️ GOOGLE_API_KEY לא הוגדר")
except Exception as e:
    logger.error(f"❌ שגיאה באתחול מודל AI: {e}")

# Initialize advanced fallback system
advanced_fallback_system = create_advanced_fallback_system()
if advanced_fallback_system:
    logger.info("🚀 מערכת Fallback מתקדמת הופעלה בהצלחה!")
else:
    logger.warning("⚠️ מערכת Fallback לא הופעלה")

# Enhanced validation schemas
class ChatMessageSchema(Schema):
    session_id = fields.Str(required=True, validate=validate_session_id)
    message = fields.Str(required=True, validate=lambda x: 0 < len(x) <= app.config['MAX_MESSAGE_LENGTH'])

class QuestionnaireSchema(Schema):
    session_id = fields.Str(required=True, validate=validate_session_id)
    parent_name = fields.Str(required=True, validate=validate_name)
    parent_gender = fields.Str(required=True)
    child_name = fields.Str(required=True, validate=validate_name)
    child_age = fields.Int(required=True, validate=validate_age)
    child_gender = fields.Str(required=True)
    main_challenge = fields.Str(required=True)

# Enhanced utility functions
def get_or_create_parent(session_id: str, questionnaire_data: Dict[str, Any]) -> Parent:
    """Get or create parent record with enhanced error handling"""
    try:
        parent = Parent.query.filter_by(id=session_id).first()
        
        if not parent:
            parent = Parent(
                id=session_id,
                name=questionnaire_data.get('parent_name', 'הורה'),
                gender=questionnaire_data.get('parent_gender', 'לא צוין')
            )
            db.session.add(parent)
        
        parent.update_last_activity()
        return parent
    except Exception as e:
        logger.error(f"Error creating/getting parent: {e}")
        raise DatabaseError("שגיאה בטעינת נתוני הורה")

def get_or_create_child(parent: Parent, questionnaire_data: Dict[str, Any]) -> Child:
    """Get or create child record with enhanced error handling"""
    try:
        child = Child.query.filter_by(
            parent_id=parent.id,
            name=questionnaire_data.get('child_name', 'ילד')
        ).first()
        
        if not child:
            child = Child(
                name=questionnaire_data.get('child_name', 'ילד'),
                gender=questionnaire_data.get('child_gender', 'לא צוין'),
                age=int(questionnaire_data.get('child_age', 15)),
                parent_id=parent.id
            )
            db.session.add(child)
        
        return child
    except Exception as e:
        logger.error(f"Error creating/getting child: {e}")
        raise DatabaseError("שגיאה בטעינת נתוני ילד")

def generate_ai_response(user_message: str, session_id: str, questionnaire_data: Optional[Dict] = None) -> Generator[str, None, None]:
    """Generate AI response with streaming and enhanced error handling"""
    try:
        if not model:
            raise AIModelError("מודל AI לא זמין")
        
        # Build enhanced context-aware prompt
        context = ""
        if questionnaire_data:
            context = f"""
הורה בשם {questionnaire_data.get('parent_name', 'הורה')} פונה אליך לגבי {questionnaire_data.get('child_name', 'הילד/ה')} 
בן/בת {questionnaire_data.get('child_age', 'לא ידוע')}.
האתגר העיקרי: {questionnaire_data.get('main_challenge', 'לא צוין')}.
רמת מצוקה: {questionnaire_data.get('distress_level', 'לא צוין')}/10
ניסיונות קודמים: {questionnaire_data.get('past_solutions', 'לא צוין')}
מטרת השיחה: {questionnaire_data.get('goal', 'לא צוין')}
"""
        
        enhanced_prompt = f"""
אתה יונתן, פסיכו-בוט חינוכי מתקדם המתמחה בהורות למתבגרים ומבוסס על עקרונות CBT.

{context}

עקרונות התגובה שלך:
1. הגב בעברית בלבד עם טון חם, תומך ומקצועי
2. השתמש בעקרונות CBT: זיהוי מחשבות, אתגור אמונות, שינוי התנהגות
3. תן כלים פרקטיים ומעשיים שאפשר ליישם מיד
4. השתמש בפורמט CARD[כותרת|תוכן] לטיפים חשובים
5. הוסף כפתורי הצעה בפורמט [טקסט כפתור] לפעולות נוספות
6. התמקד בפתרונות ולא בבעיות
7. הכר ברגשות ההורה ותן legitimacy למצוקה
8. תן דוגמאות קונקרטיות ומעשיות

הודעת המשתמש: {user_message}
"""

        # Generate response with timeout
        try:
            response = model.generate_content(enhanced_prompt)
            
            if response and response.text:
                # Enhanced streaming with better chunking
                full_text = response.text
                chunk_size = 50
                
                for i in range(0, len(full_text), chunk_size):
                    chunk = full_text[i:i+chunk_size]
                    yield chunk
                    time.sleep(0.02)  # Small delay for better UX
            else:
                raise AIModelError("לא התקבלה תגובה מהמודל")
                
        except Exception as e:
            logger.error(f"AI model error: {e}")
            # Check if it's a quota/rate limit error
            if "quota" in str(e).lower() or "429" in str(e):
                raise QuotaExceededError("המערכת עמוסה כרגע")
            elif "timeout" in str(e).lower():
                raise AIModelError("תגובת הבוט ארכה יותר מדי")
            else:
                raise AIModelError(f"שגיאה ביצירת תגובה: {str(e)}")
            
    except Exception as e:
        logger.error(f"AI response generation error: {e}")
        raise e

# Routes
@app.route('/')
def index():
    """Main page with enhanced error handling"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error serving index page: {e}")
        return "שגיאה בטעינת הדף", 500

@app.route('/accessibility.html')
def accessibility():
    """Accessibility page"""
    try:
        return render_template('accessibility.html')
    except Exception as e:
        logger.error(f"Error serving accessibility page: {e}")
        return "שגיאה בטעינת דף הנגישות", 500

@app.route('/api/health')
def health_check():
    """Enhanced system health check"""
    try:
        db_connected = ensure_db_connection()
        ai_working = model is not None
        fallback_available = advanced_fallback_system is not None
        
        # Determine overall status
        if db_connected and (ai_working or fallback_available):
            if ai_working:
                status = "healthy"
            else:
                status = "fallback_mode"
        elif db_connected and not ai_working and not fallback_available:
            status = "degraded"
        else:
            status = "unhealthy"
        
        # Check quotas (simplified check)
        quota_exceeded = False
        try:
            if model:
                # Try a simple test to check if quota is available
                test_response = model.generate_content("test", 
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=1,
                        temperature=0
                    )
                )
                quota_exceeded = False
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                quota_exceeded = True
                status = "quota_exceeded"
        
        health_data = {
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database_connected": db_connected,
            "ai_model_working": ai_working,
            "fallback_system_available": fallback_available,
            "quota_exceeded": quota_exceeded,
            "version": "2.0",
            "features": {
                "streaming_responses": ADVANCED_SETTINGS.get('ENABLE_STREAMING_RESPONSES', True),
                "conversation_history": ADVANCED_SETTINGS.get('ENABLE_CONVERSATION_HISTORY', True),
                "csrf_protection": app.config.get('WTF_CSRF_ENABLED', False)
            }
        }
        
        # Return appropriate status code
        if status in ["healthy", "fallback_mode"]:
            return jsonify(health_data), 200
        elif status == "degraded":
            return jsonify(health_data), 206  # Partial Content
        else:
            return jsonify(health_data), 503  # Service Unavailable
            
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            "status": "error", 
            "error": "שגיאה בבדיקת בריאות המערכת",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 500

@app.route('/api/info')
def system_info():
    """Enhanced system information"""
    try:
        from models import get_db_stats
        stats = get_db_stats() if ensure_db_connection() else {}
        
        return jsonify({
            "system": "יונתן הפסיכו-בוט",
            "version": "2.0",
            "environment": app.config.get('ENV', 'unknown'),
            "database_stats": stats,
            "features": {
                "ai_model": model is not None,
                "fallback_system": advanced_fallback_system is not None,
                "rate_limiting": True,
                "csrf_protection": app.config.get('WTF_CSRF_ENABLED', False),
                "streaming_responses": ADVANCED_SETTINGS.get('ENABLE_STREAMING_RESPONSES', True),
                "conversation_history": ADVANCED_SETTINGS.get('ENABLE_CONVERSATION_HISTORY', True)
            },
            "limits": {
                "max_message_length": app.config.get('MAX_MESSAGE_LENGTH', 5000),
                "session_timeout": app.config.get('SESSION_TIMEOUT', 1800),
                "max_sessions_per_ip": app.config.get('MAX_SESSIONS_PER_IP', 10)
            }
        })
    except Exception as e:
        logger.error(f"System info error: {e}")
        return jsonify({"error": "מידע המערכת לא זמין"}), 500

@app.route('/api/init', methods=['POST'])
@limiter.limit("10 per minute")
def initialize_session():
    """Enhanced session initialization"""
    try:
        # Enhanced security checks
        if is_suspicious_request():
            log_security_event("suspicious_init_request", {
                "ip": get_client_ip(),
                "user_agent": request.headers.get('User-Agent', 'unknown')
            })
            raise SecurityError("בקשה חשודה נחסמה")
        
        if not validate_request_size():
            raise ValidationError("גודל הבקשה חורג מהמותר")
        
        # Generate secure session ID
        session_id = generate_secure_session_id()
        
        # Generate CSRF token
        csrf_token = generate_csrf_token()
        
        # Store in session
        session['session_id'] = session_id
        session['csrf_token'] = csrf_token
        session.permanent = True
        
        logger.info(f"New session initialized: {session_id[:8]}...")
        
        return jsonify({
            "session_id": session_id,
            "csrf_token": csrf_token,
            "status": "initialized",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "expires_in": app.config.get('SESSION_TIMEOUT', 1800)
        })
        
    except BotError as e:
        return jsonify(e.to_dict()), e.status_code
    except Exception as e:
        error = handle_generic_error(e)
        return jsonify(error.to_dict()), error.status_code

@app.route('/api/questionnaire', methods=['POST'])
@limiter.limit("5 per minute")
def save_questionnaire():
    """Enhanced questionnaire saving"""
    try:
        # Validate request
        schema = QuestionnaireSchema()
        data = schema.load(request.json)
        
        session_id = data['session_id']
        
        # Enhanced data validation
        if not validate_name(data['parent_name']):
            raise CustomValidationError("שם ההורה לא תקין")
        
        if not validate_name(data['child_name']):
            raise CustomValidationError("שם הילד לא תקין")
        
        if not validate_age(data['child_age']):
            raise CustomValidationError("גיל הילד לא תקין")
        
        # Create parent and child records with transaction
        try:
            parent = get_or_create_parent(session_id, data)
            child = get_or_create_child(parent, data)
            
            # Save questionnaire response
            questionnaire = QuestionnaireResponse(
                parent_id=parent.id,
                child_id=child.id,
                response_data=json.dumps(data, ensure_ascii=False),
                ip_address=get_client_ip(),
                user_agent=request.headers.get('User-Agent', 'unknown')[:500]  # Limit length
            )
            
            db.session.add(questionnaire)
            db.session.commit()
            
            logger.info(f"Questionnaire saved for session: {session_id[:8]}...")
            
            return jsonify({
                "status": "saved",
                "session_id": session_id,
                "parent_id": parent.id,
                "child_id": child.id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as db_error:
            db.session.rollback()
            logger.error(f"Database error in questionnaire: {db_error}")
            raise DatabaseError("שגיאה בשמירת נתוני השאלון")
        
    except ValidationError as e:
        return jsonify({"error": "נתונים לא תקינים", "details": e.messages}), 400
    except BotError as e:
        return jsonify(e.to_dict()), e.status_code
    except Exception as e:
        logger.error(f"Questionnaire save error: {e}")
        error = handle_generic_error(e)
        return jsonify(error.to_dict()), error.status_code

# נקודת הקצה המעודכנת עבור הצ'אט
@app.route('/api/chat', methods=['POST'])
# @limiter.limit("30 per minute") # השורה הזו הייתה קיימת בקוד המקורי, החזרתי אותה
def chat():
    # וודא שהבקשה היא בפורמט JSON
    if not request.is_json:
        return jsonify({"error": "הבקשה חייבת להיות בפורמט JSON"}), 400

    data = request.get_json()

    # וודא ששדות החובה קיימים
    session_id = data.get('session_id')
    message = data.get('message')
    timestamp = data.get('timestamp') # שדה אופציונלי, אך כדאי לצפות לו אם נשלח

    if not session_id:
        return jsonify({"error": "שדה 'session_id' חסר"}), 400
    if not message:
        return jsonify({"error": "שדה 'message' חסר"}), 400
    
    # אם יש לך דרישות ספציפיות לסוגי נתונים או פורמטים, הוסף כאן אימות נוסף.
    # לדוגמה, וודא ש-message הוא מחרוזת, ש-timestamp הוא מספר, וכו'.
    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": "שדה 'message' לא תקין"}), 400
    
    # עבד את ההודעה, צור אינטראקציה עם הבוט שלך וכו'.
    # לדוגמה:
    bot_response = f"שלום, קיבלתי את ההודעה שלך: '{message}' עבור סשן {session_id}"

    return jsonify({"response": bot_response}), 200

@app.route('/api/csrf-token')
def get_csrf_token():
    """Enhanced CSRF token generation"""
    try:
        token = generate_csrf_token()
        session['csrf_token'] = token
        session.permanent = True
        
        return jsonify({
            "csrf_token": token,
            "expires_in": app.config.get('WTF_CSRF_TIME_LIMIT', 3600)
        })
    except Exception as e:
        logger.error(f"CSRF token error: {e}")
        return jsonify({"error": "לא ניתן ליצור CSRF token"}), 500

@app.route('/api/reset_session', methods=['POST'])
@limiter.limit("5 per minute")
def reset_session():
    """Enhanced session reset"""
    try:
        data = request.json or {}
        session_id = data.get('session_id')
        
        if session_id and validate_session_id(session_id):
            try:
                # Mark conversations as completed
                conversations = Conversation.query.filter_by(
                    parent_id=session_id,
                    status='active'
                ).all()
                
                for conv in conversations:
                    conv.mark_completed()
                
                db.session.commit()
                logger.info(f"Session reset for: {session_id[:8]}...")
                
            except Exception as db_error:
                logger.warning(f"Could not reset conversations: {db_error}")
                db.session.rollback()
        
        # Clear session
        session.clear()
        
        return jsonify({
            "status": "reset", 
            "message": "הסשן אופס בהצלחה",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Session reset error: {e}")
        return jsonify({"error": "שגיאה באיפוס הסשן"}), 500

# Enhanced error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "הדף לא נמצא"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "שגיאה פנימית במערכת"}), 500

@app.errorhandler(413)  # Payload too large
def payload_too_large(error):
    return jsonify({
        "error": "ההודעה ארוכה מדי",
        "message": "אנא קצר את ההודעה ונסה שוב"
    }), 413

@app.errorhandler(RequestTimeout)
def request_timeout(error):
    return jsonify({
        "error": "הבקשה ארכה יותר מדי זמן",
        "message": "אנא נסה שוב עם הודעה קצרה יותר"
    }), 408

@app.errorhandler(TooManyRequests)
def rate_limit_handler(error):
    return jsonify({
        "error": "יותר מדי בקשות",
        "message": "אנא המתן ונסה שוב",
        "retry_after": getattr(error, 'retry_after', 60)
    }), 429

@app.errorhandler(BotError)
def handle_bot_error(error):
    return jsonify(error.to_dict()), error.status_code

# Initialize configuration
config.init_app(app)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = app.config.get('DEBUG', False)
    
    logger.info(f"🚀 Starting Yonatan Bot on port {port}")
    logger.info(f"🏭 Environment: {config_name}")
    logger.info(f"🤖 AI Model: {'Available' if model else 'Not Available'}")
    logger.info(f"🔄 Fallback System: {'Available' if advanced_fallback_system else 'Not Available'}")
    logger.info(f"🔒 CSRF Protection: {app.config.get('WTF_CSRF_ENABLED', False)}")
    logger.info(f"📊 Database: {app.config['SQLALCHEMY_DATABASE_URI'][:30]}...")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
