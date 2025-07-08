# models.py - v8.0 - Stable version
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

def init_app_db(app):
    """Initializes the database and creates tables if they don't exist."""
    db.init_app(app)
    with app.app_context():
        db.create_all()

class Parent(db.Model):
    __tablename__ = 'parent'
    id = db.Column(db.String, primary_key=True) # session_id
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    children = db.relationship('Child', backref='parent', lazy=True, cascade="all, delete-orphan")
    conversations = db.relationship('Conversation', backref='parent', lazy=True, cascade="all, delete-orphan")
    questionnaires = db.relationship('QuestionnaireResponse', backref='parent', lazy=True, cascade="all, delete-orphan")

class Child(db.Model):
    __tablename__ = 'child'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    parent_id = db.Column(db.String, db.ForeignKey('parent.id'), nullable=False)
    conversations = db.relationship('Conversation', backref='child', lazy=True)

class Conversation(db.Model):
    __tablename__ = 'conversation'
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.String, db.ForeignKey('parent.id'), nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey('child.id'), nullable=True)
    topic = db.Column(db.String(200), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade="all, delete-orphan")

class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    sender_type = db.Column(db.String(10), nullable=False) # 'user' or 'bot'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class QuestionnaireResponse(db.Model):
    __tablename__ = 'questionnaire_response'
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.String, db.ForeignKey('parent.id'), nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey('child.id'), nullable=False)
    response_data = db.Column(db.Text, nullable=False) # Storing as JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

