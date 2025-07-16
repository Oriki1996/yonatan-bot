# app.py - יונתן הפסיכו-בוט - Flask Application עם יצירת טבלאות אוטומטית
import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Generator
from flask import Flask, request, jsonify, render_template, session, stream_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import BadRequest, TooManyRequests, InternalServerError
import google.generativeai as genai
from marshmallow import Schema, fields, ValidationError

# Import local modules
from config import get_config, validate_config
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
    log_security_event, clean_message_for_ai, validate_request_size
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
cors = CORS(app)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per hour"]
)
limiter.init_app(app)

# Initialize database
init_app_db(app)

# 🚨 CRITICAL: Auto-create tables on startup (Render-friendly)
def ensure_tables_exist():
    """יצירת טבלאות אוטומטית בהפעלה - פתרון ל-Render"""
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
        logger.error(f"❌ שגיאה ביצירת טבלאות: {e}")
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

# Initialize AI model
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

# Validation schemas
class ChatMessageSchema(Schema):
    session_id = fields.Str(required=True, validate=validate_session_id)
    message = fields.Str(required=True, validate=lambda x: 0 < len(x) <= 5000)

class QuestionnaireSchema(Schema):
    session_id = fields.Str(required=True, validate=validate_session_id)
    parent_name = fields.Str(required=True, validate=validate_name)
    parent_gender = fields.Str(required=True)
    child_name = fields.Str(required=True, validate=validate_name)
    child_age = fields.Int(required=True, validate=validate_age)
    child_gender = fields.Str(required=True)
    main_challenge = fields.Str(required=True)

