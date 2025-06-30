# app.py - v5.0 - AI Chat & Dashboard Fixes

import os
import logging
from flask import Flask, jsonify, render_template, send_from_directory, request
from flask_cors import CORS
from dotenv import load_dotenv
from models import db, Parent, Child, Conversation, Message, Reflection, PracticeLog, SavedArticle
import google.generativeai as genai
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

# --- App Initialization ---
load_dotenv()

# This tells Flask to look for HTML files in the same directory.
app = Flask(__name__, template_folder='.')

# --- Database and CORS Configuration ---
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(data_dir, exist_ok=True)
db_path = os.path.join(data_dir, 'yonatan.db')

app.config.from_mapping(
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    JSON_AS_ASCII=False
)
db.init_app(app)
CORS(app)

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# --- AI Model Configuration ---
model = None
try:
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    if GOOGLE_API_KEY:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("✅ Google Generative AI model configured.")
    else:
        logger.warning("⚠️ GOOGLE_API_KEY not found. AI features will be disabled.")
except Exception as e:
    logger.error(f"❌ AI model configuration failed: {e}")

# --- API Routes ---

@app.route('/api/session', methods=['POST'])
def handle_session():
    """Creates or retrieves a parent session."""
    data = request.get_json()
    session_id = data.get('session_id')
    name = data.get('name')
    gender = data.get('gender')

    if not all([session_id, name, gender]):
        return jsonify({"error": "Missing required session data"}), 400

    parent = Parent.query.get(session_id)
    if not parent:
        parent = Parent(id=session_id, name=name, gender=gender)
        db.session.add(parent)
        logger.info(f"New parent created with session_id: {session_id}")
    else:
        parent.name = name
        parent.gender = gender
        logger.info(f"Parent session updated for session_id: {session_id}")
    
    try:
        db.session.commit()
        return jsonify({"id": parent.id, "name": parent.name, "gender": parent.gender})
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error on session handling: {e}")
        return jsonify({"error": "Database operation failed"}), 500

@app.route('/api/children', methods=['GET', 'POST'])
def handle_children():
    """Handles getting and adding children for a parent."""
    session_id = request.args.get('session_id') or request.get_json().get('session_id')
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    parent = Parent.query.get(session_id)
    if not parent:
        return jsonify({"error": "Parent not found"}), 404

    if request.method == 'GET':
        children_data = [{"id": c.id, "name": c.name, "gender": c.gender, "age_range": c.age_range} for c in parent.children]
        return jsonify(children_data)

    if request.method == 'POST':
        data = request.get_json()
        new_child = Child(
            name=data.get('name'),
            gender=data.get('gender'),
            age_range=data.get('age_range'),
            parent_id=parent.id
        )
        db.session.add(new_child)
        try:
            db.session.commit()
            logger.info(f"New child '{new_child.name}' added for parent {parent.id}")
            return jsonify({"id": new_child.id, "name": new_child.name, "gender": new_child.gender, "age_range": new_child.age_range}), 201
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error on adding child: {e}")
            return jsonify({"error": "Database operation failed"}), 500

@app.route('/api/chat', methods=['POST'])
def handle_chat():
    """Handles chat interactions and AI responses, now with real AI."""
    data = request.get_json()
    session_id = data.get('session_id')
    child_id = data.get('child_id')
    history = data.get('history')
    
    if not all([session_id, child_id, history]):
        return jsonify({"error": "Missing chat data"}), 400

    # Ensure parent and child exist
    parent = Parent.query.get(session_id)
    child = Child.query.get(child_id)
    if not parent or not child:
        return jsonify({"error": "Parent or child not found"}), 404

    # Find or create a conversation
    conversation = Conversation.query.filter_by(parent_id=session_id, child_id=child_id, is_open=True).first()
    if not conversation:
        conversation = Conversation(parent_id=session_id, child_id=child_id, start_time=datetime.utcnow())
        db.session.add(conversation)
        db.session.commit() # Commit to get conversation.id

    # Save user message
    user_message_content = history[-1]['parts'][0]['text']
    user_message = Message(conversation_id=conversation.id, role='user', content=user_message_content)
    db.session.add(user_message)

    bot_response_text = ""
    try:
        if not model:
            raise ConnectionError("Google AI Model not configured.")
        
        # Generate AI response
        # Note: The history format from the client matches what the API expects.
        response = model.generate_content(history)
        bot_response_text = response.text

        # Save bot response
        bot_message = Message(conversation_id=conversation.id, role='model', content=bot_response_text)
        db.session.add(bot_message)

    except Exception as e:
        logger.error(f"AI chat generation failed: {e}")
        bot_response_text = "אני מתנצל, אני חווה תקלה טכנית כרגע. נוכל לנסות שוב בעוד כמה רגעים?"
    
    try:
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error on saving chat messages: {e}")
        return jsonify({"error": "Database operation failed"}), 500

    return jsonify({
        "response": bot_response_text,
        "conversation_id": conversation.id
    })

