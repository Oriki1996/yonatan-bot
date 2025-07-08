# app.py - v9.0 - More dynamic conversation and interactive prompts
import os
import logging
import json
from flask import Flask, jsonify, render_template, send_from_directory, request
from flask_cors import CORS
from dotenv import load_dotenv
from models import db, Parent, Child, Conversation, Message, QuestionnaireResponse, init_app_db
import google.generativeai as genai
from sqlalchemy.exc import SQLAlchemyError
from uuid import uuid4

# --- App Initialization & Config ---
load_dotenv()
app = Flask(__name__, template_folder='.')

instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
os.makedirs(instance_path, exist_ok=True)

db_path = os.path.join(instance_path, 'yonatan.db')
app.config.from_mapping(
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    JSON_AS_ASCII=False
)

init_app_db(app)
CORS(app)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

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

# --- CBT System Prompt (Revised) ---
CBT_SYSTEM_PROMPT = """
אתה "יונתן", פסיכו-בוט חינוכי דיגיטלי, המבוסס על עקרונות טיפול קוגניטיבי-התנהגותי (CBT).
תפקידך הוא לסייע להורים למתבגרים. אתה אמפתי, מקצועי, ופרקטי.
המשתמש הוא הורה. פרטיו, פרטי ילדו, ותשובותיו לשאלון ראשוני יסופקו לך.

הנחיות הפעולה שלך:
1.  **פתיחה ואימות:** התחל כל שיחה חדשה בפנייה אישית להורה בשמו, והתייחס בקצרה לבעיה המרכזית שהגדיר.
2.  **מסגור CBT:** הסבר בקצרה את מודל אפר"ת (אירוע, פרשנות, רגש, תגובה). עזור להורה להבין את הקשר בין מחשבות (פרשנות), רגשות, והתנהגות (תגובה).
3.  **חקירה סוקרטית:** השתמש בשאלות פתוחות כדי לעזור להורה לחקור את המחשבות האוטומטיות שלו.
4.  **הצעת כלים אינטראקטיביים:** הצע כלים פרקטיים והפוך אותם לבחירות. כדי להציע בחירה, השתמש בסוגריים מרובעים. למשל: "מה דעתך שננסה את [טבלת המחשבות] או שנעדיף [ניסוי התנהגותי]?". אל תציע יותר מ-2-3 אפשרויות בכל פעם.
5.  **שמירה על מיקוד:** שמור על השיחה ממוקדת. אם ההורה גולש לנושאים אחרים או מגיב בתגובה לא קשורה (למשל 'פיצה'), הכר בכך בעדינות והחזר אותו למסלול. למשל: "אני מבין, בוא נחזור רגע להתמודדות עם...".
6.  **שפה דינמית:** גוון את תגובותיך. אל תפתח כל הודעה באותה הדרך. היה תמציתי והשתמש בפסקאות קצרות.
7.  **סיכום וחיזוק:** בסיום השיחה, סכם את הנקודות המרכזיות, חזור על הכלי שהוצע, ועודד את ההורה לנסות אותו.

**מבנה התגובה שלך:**
* היה תמציתי וברור.
* השתמש בהדגשות (bold) כדי להבליט מושגי מפתח (כמו **מחשבה אוטומטית**).
* הצע הצעות כבחירה באמצעות סוגריים מרובעים: [זו הצעה אחת] [וזו הצעה שנייה]
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
        logger.error(f"Database error during session initialization: {e}")
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
        response = QuestionnaireResponse(parent_id=session_id, child_id=child.id, response_data=json.dumps(data))
        db.session.add(response)
        db.session.commit()
        logger.info(f"Questionnaire data saved for session: {session_id}")
        return jsonify({"status": "success", "child_id": child.id})
    except (SQLAlchemyError, KeyError, ValueError) as e:
        db.session.rollback()
        logger.error(f"Error saving questionnaire data: {e}")
        return jsonify({"error": "Failed to save questionnaire data"}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    session_id = data.get('session_id')
    user_message = data.get('message')

    if not all([session_id, user_message, model]):
        return jsonify({"error": "Missing data or AI model not configured."}), 400

    try:
        parent = db.session.get(Parent, session_id)
        if not parent: return jsonify({"error": "User not found"}), 404

        # --- CONTEXT ENHANCEMENT ---
        child = Child.query.filter_by(parent_id=session_id).first()
        questionnaire = QuestionnaireResponse.query.filter_by(parent_id=session_id).first()
        
        # Find the conversation
        conversation = Conversation.query.filter_by(parent_id=session_id).first()
        if not conversation:
            conversation = Conversation(parent_id=session_id, child_id=child.id if child else None, topic="General")
            db.session.add(conversation)
            db.session.commit() # Commit to get conversation ID
            db.session.refresh(conversation)

        # Build conversation history
        history_records = Message.query.filter_by(conversation_id=conversation.id).order_by(Message.timestamp.asc()).limit(10).all()
        history_str = "\n".join([f"{msg.sender_type.capitalize()}: {msg.content}" for msg in history_records])

        context = f"""
        --- CONTEXT ---
        Parent Name: {parent.name}
        Child Name: {child.name if child else 'N/A'}
        Child Age: {child.age if child else 'N/A'}
        Initial Questionnaire Answers: {json.loads(questionnaire.response_data) if questionnaire else 'N/A'}
        --- PREVIOUS CONVERSATION ---
        {history_str}
        --- END CONTEXT ---
        """
        
        full_prompt = f"{CBT_SYSTEM_PROMPT}\n{context}\n\nUser: {user_message}"
        
        response = model.generate_content(full_prompt)
        ai_response = response.text

        # Save new messages to DB
        user_msg_db = Message(conversation_id=conversation.id, sender_type='user', content=user_message)
        ai_msg_db = Message(conversation_id=conversation.id, sender_type='bot', content=ai_response)
        db.session.add_all([user_msg_db, ai_msg_db])
        db.session.commit()

        return jsonify({"reply": ai_response})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({"error": "An internal error occurred."}), 500

@app.route('/api/articles', methods=['GET'])
def get_articles():
    try:
        return send_from_directory('.', 'articles.json')
    except FileNotFoundError:
        return jsonify({"error": "Articles file not found."}), 404

# --- Frontend Serving ---
@app.route('/')
def serve_main_landing():
    return render_template('index.html')

@app.route('/<path:filename>')
def serve_static_files(filename):
    if filename.endswith('.html'):
        return render_template(filename)
    return send_from_directory('.', filename)

if __name__ == '__main__':
    app.run(debug=True)
