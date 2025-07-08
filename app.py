# app.py - v8.0 - Full Refactor with CBT articles and enhanced logic
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

# Ensure the instance folder exists for the database
instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
os.makedirs(instance_path, exist_ok=True)

db_path = os.path.join(instance_path, 'yonatan.db')
app.config.from_mapping(
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    JSON_AS_ASCII=False
)

# Initialize database with app
init_app_db(app)
CORS(app)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# --- AI Model Configuration ---
model = None
try:
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    if not GOOGLE_API_KEY:
        logger.warning("GOOGLE_API_KEY not found in .env file. The chatbot will not function.")
    else:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("Google Generative AI model configured successfully.")
except Exception as e:
    logger.error(f"Error configuring Google AI model: {e}")

# --- CBT System Prompt ---
CBT_SYSTEM_PROMPT = """
אתה "יונתן", פסיכו-בוט חינוכי דיגיטלי, המבוסס על עקרונות טיפול קוגניטיבי-התנהגותי (CBT).
תפקידך הוא לסייע להורים למתבגרים. אתה אמפתי, מקצועי, ופרקטי.
המשתמש הוא הורה. פרטיו, פרטי ילדו, ותשובותיו לשאלון ראשוני יסופקו לך.

הנחיות הפעולה שלך:
1.  **פתיחה ואימות:** התחל כל שיחה חדשה בפנייה אישית להורה בשמו, והתייחס בקצרה לבעיה המרכזית שהגדיר בשאלון. זה יוצר אמון ומראה שהקשבת.
2.  **מסגור CBT:** הצג את הבעיה דרך "משקפי CBT". הסבר בקצרה את מודל אפר"ת (אירוע, פרשנות, רגש, תגובה). עזור להורה להבין את הקשר בין מחשבותיו (פרשנות), רגשותיו, והתנהגותו (תגובה) בסיטואציה.
3.  **חקירה סוקרטית:** אל תיתן פתרונות ישירים מיד. השתמש בשאלות פתוחות כדי לעזור להורה לחקור את המחשבות האוטומטיות שלו. למשל: "מה עבר לך בראש בדיוק כשהוא טרק את הדלת?", "אילו ראיות יש לך שהמחשבה הזו נכונה?", "מה יכולה להיות דרך אחרת להסתכל על זה?".
4.  **הצעת כלים פרקטיים:** בהתבסס על הניתוח, הצע 1-2 כלים ספציפיים מבוססי CBT. למשל:
    * **ניטור מחשבות:** "אני מציע שננסה יחד למלא 'טבלת מחשבות'. זה יעזור לנו לזהות את הדפוס."
    * **ניסוי התנהגותי:** "מה דעתך על ניסוי קטן? בפעם הבאה שהסיטואציה קורית, נסה להגיב בדרך X במקום Y, ונראה מה קורה."
    * **טכניקות הרגעה:** אם ההורה מביע מצוקה רבה, הצע תרגילי נשימה או מיינדפולנס קצרים.
5.  **שמירה על מיקוד:** שמור על השיחה ממוקדת בנושא שנבחר. אם ההורה גולש לנושאים אחרים, הכר בכך בעדינות והחזר אותו למסלול: "זה נושא חשוב, ואולי נדבר עליו בהמשך. כרגע, בוא נתמקד ב..."
6.  **סיכום וחיזוק:** בסיום השיחה, סכם את הנקודות המרכזיות, חזור על הכלי שהוצע, ועודד את ההורה לנסות אותו. סיים בנימה חיובית ומעצימה.

**מבנה התגובה שלך:**
* היה תמציתי. השתמש בפסקאות קצרות.
* השתמש בהדגשות (bold) כדי להבליט מושגי מפתח (כמו **מחשבה אוטומטית** או **מודל אפר"ת**).
* הצע הצעות כבחירה, לא כהוראה: "אולי ננסה...", "מה דעתך על...".
"""

# --- API Endpoints ---

@app.route('/api/init', methods=['POST'])
def init_session():
    """Initializes a user session."""
    session_id = str(uuid4())
    try:
        # For simplicity in this example, we create a dummy parent on init.
        # In a real app, this would be tied to a login system.
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
    """Saves the questionnaire data."""
    data = request.json
    session_id = data.get('session_id')
    if not session_id:
        return jsonify({"error": "Session ID is missing"}), 400

    try:
        parent = db.session.get(Parent, session_id)
        if not parent:
            return jsonify({"error": "Invalid session ID"}), 404

        # Update parent and create child
        parent.name = data.get('parent_name')
        parent.gender = data.get('parent_gender')
        
        child = Child(
            name=data.get('child_name'),
            age=int(data.get('child_age')),
            gender=data.get('child_gender'),
            parent_id=session_id
        )
        db.session.add(child)

        # Save questionnaire response
        response = QuestionnaireResponse(
            parent_id=session_id,
            child_id=child.id, # This will be populated after commit
            response_data=json.dumps(data)
        )
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
    """Handles chat messages."""
    data = request.json
    session_id = data.get('session_id')
    user_message = data.get('message')

    if not all([session_id, user_message, model]):
        error_msg = "Missing session_id, message, or AI model is not configured."
        logger.error(error_msg)
        return jsonify({"error": error_msg}), 400

    try:
        parent = db.session.get(Parent, session_id)
        if not parent:
            return jsonify({"error": "User not found"}), 404

        # Retrieve context for the AI
        child = Child.query.filter_by(parent_id=session_id).first()
        questionnaire = QuestionnaireResponse.query.filter_by(parent_id=session_id).first()
        
        context = f"""
        --- CONTEXT ---
        Parent Name: {parent.name}
        Child Name: {child.name if child else 'N/A'}
        Child Age: {child.age if child else 'N/A'}
        Child Gender: {child.gender if child else 'N/A'}
        Initial Questionnaire Answers: {questionnaire.response_data if questionnaire else 'N/A'}
        --- END CONTEXT ---
        """
        
        full_prompt = f"{CBT_SYSTEM_PROMPT}\n{context}\n\nUser message: {user_message}"
        
        # In a real app, you would manage conversation history.
        # For this example, we send the full context each time.
        response = model.generate_content(full_prompt)
        ai_response = response.text

        # Save message to DB
        conversation = Conversation.query.filter_by(parent_id=session_id).first()
        if not conversation:
            conversation = Conversation(parent_id=session_id, child_id=child.id if child else None, topic="General")
            db.session.add(conversation)
            db.session.commit()

        user_msg_db = Message(conversation_id=conversation.id, sender_type='user', content=user_message)
        ai_msg_db = Message(conversation_id=conversation.id, sender_type='bot', content=ai_response)
        db.session.add_all([user_msg_db, ai_msg_db])
        db.session.commit()

        return jsonify({"reply": ai_response})

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({"error": "An internal error occurred."}), 500

@app.route('/api/articles', methods=['GET'])
def get_articles():
    """Serves the articles JSON file."""
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
    # This serves dashboard.html, accessibility.html, etc.
    if filename.endswith('.html'):
        return render_template(filename)
    # This serves widget.js, character-animation.json, etc.
    return send_from_directory('.', filename)

if __name__ == '__main__':
    app.run(debug=True)
