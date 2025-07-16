# models.py - v10.1 - Fixed metadata naming conflict
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import json
import hashlib

db = SQLAlchemy()

def init_app_db(app):
    """Initializes the database extension."""
    db.init_app(app)
    # IMPORTANT: We no longer call db.create_all() here.
    # This will be done manually via a separate script.

# Helper function for generating secure IDs
def generate_secure_id(data: str) -> str:
    """Generate a secure hash for sensitive data"""
    return hashlib.sha256(data.encode()).hexdigest()[:16]

class Parent(db.Model):
    __tablename__ = 'parent'
    
    id = db.Column(db.String(100), primary_key=True)  # session_id
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_activity = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Enhanced fields
    email = db.Column(db.String(254), nullable=True)  # Optional email
    phone = db.Column(db.String(20), nullable=True)   # Optional phone
    preferred_language = db.Column(db.String(5), default='he')
    
    # Privacy and security
    data_processing_consent = db.Column(db.Boolean, default=False)
    marketing_consent = db.Column(db.Boolean, default=False)
    
    # Relationships
    children = db.relationship('Child', backref='parent', lazy=True, cascade="all, delete-orphan")
    conversations = db.relationship('Conversation', backref='parent', lazy=True, cascade="all, delete-orphan")
    questionnaires = db.relationship('QuestionnaireResponse', backref='parent', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Parent {self.name}>'
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'name': self.name,
            'gender': self.gender,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'preferred_language': self.preferred_language,
            'children_count': len(self.children)
        }
        
        if include_sensitive:
            data.update({
                'email': self.email,
                'phone': self.phone,
                'data_processing_consent': self.data_processing_consent,
                'marketing_consent': self.marketing_consent
            })
        
        return data
    
    def update_last_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now(timezone.utc)
    
    def get_active_conversations(self) -> List['Conversation']:
        """Get active conversations from last 24 hours"""
        from datetime import timedelta
        last_24h = datetime.now(timezone.utc) - timedelta(hours=24)
        return [conv for conv in self.conversations if conv.start_time >= last_24h]

