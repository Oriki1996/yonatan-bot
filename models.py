# models.py - מודלי הנתונים של מערכת "יונתן" (גרסה משודרגת)

import datetime
import json
import uuid
from collections import defaultdict

class ParentProfile:
    """פרופיל הורה במערכת יונתן - גרסה מורחבת"""
    
    def __init__(self, parent_id, name=None, gender=None):
        self.parent_id = parent_id
        self.name = name
        self.gender = gender # 'male' או 'female'
        self.created_at = datetime.datetime.now()
        self.last_active = datetime.datetime.now()
        self.session_count = 0
        self.message_count = 0
        
        # מידע על הילד
        self.child = {
            "age": None,
            "gender": None,
            "challenges": [],
            "strengths": []
        }
        
        # מידע טיפולי
        self.treatment_phase = 1
        self.risk_level = 0
        self.tools = []
        self.goals = []
        self.measurements = []
        
        self.interaction_history = []
    
    def to_dict(self):
        """המרת הפרופיל למילון"""
        return {
            "parent_id": self.parent_id,
            "name": self.name,
            "gender": self.gender,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "session_count": self.session_count,
            "message_count": self.message_count,
            "child": self.child,
            "treatment_phase": self.treatment_phase,
            "risk_level": self.risk_level,
            "tools": self.tools,
            "goals": self.goals,
            "measurements": self.measurements
        }
    
    @classmethod
    def from_dict(cls, data):
        """יצירת פרופיל מתוך מילון"""
        profile = cls(data["parent_id"], data.get("name"), data.get("gender"))
        profile.created_at = datetime.datetime.fromisoformat(data["created_at"])
        profile.last_active = datetime.datetime.fromisoformat(data["last_active"])
        profile.session_count = data.get("session_count", 0)
        profile.message_count = data.get("message_count", 0)
        profile.child = data.get("child", {})
        profile.treatment_phase = data.get("treatment_phase", 1)
        profile.risk_level = data.get("risk_level", 0)
        profile.tools = data.get("tools", [])
        profile.goals = data.get("goals", [])
        profile.measurements = data.get("measurements", [])
        return profile
    
    def update_last_active(self):
        """עדכון זמן הפעילות האחרון"""
        self.last_active = datetime.datetime.now()
        
    def add_message(self):
        """הוספת הודעה לספירה"""
        self.message_count += 1
        self.update_last_active()
    
    def add_session(self):
        """הוספת שיחה לספירה"""
        self.session_count += 1
        self.update_last_active()

class AnalyticsManager:
    """מנהל אנליטיקה ומעקב נתונים"""
    
    def __init__(self):
        self.sessions_data = defaultdict(list)
        self.daily_stats = defaultdict(int)
        self.risk_assessments = []
    
    def log_session(self, session_id, parent_id, duration, message_count):
        """תיעוד שיחה"""
        session_data = {
            "session_id": session_id,
            "parent_id": parent_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "duration": duration,
            "message_count": message_count
        }
        self.sessions_data[parent_id].append(session_data)
    
    def generate_daily_report(self):
        """יצירת דוח יומי"""
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        return {
            "date": today,
            "total_sessions": len(self.sessions_data),
            "total_messages": sum(self.daily_stats.values()),
            "active_users": len([p for p in self.sessions_data if self.sessions_data[p]])
        }

class SessionManager:
    """מנהל שיחות ומעקב סשנים"""
    
    def __init__(self):
        self.active_sessions = {}
        self.parent_profiles = {}
    
    def create_session(self, parent_id):
        """יצירת שיחה חדשה"""
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "parent_id": parent_id,
            "start_time": datetime.datetime.now(),
            "messages": [],
            "context": {}
        }
        self.active_sessions[session_id] = session_data
        
        if parent_id not in self.parent_profiles:
            self.parent_profiles[parent_id] = ParentProfile(parent_id)
        
        self.parent_profiles[parent_id].add_session()
        return session_id
    
    def add_message(self, session_id, role, content):
        """הוספת הודעה לשיחה"""
        if session_id in self.active_sessions:
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.datetime.now().isoformat()
            }
            self.active_sessions[session_id]["messages"].append(message)
            
            parent_id = self.active_sessions[session_id]["parent_id"]
            if parent_id in self.parent_profiles:
                self.parent_profiles[parent_id].add_message()