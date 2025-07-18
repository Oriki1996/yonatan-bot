# app.py - קובץ מתוקן בשלמותו

from flask import Flask, request, jsonify, Response, render_template, send_from_directory # ADDED render_template, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
import logging
import os
from datetime import datetime, timezone, timedelta
import json
import re
from typing import Dict, Any

# Import models and db initialization
from models import db, init_app_db, Parent, Child, Conversation, Message, QuestionnaireResponse

# Import Config and error handling
from config import get_config, validate_config
from errors import BotError, ValidationError, handle_generic_error, QuotaExceededError, RateLimitExceededError, AIModelError, FallbackSystemError

# Import advanced_fallback_system
from advanced_fallback_system import create_advanced_fallback_system, ResponseContext, AgeGroup, ChallengeCategory, ConversationStage, CBTTechnique

# Import Google Generative AI
import google.generativeai as genai


# --- Application Initialization ---
app = Flask(__name__)

# Load configuration
current_config = get_config(os.environ.get('FLASK_ENV', 'development'))
app.config.from_object(current_config)
current_config.init_app(app)

# Validate configuration
if not validate_config(current_config):
    logging.error("❌ Configuration validation failed. Exiting.")
    exit(1)

# Initialize database
init_app_db(app)

# Initialize CORS
CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}})

# Initialize Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri=app.config['RATELIMIT_STORAGE_URL'],
    strategy=app.config['RATELIMIT_STRATEGY'],
    headers_enabled=app.config['RATELIMIT_HEADERS_ENABLED']
)

# Configure logging
logging.basicConfig(level=getattr(logging, app.config['LOG_LEVEL'].upper()))
logger = logging.getLogger(__name__)

# Configure Google Generative AI
model = None
if app.config.get('GOOGLE_API_KEY'):
    try:
        genai.configure(api_key=app.config['GOOGLE_API_KEY'])
        model = genai.GenerativeModel('gemini-pro')
        logger.info("✅ Google Generative AI model initialized.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Google Generative AI model: {e}")
        model = None
else:
    logger.warning("GOOGLE_API_KEY not set. AI model will not be available.")

# Initialize advanced fallback system
advanced_fallback_system = create_advanced_fallback_system()
if not advanced_fallback_system:
    logger.error("❌ Advanced Fallback System could not be initialized.")


# --- Helper Functions ---

def validate_session_id(session_id: str) -> bool:
    """Basic validation for session_id (e.g., length, character set)"""
    return isinstance(session_id, str) and 5 <= len(session_id) <= 100 and re.match(r"^[a-zA-Z0-9_-]+$", session_id)

def is_suspicious_request():
    """Placeholder for more advanced security checks"""
    return False

def log_security_event(event_type: str, details: Dict[str, Any]):
    """Log security events"""
    logger.warning(f"SECURITY ALERT: {event_type} - Details: {details}")

