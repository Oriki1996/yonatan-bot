# models.py - v3.0 - Full Project Implementation
# Added SavedArticle model to support the dashboard feature set.

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Parent(db.Model):
    __tablename__ = 'parent'
    id = db.Column(db.String, primary_key=True) # session_id
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    children = db.relationship('Child', backref='parent', lazy=True, cascade="all, delete-orphan")
    conversations = db.relationship('Conversation', backref='parent', lazy=True, cascade="all, delete-orphan")
    practice_logs = db.relationship('PracticeLog', backref='parent', lazy=True, cascade="all, delete-orphan")
    saved_articles = db.relationship('SavedArticle', backref='parent', lazy=True, cascade="all, delete-orphan")

class Child(db.Model):
    __tablename__ = 'child'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    age_range = db.Column(db.String(50), nullable=False)
    parent_id = db.Column(db.String, db.ForeignKey('parent.id'), nullable=False)
    conversations = db.relationship('Conversation', backref='child', lazy=True, cascade="all, delete-orphan")
    practice_logs = db.relationship('PracticeLog', backref='child', lazy=True, cascade="all, delete-orphan")

class Conversation(db.Model):
    __tablename__ = 'conversation'
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.String, db.ForeignKey('parent.id'), nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey('child.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    main_topic = db.Column(db.String(200), nullable=True)
    sentiment = db.Column(db.String(100), nullable=True)
    is_open = db.Column(db.Boolean, default=True, nullable=False)
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade="all, delete-orphan")
    reflection = db.relationship('Reflection', backref='conversation', uselist=False, cascade="all, delete-orphan")

class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    role = db.Column(db.String(10), nullable=False) # 'user' or 'model'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Reflection(db.Model):
    __tablename__ = 'reflection'
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False, unique=True)
    summary = db.Column(db.Text, nullable=False)
    recommendation = db.Column(db.Text, nullable=True)
    suggested_tool = db.Column(db.String(200), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class PracticeLog(db.Model):
    """Represents a goal or technique the parent is practicing."""
    __tablename__ = 'practice_log'
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.String, db.ForeignKey('parent.id'), nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey('child.id'), nullable=False)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=True)
    technique_name = db.Column(db.String(200), nullable=False)
    # Status can be 'suggested', 'in_progress', 'completed'
    status = db.Column(db.String(50), default='suggested')
    notes = db.Column(db.Text, nullable=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SavedArticle(db.Model):
    """Represents an article saved by a parent for future reference."""
    __tablename__ = 'saved_article'
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.String, db.ForeignKey('parent.id'), nullable=False)
    # The 'article_key' will correspond to a key in a client-side dictionary of articles.
    article_key = db.Column(db.String(100), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