@app.route('/api/dashboard-data')
def get_dashboard_data():
    """Provides all necessary data for the user's personal dashboard."""
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400
    
    parent = Parent.query.get(session_id)
    if not parent:
        return jsonify({"error": "Parent not found"}), 404
    
    # --- Children Data ---
    children_data = [{"id": c.id, "name": c.name, "gender": c.gender, "age_range": c.age_range} for c in parent.children]
    
    # --- Recent Conversations Data ---
    conversations = Conversation.query.filter_by(parent_id=session_id).order_by(Conversation.start_time.desc()).limit(5).all()
    conversations_data = []
    for conv in conversations:
        child = Child.query.get(conv.child_id)
        reflection = Reflection.query.filter_by(conversation_id=conv.id).first()
        conversations_data.append({
            "id": conv.id,
            "child_name": child.name if child else "Unknown",
            "start_time": conv.start_time.isoformat(),
            "main_topic": conv.main_topic or "שיחה כללית",
            "summary": reflection.summary if reflection else "אין עדיין סיכום זמין."
        })

    # --- FIX: Query for Saved Articles and Goals ---
    saved_articles = SavedArticle.query.filter_by(parent_id=session_id).order_by(SavedArticle.saved_at.desc()).all()
    saved_articles_data = [{"article_key": sa.article_key, "saved_at": sa.saved_at.isoformat()} for sa in saved_articles]
    
    goals = PracticeLog.query.filter_by(parent_id=session_id).order_by(PracticeLog.last_updated.desc()).all()
    goals_data = [{"technique_name": g.technique_name, "status": g.status} for g in goals]

    # --- Build the full payload ---
    dashboard_payload = {
        "parent_name": parent.name,
        "children": children_data,
        "recent_conversations": conversations_data,
        "saved_articles": saved_articles_data, # FIX: Added saved articles list
        "goals": goals_data,                   # FIX: Added goals list
        "stats": {
            "conversations_count": Conversation.query.filter_by(parent_id=session_id).count(),
            "saved_articles_count": len(saved_articles_data),
            "goals_completed_count": PracticeLog.query.filter_by(parent_id=session_id, status='completed').count()
        }
    }
    return jsonify(dashboard_payload)

# --- Page Serving Routes ---

@app.route('/')
def serve_main_landing():
    """Serves the main, feature-rich index.html as the landing page."""
    return render_template('index.html')

@app.route('/index.html')
def serve_index_page():
    """Explicitly serves the index.html file."""
    return render_template('index.html')

@app.route('/dashboard.html')
def serve_dashboard():
    """Serves the user's personal dashboard page."""
    return render_template('dashboard.html')

@app.route('/widget.js')
def serve_widget():
    """Serves the JavaScript file for the chat widget."""
    return send_from_directory('.', 'widget.js')

@app.route('/character-animation.json')
def serve_animation():
    """Serves the Lottie animation file."""
    return send_from_directory('.', 'character-animation.json')

# --- Main Execution ---
if __name__ == '__main__':
    with app.app_context():
        # Create all database tables if they don't exist
        db.create_all()
        logger.info("Database initialized and all tables created.")
    app.run(host='0.0.0.0', port=10000, debug=True)