def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent injection attacks"""
    cleaned_text = re.sub(r'<[^>]*>', '', text)
    cleaned_text = cleaned_text[:app.config.get('MAX_MESSAGE_LENGTH', 5000)]
    return cleaned_text.strip()


# --- Routes ---

@app.route('/')
def index():
    """Renders the main index.html page."""
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    """Serves the favicon.ico file (you'll need to place it in the static directory)."""
    # Assuming you have a favicon.ico in your static folder.
    # If not, you might want to return an empty response or a default icon.
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/accessibility.html')
def accessibility():
    """Renders the accessibility.html page."""
    return render_template('accessibility.html')

@app.route('/api/chat', methods=['POST'])
@limiter.limit("30 per minute")
def chat():
    """Enhanced chat endpoint with proper validation and streaming response"""
    try:
        if not request.is_json:
            return jsonify({"error": "הבקשה חייבת להיות בפורמט JSON"}), 400

        data = request.get_json()
        if not data:
            return jsonify({"error": "נתוני JSON חסרים"}), 400

        session_id = data.get('session_id')
        message = data.get('message')
        
        if not session_id:
            return jsonify({"error": "שדה session_id חסר"}), 400
        if not message:
            return jsonify({"error": "שדה message חסר"}), 400
        
        if not validate_session_id(session_id):
            return jsonify({"error": "session_id לא תקין"}), 400
            
        if not isinstance(message, str) or not message.strip():
            return jsonify({"error": "שדה message לא תקין"}), 400
            
        if len(message) > app.config.get('MAX_MESSAGE_LENGTH', 5000):
            return jsonify({"error": "ההודעה ארוכה מדי"}), 400

        if is_suspicious_request():
            log_security_event("suspicious_chat_request", {
                "session_id": session_id[:8] + "...",
                "message_length": len(message)
            })
            return jsonify({"error": "בקשה חשודה נחסמה"}), 403

        message = sanitize_input(message)
        if not message:
            return jsonify({"error": "הודעה לא תקינה אחרי ניקוי"}), 400

        conversation = None
        parent = None
        try:
            questionnaire_data = {}
            if session_id:
                questionnaire = QuestionnaireResponse.query.filter_by(parent_id=session_id).first()
                if questionnaire:
                    questionnaire_data = questionnaire.get_response_data()

            parent = Parent.query.filter_by(id=session_id).first()
            if parent:
                conversation = Conversation.query.filter_by(
                    parent_id=session_id,
                    status='active'
                ).first()
                
                if not conversation:
                    conversation = Conversation(
                        parent_id=session_id,
                        child_id=parent.children[0].id if parent.children else None,
                        topic=questionnaire_data.get('main_challenge', 'שיחה כללית')
                    )
                    db.session.add(conversation)
                    db.session.flush()

                if message != "START_CONVERSATION":
                    user_message = Message(
                        conversation_id=conversation.id,
                        sender_type='user',
                        content=message
                    )
                    db.session.add(user_message)
                    db.session.commit()
                    
        except Exception as db_error:
            logger.error(f"Database error in chat: {db_error}")
            db.session.rollback()

        def generate_response_stream():
            current_conversation = conversation
            
            try:
                if model:
                    try:
                        context = ""
                        if questionnaire_data:
                            context = f"""
הורה: {questionnaire_data.get('parent_name', 'הורה')}
ילד/ה: {questionnaire_data.get('child_name', 'ילד/ה')} בן/בת {questionnaire_data.get('child_age', 'לא ידוע')}
אתגר עיקרי: {questionnaire_data.get('main_challenge', 'לא צוין')}
רמת מצוקה: {questionnaire_data.get('distress_level', 'לא צוין')}/10
ניסיונות קודמים: {questionnaire_data.get('past_solutions', 'לא צוין')}
מטרת השיחה: {questionnaire_data.get('goal', 'לא צוין')}
"""

                        prompt = f"""
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

הודעת המשתמש: {message}
"""

                        response_ai = model.generate_content(prompt)
                        
                        if response_ai and response_ai.text:
                            full_response = response_ai.text
                            
                            try:
                                if current_conversation:
                                    bot_message = Message(
                                        conversation_id=current_conversation.id,
                                        sender_type='bot',
                                        content=full_response
                                    )
                                    db.session.add(bot_message)
                                    current_conversation.update_message_count()
                                    db.session.commit()
                            except Exception as save_error:
                                logger.warning(f"Could not save message to DB: {save_error}")
                                db.session.rollback()
                            
                            chunk_size = 50
                            for i in range(0, len(full_response), chunk_size):
                                chunk = full_response[i:i+chunk_size]
                                yield chunk
                            return
                            
                    except Exception as ai_error:
                        logger.error(f"AI model error: {ai_error}")

                if advanced_fallback_system:
                    fallback_response = advanced_fallback_system.get_fallback_response(
                        user_input=message, session_id=session_id, questionnaire_data=questionnaire_data
                    )
                    
                    try:
                        if current_conversation:
                            bot_message = Message(
                                conversation_id=current_conversation.id,
                                sender_type='bot',
                                content=fallback_response
                            )
                            db.session.add(bot_message)
                            current_conversation.update_message_count()
                            db.session.commit()
                    except Exception as save_error:
                        logger.warning(f"Could not save fallback message to DB: {save_error}")
                        db.session.rollback()
                    
                    chunk_size = 50
                    for i in range(0, len(fallback_response), chunk_size):
                        chunk = fallback_response[i:i+chunk_size]
                        yield chunk
                    return
                
                basic_response = "שלום! אני יונתן. מצטער, יש לי קושי טכני כרגע, אבל אני כאן לעזור לך. איך אני יכול לסייע?"
                yield basic_response
                
            except Exception as e:
                logger.error(f"Error in generate_response_stream: {e}")
                error_response = "מצטער, אירעה שגיאה טכנית. אנא נסה שוב."
                yield error_response

        return Response(
            generate_response_stream(),
            mimetype='text/plain',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )

    except ValidationError as e:
        db.session.rollback()
        return jsonify({"error": "נתונים לא תקינים", "details": e.messages}), 400
    except BotError as e:
        db.session.rollback()
        return jsonify(e.to_dict()), e.status_code
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error in chat endpoint: {e}")
        error = handle_generic_error(e)
        return jsonify(error.to_dict()), error.status_code

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify service status."""
    db_connected = False
    try:
        with db.engine.connect() as connection:
            connection.execute(db.text("SELECT 1"))
        db_connected = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_connected = False

    ai_model_working = False
    if model:
        try:
            response = model.generate_content("hello")
            if response and response.text:
                ai_model_working = True
        except Exception as e:
            logger.error(f"AI model health check failed: {e}")
            ai_model_working = False
    
    fallback_system_available = advanced_fallback_system is not None

    return jsonify({
        "status": "healthy",
        "database_connected": db_connected,
        "ai_model_working": ai_model_working,
        "fallback_system_available": fallback_system_available,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200

# Main entry point for running the app directly (for development)
if __name__ == '__main__':
    app.run(debug=current_config.DEBUG, host='0.0.0.0', port=5000)