class Child(db.Model):
    __tablename__ = 'child'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    parent_id = db.Column(db.String(100), db.ForeignKey('parent.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Enhanced fields
    birth_month = db.Column(db.Integer, nullable=True)  # Month of birth (1-12)
    school_grade = db.Column(db.String(20), nullable=True)
    special_needs = db.Column(db.Text, nullable=True)
    interests = db.Column(db.Text, nullable=True)  # JSON string
    
    # Privacy - anonymized identifier
    anonymous_id = db.Column(db.String(32), unique=True, nullable=True)
    
    # Relationships
    conversations = db.relationship('Conversation', backref='child', lazy=True)
    questionnaires = db.relationship('QuestionnaireResponse', backref='child', lazy=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.anonymous_id:
            self.anonymous_id = generate_secure_id(f"{self.name}_{self.parent_id}")
    
    def __repr__(self):
        return f'<Child {self.name}, Age {self.age}>'
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'name': self.name if include_sensitive else f"Child_{self.anonymous_id[:8]}",
            'gender': self.gender,
            'age': self.age,
            'created_at': self.created_at.isoformat(),
            'anonymous_id': self.anonymous_id
        }
        
        if include_sensitive:
            data.update({
                'birth_month': self.birth_month,
                'school_grade': self.school_grade,
                'special_needs': self.special_needs,
                'interests': json.loads(self.interests) if self.interests else []
            })
        
        return data
    
    def get_age_group(self) -> str:
        """Get age group category"""
        if self.age <= 14:
            return "early_teen"
        elif self.age <= 16:
            return "mid_teen"
        elif self.age <= 18:
            return "late_teen"
        else:
            return "young_adult"
    
    def add_interest(self, interest: str):
        """Add an interest to the child"""
        interests = json.loads(self.interests) if self.interests else []
        if interest not in interests:
            interests.append(interest)
            self.interests = json.dumps(interests, ensure_ascii=False)
    
    def remove_interest(self, interest: str):
        """Remove an interest from the child"""
        interests = json.loads(self.interests) if self.interests else []
        if interest in interests:
            interests.remove(interest)
            self.interests = json.dumps(interests, ensure_ascii=False)

class Conversation(db.Model):
    __tablename__ = 'conversation'
    
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.String(100), db.ForeignKey('parent.id'), nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey('child.id'), nullable=True)
    topic = db.Column(db.String(200), nullable=False)
    start_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    end_time = db.Column(db.DateTime, nullable=True)
    
    # Enhanced fields
    status = db.Column(db.String(20), default='active')  # active, completed, abandoned
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    satisfaction_rating = db.Column(db.Integer, nullable=True)  # 1-5 rating
    tags = db.Column(db.Text, nullable=True)  # JSON string of tags
    
    # Analytics
    message_count = db.Column(db.Integer, default=0)
    avg_response_time = db.Column(db.Float, nullable=True)  # seconds
    
    # Relationships
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Conversation {self.topic} - {self.start_time}>'
    
    def to_dict(self, include_messages: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'topic': self.topic,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status,
            'priority': self.priority,
            'satisfaction_rating': self.satisfaction_rating,
            'message_count': self.message_count,
            'avg_response_time': self.avg_response_time,
            'tags': json.loads(self.tags) if self.tags else []
        }
        
        if include_messages:
            data['messages'] = [msg.to_dict() for msg in self.messages]
        
        return data
    
    def add_tag(self, tag: str):
        """Add a tag to the conversation"""
        tags = json.loads(self.tags) if self.tags else []
        if tag not in tags:
            tags.append(tag)
            self.tags = json.dumps(tags, ensure_ascii=False)
    
    def remove_tag(self, tag: str):
        """Remove a tag from the conversation"""
        tags = json.loads(self.tags) if self.tags else []
        if tag in tags:
            tags.remove(tag)
            self.tags = json.dumps(tags, ensure_ascii=False)
    
    def mark_completed(self, satisfaction_rating: Optional[int] = None):
        """Mark conversation as completed"""
        self.status = 'completed'
        self.end_time = datetime.now(timezone.utc)
        if satisfaction_rating:
            self.satisfaction_rating = satisfaction_rating
        self.update_message_count()
    
    def update_message_count(self):
        """Update message count"""
        self.message_count = len(self.messages)
    
    def get_duration(self) -> Optional[float]:
        """Get conversation duration in minutes"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() / 60
        return None

class Message(db.Model):
    __tablename__ = 'message'
    
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    sender_type = db.Column(db.String(10), nullable=False)  # 'user' or 'bot'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Enhanced fields
    message_type = db.Column(db.String(20), default='text')  # text, image, file, card
    message_metadata = db.Column(db.Text, nullable=True)  # JSON string for additional data - FIXED: renamed from metadata
    is_edited = db.Column(db.Boolean, default=False)
    edited_at = db.Column(db.DateTime, nullable=True)
    
    # Analytics
    character_count = db.Column(db.Integer, default=0)
    word_count = db.Column(db.Integer, default=0)
    response_time = db.Column(db.Float, nullable=True)  # seconds from previous message
    
    # Quality metrics
    sentiment_score = db.Column(db.Float, nullable=True)  # -1 to 1
    toxicity_score = db.Column(db.Float, nullable=True)  # 0 to 1
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.content:
            self.character_count = len(self.content)
            self.word_count = len(self.content.split())
    
    def __repr__(self):
        return f'<Message {self.sender_type} - {self.timestamp}>'
    
    def to_dict(self, include_metadata: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'sender_type': self.sender_type,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'message_type': self.message_type,
            'character_count': self.character_count,
            'word_count': self.word_count,
            'is_edited': self.is_edited
        }
        
        if include_metadata:
            data.update({
                'message_metadata': json.loads(self.message_metadata) if self.message_metadata else {},
                'response_time': self.response_time,
                'sentiment_score': self.sentiment_score,
                'toxicity_score': self.toxicity_score
            })
        
        return data
    
    def edit_content(self, new_content: str):
        """Edit message content"""
        self.content = new_content
        self.is_edited = True
        self.edited_at = datetime.now(timezone.utc)
        self.character_count = len(new_content)
        self.word_count = len(new_content.split())
    
    def add_message_metadata(self, key: str, value: Any):
        """Add metadata to message - FIXED: renamed function"""
        message_metadata = json.loads(self.message_metadata) if self.message_metadata else {}
        message_metadata[key] = value
        self.message_metadata = json.dumps(message_metadata, ensure_ascii=False)
    
    def get_message_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value - FIXED: renamed function"""
        if not self.message_metadata:
            return default
        message_metadata = json.loads(self.message_metadata)
        return message_metadata.get(key, default)

class QuestionnaireResponse(db.Model):
    __tablename__ = 'questionnaire_response'
    
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.String(100), db.ForeignKey('parent.id'), nullable=False)
    child_id = db.Column(db.Integer, db.ForeignKey('child.id'), nullable=False)
    response_data = db.Column(db.Text, nullable=False)  # JSON string
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Enhanced fields
    version = db.Column(db.String(10), default='1.0')  # Questionnaire version
    completion_time = db.Column(db.Integer, nullable=True)  # seconds to complete
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4/IPv6
    user_agent = db.Column(db.Text, nullable=True)
    
    # Privacy
    is_anonymized = db.Column(db.Boolean, default=False)
    anonymized_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<QuestionnaireResponse {self.parent_id} - {self.created_at}>'
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'created_at': self.created_at.isoformat(),
            'version': self.version,
            'completion_time': self.completion_time,
            'is_anonymized': self.is_anonymized
        }
        
        if include_sensitive and not self.is_anonymized:
            data.update({
                'response_data': json.loads(self.response_data),
                'ip_address': self.ip_address,
                'user_agent': self.user_agent
            })
        elif not self.is_anonymized:
            # Include only non-sensitive parts of response_data
            response_data = json.loads(self.response_data)
            data['response_data'] = {
                'main_challenge': response_data.get('main_challenge'),
                'child_age': response_data.get('child_age'),
                'child_gender': response_data.get('child_gender')
            }
        
        return data
    
    def get_response_data(self) -> Dict[str, Any]:
        """Get parsed response data"""
        return json.loads(self.response_data)
    
    def anonymize(self):
        """Anonymize the questionnaire response"""
        if not self.is_anonymized:
            response_data = json.loads(self.response_data)
            
            # Remove or hash sensitive data
            if 'parent_name' in response_data:
                response_data['parent_name'] = f"Parent_{generate_secure_id(response_data['parent_name'])[:8]}"
            if 'child_name' in response_data:
                response_data['child_name'] = f"Child_{generate_secure_id(response_data['child_name'])[:8]}"
            
            # Remove completely identifying information
            for key in ['email', 'phone', 'address']:
                if key in response_data:
                    del response_data[key]
            
            self.response_data = json.dumps(response_data, ensure_ascii=False)
            self.is_anonymized = True
            self.anonymized_at = datetime.now(timezone.utc)
            self.ip_address = None
            self.user_agent = None
    
    def validate_response_data(self) -> bool:
        """Validate that response data is properly formatted"""
        try:
            data = json.loads(self.response_data)
            required_fields = ['parent_name', 'child_name', 'child_age', 'main_challenge']
            return all(field in data for field in required_fields)
        except (json.JSONDecodeError, KeyError):
            return False

# Database utility functions
def create_all_tables():
    """Create all database tables"""
    db.create_all()

def drop_all_tables():
    """Drop all database tables"""
    db.drop_all()

def get_db_stats() -> Dict[str, Any]:
    """Get database statistics"""
    return {
        'total_parents': Parent.query.count(),
        'total_children': Child.query.count(),
        'total_conversations': Conversation.query.count(),
        'total_messages': Message.query.count(),
        'total_questionnaires': QuestionnaireResponse.query.count(),
        'active_conversations': Conversation.query.filter_by(status='active').count(),
        'completed_conversations': Conversation.query.filter_by(status='completed').count()
    }

# Export all models
__all__ = [
    'db',
    'init_app_db',
    'Parent',
    'Child', 
    'Conversation',
    'Message',
    'QuestionnaireResponse',
    'create_all_tables',
    'drop_all_tables',
    'get_db_stats'
]