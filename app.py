# app.py - v7.0 - Precision, Questionnaire & Enhanced AI Logic

import os
import logging
import json
from flask import Flask, jsonify, render_template, send_from_directory, request
from flask_cors import CORS
from dotenv import load_dotenv
from models import db, Parent, Child, Conversation, Message, Reflection, PracticeLog, SavedArticle, QuestionnaireResponse
import google.generativeai as genai
from sqlalchemy.exc import SQLAlchemyError

# --- App Initialization & Config ---
load_dotenv()
app = Flask(__name__, template_folder='.')
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
    data = request.get_json()
    session_id, name, gender = data.get('session_id'), data.get('name'), data.get('gender')
    if not all([session_id, name, gender]):
        return jsonify({"error": "Missing required session data"}), 400
    parent = Parent.query.get(session_id)
    if not parent:
        parent = Parent(id=session_id, name=name, gender=gender)
        db.session.add(parent)
    else:
        parent.name, parent.gender = name, gender
    try:
        db.session.commit()
        return jsonify({"id": parent.id, "name": parent.name, "gender": parent.gender})
    except SQLAlchemyError as e:
        db.session.rollback(); logger.error(f"DB error: {e}"); return jsonify({"error": "DB failed"}), 500

@app.route('/api/children', methods=['GET', 'POST'])
def handle_children():
    session_id = request.args.get('session_id') or request.get_json().get('session_id')
    if not session_id: return jsonify({"error": "session_id is required"}), 400
    parent = Parent.query.get(session_id)
    if not parent: return jsonify({"error": "Parent not found"}), 404
    
    if request.method == 'GET':
        return jsonify([{"id": c.id, "name": c.name, "gender": c.gender, "age": c.age} for c in parent.children])
    
    if request.method == 'POST':
        data = request.get_json()
        # MODIFIED: Use 'age' instead of 'age_range'
        new_child = Child(name=data.get('name'), gender=data.get('gender'), age=data.get('age'), parent_id=parent.id)
        db.session.add(new_child)
        try:
            db.session.commit()
            logger.info(f"New child '{new_child.name}' (age {new_child.age}) added for parent {parent.id}")
            return jsonify({"id": new_child.id, "name": new_child.name, "gender": new_child.gender, "age": new_child.age}), 201
        except SQLAlchemyError as e:
            db.session.rollback(); logger.error(f"DB error: {e}"); return jsonify({"error": "DB failed"}), 500

# NEW: Endpoint to handle questionnaire submission
@app.route('/api/questionnaire', methods=['POST'])
def handle_questionnaire():
    data = request.get_json()
    session_id = data.get('session_id')
    child_id = data.get('child_id')
    answers = data.get('answers')

    if not all([session_id, child_id, answers]):
        return jsonify({"error": "Missing questionnaire data"}), 400
    
    # Save the response
    response = QuestionnaireResponse(
        child_id=child_id,
        parent_id=session_id,
        answers=json.dumps(answers) # Store answers as a JSON string
    )
    db.session.add(response)
    try:
        db.session.commit()
        logger.info(f"Questionnaire saved for child {child_id}")
        return jsonify({"status": "success"}), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"DB error saving questionnaire: {e}")
        return jsonify({"error": "Database operation failed"}), 500

