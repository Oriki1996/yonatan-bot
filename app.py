# app.py - v14.1 - DB Connection Fix
import os
import logging
import json
from flask import Flask, jsonify, render_template, request, Response, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv
from models import db, Parent, Child, Conversation, Message, QuestionnaireResponse, init_app_db
import google.generativeai as genai
from sqlalchemy.exc import SQLAlchemyError
from uuid import uuid4

# --- App Initialization & Config ---
load_dotenv()
app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Database Configuration (Updated for Production) ---
DATABASE_URL = os.environ.get('DATABASE_URL')
# FIX: Check for the correct 'postgresql://' prefix provided by Render.
if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    logger.info("Connecting to PostgreSQL database.")
else:
    # For local development, fall back to a SQLite database.
    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    os.makedirs(instance_path, exist_ok=True)
    db_path = os.path.join(instance_path, 'yonatan.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
    logger.info("Connecting to local SQLite database.")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False

init_app_db(app)
CORS(app)

# --- AI Model Configuration ---
model = None
try:
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    if not GOOGLE_API_KEY:
        logger.warning("GOOGLE_API_KEY not found. Chatbot will not function.")
    else:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("Google Generative AI model configured successfully.")
except Exception as e:
    logger.error(f"Error configuring Google AI model: {e}")

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

# --- API Endpoints ---

@app.route('/api/init', methods=['POST'])
def init_session():
    session_id = str(uuid4())
    try:
        parent = Parent(id=session_id, name="אורח", gender="לא צוין")
        db.session.add(parent)
        db.session.commit()
        logger.info(f"New session created with ID: {session_id}")
        return jsonify({"session_id": session_id, "status": "new_user"})
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error on init: {e}")
        return jsonify({"error": "Failed to initialize session"}), 500

@app.route('/api/questionnaire', methods=['POST'])
def handle_questionnaire():
    data = request.json
    session_id = data.get('session_id')
    if not session_id: return jsonify({"error": "Session ID is missing"}), 400
    try:
        parent = db.session.get(Parent, session_id)
        if not parent: return jsonify({"error": "Invalid session ID"}), 404
        parent.name = data.get('parent_name')
        parent.gender = data.get('parent_gender')
        child = Child(name=data.get('child_name'), age=int(data.get('child_age')), gender=data.get('child_gender'), parent_id=session_id)
        db.session.add(child)
        db.session.flush()
        response = QuestionnaireResponse(parent_id=session_id, child_id=child.id, response_data=json.dumps(data, ensure_ascii=False))
        db.session.add(response)
        db.session.commit()
        logger.info(f"Questionnaire data saved for session: {session_id}")
        return jsonify({"status": "success"})
    except (SQLAlchemyError, KeyError, ValueError) as e:
        db.session.rollback()
        logger.error(f"Error saving questionnaire: {e}")
        return jsonify({"error": "Failed to save questionnaire data"}), 500

# --- MODIFIED CHAT ENDPOINT FOR STREAMING ---
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    session_id = data.get('session_id')
    user_message = data.get('message')

    if not all([session_id, user_message, model]):
        return jsonify({"error": "Missing data or AI model not configured."}), 400

    try:
        if session_id not in chat_sessions:
            logger.info(f"Creating new chat session for session_id: {session_id}")
            parent = db.session.get(Parent, session_id)
            if not parent: return jsonify({"error": "User not found"}), 404
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

            chat_sessions[session_id] = model.start_chat(
                history=history,
                system_instruction=f"{CBT_SYSTEM_PROMPT}\n{context}"
            )
        
        active_chat = chat_sessions[session_id]
        
        # Save user message to DB before starting the stream
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

        # Generate content with streaming enabled
        stream = active_chat.send_message(user_message, stream=True)

        def generate_and_save():
            full_response_text = []
            for chunk in stream:
                if chunk.text:
                    full_response_text.append(chunk.text)
                    yield chunk.text
            
            # After the stream is complete, save the full response to the database
            final_text = "".join(full_response_text)
            
            # We need a conversation ID to save the message
            db_conv = Conversation.query.filter_by(parent_id=session_id).first()
            if db_conv:
                ai_msg_db = Message(conversation_id=db_conv.id, sender_type='bot', content=final_text)
                db.session.add(ai_msg_db)
                db.session.commit()
                logger.info(f"Saved streamed response for session {session_id}")

        return Response(stream_with_context(generate_and_save()), mimetype='text/plain')

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred."}), 500


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
    app.run(debug=True)