# Utility functions
def ensure_db_connection():
    """Ensure database connection is working"""
    try:
        with app.app_context():
            db.session.execute(db.text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return False

def get_or_create_parent(session_id: str, questionnaire_data: Dict[str, Any]) -> Parent:
    """Get or create parent record"""
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

def get_or_create_child(parent: Parent, questionnaire_data: Dict[str, Any]) -> Child:
    """Get or create child record"""
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

def generate_ai_response(user_message: str, session_id: str, questionnaire_data: Optional[Dict] = None) -> Generator[str, None, None]:
    """Generate AI response with streaming"""
    try:
        if not model:
            raise AIModelError("מודל AI לא זמין")
        
        # Build context-aware prompt
        context = ""
        if questionnaire_data:
            context = f"""
הורה בשם {questionnaire_data.get('parent_name', 'הורה')} פונה אליך לגבי {questionnaire_data.get('child_name', 'הילד/ה')} 
בן/בת {questionnaire_data.get('child_age', 'לא ידוע')}.
האתגר העיקרי: {questionnaire_data.get('main_challenge', 'לא צוין')}.
"""
        
        prompt = f"""
אתה יונתן, פסיכו-בוט חינוכי המתמחה בהורות למתבגרים ומבוסס על עקרונות CBT.

{context}

כללי תגובה:
1. הגב בעברית בלבד
2. השתמש בטון חם ותומך
3. תן כלים פרקטיים מבוססי CBT
4. השתמש בפורמט CARD[כותרת|תוכן] לטיפים חשובים
5. הוסף כפתורי הצעה בפורמט [טקסט כפתור]

הודעת המשתמש: {user_message}
"""

        response = model.generate_content(prompt)
        
        if response and response.text:
            # Stream the response
            full_text = response.text
            for i in range(0, len(full_text), 50):
                chunk = full_text[i:i+50]
                yield chunk
        else:
            raise AIModelError("לא התקבלה תגובה מהמודל")
            
    except Exception as e:
        logger.error(f"AI response generation error: {e}")
        raise AIModelError(f"שגיאה ביצירת תגובה: {str(e)}")

# Routes
@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/accessibility.html')
def accessibility():
    """Accessibility page"""
    return render_template('accessibility.html')

@app.route('/api/health')
def health_check():
    """System health check"""
    try:
        db_connected = ensure_db_connection()
        ai_working = model is not None
        fallback_available = advanced_fallback_system is not None
        
        status = "healthy"
        if not db_connected:
            status = "database_error"
        elif not ai_working and not fallback_available:
            status = "ai_unavailable"
        elif not ai_working:
            status = "fallback_mode"
        
        return jsonify({
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database_connected": db_connected,
            "ai_model_working": ai_working,
            "fallback_system_available": fallback_available,
            "quota_exceeded": False
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/info')
def system_info():
    """System information"""
    try:
        from models import get_db_stats
        stats = get_db_stats()
        
        return jsonify({
            "system": "יונתן הפסיכו-בוט",
            "version": "2.0",
            "environment": app.config.get('ENV', 'unknown'),
            "database_stats": stats,
            "features": {
                "ai_model": model is not None,
                "fallback_system": advanced_fallback_system is not None,
                "rate_limiting": True,
                "csrf_protection": app.config.get('WTF_CSRF_ENABLED', False)
            }
        })
    except Exception as e:
        logger.error(f"System info error: {e}")
        return jsonify({"error": "מידע המערכת לא זמין"}), 500

@app.route('/api/init', methods=['POST'])
@limiter.limit("10 per minute")
def initialize_session():
    """Initialize new session"""
    try:
        # Security checks
        if is_suspicious_request():
            raise SecurityError("בקשה חשודה נחסמה")
        
        if not validate_request_size():
            raise ValidationError("גודל הבקשה חורג מהמותר")
        
        # Generate session ID
        session_id = generate_secure_session_id()
        
        # Store in session
        session['session_id'] = session_id
        session.permanent = True
        
        logger.info(f"New session initialized: {session_id[:8]}...")
        
        return jsonify({
            "session_id": session_id,
            "status": "initialized",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except BotError as e:
        return jsonify(e.to_dict()), e.status_code
    except Exception as e:
        error = handle_generic_error(e)
        return jsonify(error.to_dict()), error.status_code

@app.route('/api/questionnaire', methods=['POST'])
@limiter.limit("5 per minute")
def save_questionnaire():
    """Save questionnaire data"""
    try:
        # Validate request
        schema = QuestionnaireSchema()
        data = schema.load(request.json)
        
        session_id = data['session_id']
        
        # Create parent and child records
        parent = get_or_create_parent(session_id, data)
        child = get_or_create_child(parent, data)
        
        # Save questionnaire response
        questionnaire = QuestionnaireResponse(
            parent_id=parent.id,
            child_id=child.id,
            response_data=json.dumps(data, ensure_ascii=False),
            ip_address=get_client_ip()
        )
        
        db.session.add(questionnaire)
        db.session.commit()
        
        logger.info(f"Questionnaire saved for session: {session_id[:8]}...")
        
        return jsonify({
            "status": "saved",
            "session_id": session_id,
            "parent_id": parent.id,
            "child_id": child.id
        })
        
    except ValidationError as e:
        return jsonify({"error": "נתונים לא תקינים", "details": e.messages}), 400
    except Exception as e:
        logger.error(f"Questionnaire save error: {e}")
        error = handle_generic_error(e)
        return jsonify(error.to_dict()), error.status_code

@app.route('/api/chat', methods=['POST'])
@limiter.limit("30 per minute")
def chat():
    """Chat endpoint with streaming response"""
    try:
        # Validate request
        schema = ChatMessageSchema()
        data = schema.load(request.json)
        
        session_id = data['session_id']
        user_message = sanitize_input(data['message'])
        
        if not user_message:
            raise CustomValidationError("הודעה ריקה")
        
        # Get questionnaire data
        questionnaire_data = None
        questionnaire = QuestionnaireResponse.query.filter_by(
            parent_id=session_id
        ).first()
        
        if questionnaire:
            questionnaire_data = questionnaire.get_response_data()
        
        # Save user message
        parent = Parent.query.filter_by(id=session_id).first()
        if parent:
            # Create or get conversation
            conversation = Conversation.query.filter_by(
                parent_id=parent.id,
                status='active'
            ).first()
            
            if not conversation:
                conversation = Conversation(
                    parent_id=parent.id,
                    topic=questionnaire_data.get('main_challenge', 'שיחה כללית') if questionnaire_data else 'שיחה כללית'
                )
                db.session.add(conversation)
                db.session.flush()
            
            # Save user message
            user_msg = Message(
                conversation_id=conversation.id,
                sender_type='user',
                content=user_message
            )
            db.session.add(user_msg)
            db.session.commit()
        
        # Generate response
        def generate_response():
            try:
                # Try AI first
                if model:
                    for chunk in generate_ai_response(user_message, session_id, questionnaire_data):
                        yield chunk
                else:
                    # Use fallback system
                    if advanced_fallback_system:
                        fallback_response = advanced_fallback_system.get_fallback_response(
                            user_message, session_id, questionnaire_data
                        )
                        for chunk in fallback_response:
                            yield chunk
                    else:
                        yield "אני מתנצל, המערכת לא זמינה כרגע. אנא נסה שוב מאוחר יותר."
                        
            except Exception as e:
                logger.error(f"Response generation error: {e}")
                if advanced_fallback_system:
                    fallback_response = advanced_fallback_system.get_fallback_response(
                        user_message, session_id, questionnaire_data
                    )
                    yield fallback_response
                else:
                    yield "אירעה שגיאה. אנא נסה שוב."
        
        return app.response_class(
            generate_response(),
            mimetype='text/plain',
            headers={'Cache-Control': 'no-cache'}
        )
        
    except ValidationError as e:
        return jsonify({"error": "נתונים לא תקינים", "details": e.messages}), 400
    except BotError as e:
        return jsonify(e.to_dict()), e.status_code
    except Exception as e:
        logger.error(f"Chat error: {e}")
        error = handle_generic_error(e)
        return jsonify(error.to_dict()), error.status_code

@app.route('/api/csrf-token')
def get_csrf_token():
    """Get CSRF token"""
    try:
        from utils import generate_csrf_token
        token = generate_csrf_token()
        session['csrf_token'] = token
        return jsonify({"csrf_token": token})
    except Exception as e:
        logger.error(f"CSRF token error: {e}")
        return jsonify({"error": "לא ניתן ליצור CSRF token"}), 500

@app.route('/api/reset_session', methods=['POST'])
@limiter.limit("5 per minute")
def reset_session():
    """Reset user session"""
    try:
        data = request.json or {}
        session_id = data.get('session_id')
        
        if session_id and validate_session_id(session_id):
            # Mark conversations as completed
            conversations = Conversation.query.filter_by(
                parent_id=session_id,
                status='active'
            ).all()
            
            for conv in conversations:
                conv.mark_completed()
            
            db.session.commit()
        
        # Clear session
        session.clear()
        
        return jsonify({"status": "reset", "message": "הסשן אופס בהצלחה"})
        
    except Exception as e:
        logger.error(f"Session reset error: {e}")
        return jsonify({"error": "שגיאה באיפוס הסשן"}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "הדף לא נמצא"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "שגיאה פנימית במערכת"}), 500

@app.errorhandler(TooManyRequests)
def rate_limit_handler(error):
    return jsonify({
        "error": "יותר מדי בקשות",
        "message": "אנא המתן ונסה שוב"
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
    
    app.run(host='0.0.0.0', port=port, debug=debug)