@app.route('/api/chat', methods=['POST'])
def handle_chat():
    data = request.get_json()
    session_id, child_id, history = data.get('session_id'), data.get('child_id'), data.get('history')
    if not all([session_id, child_id, history]): return jsonify({"error": "Missing chat data"}), 400
    
    parent = Parent.query.get(session_id)
    child = Child.query.get(child_id)
    if not parent or not child: return jsonify({"error": "Parent or child not found"}), 404

    conversation = Conversation.query.filter_by(parent_id=session_id, child_id=child_id, is_open=True).first()
    if not conversation:
        conversation = Conversation(parent_id=session_id, child_id=child_id)
        db.session.add(conversation); db.session.commit()

    user_message_content = history[-1]['parts'][0]['text']
    user_message = Message(conversation_id=conversation.id, role='user', content=user_message_content)
    db.session.add(user_message)

    # UPGRADED: Dynamic system prompt based on questionnaire
    questionnaire_data = QuestionnaireResponse.query.filter_by(child_id=child_id).order_by(QuestionnaireResponse.timestamp.desc()).first()
    
    prompt_context = f"The parent you are speaking with is '{parent.name}'. They are talking about their {child.age}-year-old child, '{child.name}'."
    if questionnaire_data:
        answers = json.loads(questionnaire_data.answers)
        prompt_context += f"""
        Based on their initial answers:
        - The main challenge is: {answers.get('mainChallenge', 'Not specified')}
        - It makes the parent feel: {answers.get('parentFeeling', 'Not specified')}
        - The parent's goal is: {answers.get('mainGoal', 'Not specified')}
        """

    system_prompt = f"""
    You are Yonatan, a warm, empathetic, and supportive virtual assistant for parents, based on the principles of Cognitive Behavioral Therapy (CBT).
    Your primary goal is to help parents understand and navigate the challenges of parenthood.
    Your persona: Patient, non-judgmental, encouraging. Your language is simple, clear, and supportive.
    Your methodology:
    1. Active Listening & Validation: Always start by acknowledging and validating the parent's feelings. (e.g., "That sounds really tough," "I can understand why you'd feel that way.")
    2. The CBT Triangle: Help the parent see the connection between Thoughts, Feelings, and Behaviors. Ask gentle questions like, "What was going through your mind then?" or "How did that feeling make you want to act?"
    3. Offer Practical, Actionable Tools: Suggest concrete, evidence-based CBT techniques. Frame them as simple "experiments" or "tools to try."
    4. Maintain Boundaries: Always remember you are a supportive tool, not a substitute for professional psychological help, especially for severe issues.
    
    Initial Context: {prompt_context}
    Start the conversation by referencing the parent's stated goal from the questionnaire.
    """
    
    ai_history = [{"role": "user", "parts": [{"text": system_prompt}]}] + history

    bot_response_text = ""
    try:
        if not model: raise ConnectionError("AI Model not configured.")
        response = model.generate_content(ai_history)
        bot_response_text = response.text
        bot_message = Message(conversation_id=conversation.id, role='model', content=bot_response_text)
        db.session.add(bot_message)
    except Exception as e:
        logger.error(f"AI chat generation failed: {e}")
        bot_response_text = "אני מתנצל, אני חווה תקלה טכנית כרגע. נוכל לנסות שוב בעוד כמה רגעים?"
    
    try:
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback(); logger.error(f"DB error: {e}"); return jsonify({"error": "DB failed"}), 500

    return jsonify({"response": bot_response_text, "conversation_id": conversation.id})

# Other routes (dashboard, pages) remain largely the same...
@app.route('/api/dashboard-data')
def get_dashboard_data():
    session_id = request.args.get('session_id')
    if not session_id: return jsonify({"error": "session_id is required"}), 400
    parent = Parent.query.get(session_id)
    if not parent: return jsonify({"error": "Parent not found"}), 404
    children_data = [{"id": c.id, "name": c.name, "gender": c.gender, "age": c.age} for c in parent.children]
    conversations = Conversation.query.filter_by(parent_id=session_id).order_by(Conversation.start_time.desc()).limit(5).all()
    conversations_data = []
    for conv in conversations:
        child = Child.query.get(conv.child_id)
        reflection = Reflection.query.filter_by(conversation_id=conv.id).first()
        conversations_data.append({ "id": conv.id, "child_name": child.name if child else "Unknown", "start_time": conv.start_time.isoformat(), "main_topic": conv.main_topic or "שיחה כללית", "summary": reflection.summary if reflection else "אין עדיין סיכום זמין." })
    saved_articles = SavedArticle.query.filter_by(parent_id=session_id).order_by(SavedArticle.saved_at.desc()).all()
    saved_articles_data = [{"article_key": sa.article_key, "saved_at": sa.saved_at.isoformat()} for sa in saved_articles]
    goals = PracticeLog.query.filter_by(parent_id=session_id).order_by(PracticeLog.last_updated.desc()).all()
    goals_data = [{"technique_name": g.technique_name, "status": g.status} for g in goals]
    return jsonify({ "parent_name": parent.name, "children": children_data, "recent_conversations": conversations_data, "saved_articles": saved_articles_data, "goals": goals_data, "stats": { "conversations_count": Conversation.query.filter_by(parent_id=session_id).count(), "saved_articles_count": len(saved_articles_data), "goals_completed_count": PracticeLog.query.filter_by(parent_id=session_id, status='completed').count() } })

@app.route('/')
def serve_main_landing(): return render_template('index.html')
@app.route('/index.html')
def serve_index_page(): return render_template('index.html')
@app.route('/dashboard.html')
def serve_dashboard(): return render_template('dashboard.html')
@app.route('/accessibility.html')
def serve_accessibility_page(): return render_template('accessibility.html')
@app.route('/widget.js')
def serve_widget(): return send_from_directory('.', 'widget.js')
@app.route('/character-animation.json')
def serve_animation(): return send_from_directory('.', 'character-animation.json')

# --- Main Execution ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        logger.info("Database initialized and all tables created.")
    app.run(host='0.0.0.0', port=10000, debug=True)
