# utils.py - פונקציות עזר ליונתן הבוט
import re
import html
import secrets
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from flask import request
import logging

logger = logging.getLogger(__name__)


def sanitize_input(text: str) -> str:
    """
    ניקוי וסניטציה של טקסט שהתקבל מהמשתמש
    """
    if not text:
        return ""
    
    # הסרת רווחים מיותרים
    text = text.strip()
    
    # escape HTML tags
    text = html.escape(text)
    
    # הסרת תווים מסוכנים
    text = re.sub(r'[<>"\']', '', text)
    
    # הגבלת אורך
    if len(text) > 5000:
        text = text[:5000]
    
    return text


def validate_hebrew_text(text: str) -> bool:
    """
    בדיקה שהטקסט מכיל עברית ותקין
    """
    if not text:
        return False
    
    # בדיקה שיש לפחות תו עברית אחד
    hebrew_pattern = r'[\u0590-\u05FF]'
    has_hebrew = bool(re.search(hebrew_pattern, text))
    
    # בדיקה שאין תווים מסוכנים
    dangerous_pattern = r'[<>{}|\\\^~`]'
    has_dangerous = bool(re.search(dangerous_pattern, text))
    
    return has_hebrew and not has_dangerous


def generate_secure_session_id() -> str:
    """
    יצירת session ID מאובטח
    """
    return secrets.token_urlsafe(32)


def validate_session_id(session_id: str) -> bool:
    """
    בדיקת תקינות session ID
    """
    if not session_id:
        return False
    
    # בדיקת אורך
    if len(session_id) < 10 or len(session_id) > 100:
        return False
    
    # בדיקת תווים מורשים בלבד
    if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
        return False
    
    return True


def validate_age(age: Any) -> bool:
    """
    בדיקת תקינות גיל
    """
    try:
        age_int = int(age)
        return 10 <= age_int <= 25
    except (ValueError, TypeError):
        return False


def validate_name(name: str) -> bool:
    """
    בדיקת תקינות שם
    """
    if not name or len(name) < 2 or len(name) > 100:
        return False
    
    # בדיקה שיש אותיות בלבד (עברית ואנגלית)
    if not re.match(r'^[a-zA-Z\u0590-\u05FF\s]+$', name):
        return False
    
    return True


def validate_email(email: str) -> bool:
    """
    בדיקת תקינות מייל (אופציונלי)
    """
    if not email:
        return True  # מייל אופציונלי
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))


def hash_sensitive_data(data: str) -> str:
    """
    hash נתונים רגישים
    """
    return hashlib.sha256(data.encode()).hexdigest()


def get_client_ip() -> str:
    """
    קבלת IP של הלקוח
    """
    # בדיקה אם יש proxy headers
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr or 'unknown'


def get_user_agent() -> str:
    """
    קבלת User-Agent של הלקוח
    """
    return request.headers.get('User-Agent', 'unknown')


def is_suspicious_request() -> bool:
    """
    בדיקה אם הבקשה חשודה
    """
    user_agent = get_user_agent().lower()
    
    # רשימת user agents חשודים
    suspicious_agents = [
        'bot', 'crawler', 'spider', 'scraper',
        'curl', 'wget', 'python-requests'
    ]
    
    for agent in suspicious_agents:
        if agent in user_agent:
            return True
    
    return False


def format_hebrew_date(date: datetime) -> str:
    """
    עיצוב תאריך בעברית
    """
    months = {
        1: 'ינואר', 2: 'פברואר', 3: 'מרץ', 4: 'אפריל',
        5: 'מאי', 6: 'יוני', 7: 'יולי', 8: 'אוגוסט',
        9: 'ספטמבר', 10: 'אוקטובר', 11: 'נובמבר', 12: 'דצמבר'
    }
    
    return f"{date.day} {months[date.month]} {date.year}"


def time_ago_hebrew(date: datetime) -> str:
    """
    זמן שעבר בעברית
    """
    now = datetime.now()
    diff = now - date
    
    if diff.days > 0:
        return f"לפני {diff.days} ימים"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"לפני {hours} שעות"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"לפני {minutes} דקות"
    else:
        return "לפני רגע"


def clean_message_for_ai(message: str) -> str:
    """
    ניקוי הודעה לפני שליחה ל-AI
    """
    # הסרת רווחים מיותרים
    message = message.strip()
    
    # החלפת line breaks מרובים
    message = re.sub(r'\n+', '\n', message)
    
    # הסרת תווים מיוחדים מסוכנים
    message = re.sub(r'[^\w\s\u0590-\u05FF.,!?;:()\-]', '', message)
    
    return message


def extract_keywords_hebrew(text: str) -> List[str]:
    """
    חילוץ מילות מפתח בעברית
    """
    # מילות עצירה בעברית
    stop_words = {
        'של', 'את', 'על', 'אל', 'עם', 'כל', 'זה', 'היא', 'הוא',
        'אני', 'אתה', 'אתם', 'הם', 'היו', 'היה', 'יש', 'אין',
        'לא', 'כן', 'רק', 'גם', 'אבל', 'או', 'אם', 'כי', 'מה',
        'איך', 'איפה', 'מתי', 'למה', 'מי', 'כמה', 'בגלל', 'בלי'
    }
    
    # פיצול למילים
    words = re.findall(r'[\u0590-\u05FF]+', text)
    
    # סינון מילות עצירה ומילים קצרות
    keywords = [word for word in words if len(word) > 2 and word not in stop_words]
    
    return list(set(keywords))  # הסרת כפילויות


def mask_sensitive_info(text: str) -> str:
    """
    מיסוך מידע רגיש בלוגים
    """
    # מיסוך מספרי טלפון
    text = re.sub(r'\b0\d{1,2}-?\d{7}\b', '05*-***-****', text)
    
    # מיסוך מיילים
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '***@***.***', text)
    
    # מיסוך מספרי זהות
    text = re.sub(r'\b\d{9}\b', '*********', text)
    
    return text


def create_error_id() -> str:
    """
    יצירת מזהה שגיאה ייחודי
    """
    return f"ERR-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"


def log_security_event(event_type: str, details: Dict[str, Any]):
    """
    רישום אירוע אבטחה
    """
    security_log = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        'ip': get_client_ip(),
        'user_agent': get_user_agent(),
        'details': details
    }
    
    logger.warning(f"Security Event: {event_type} - {details}")


def validate_request_size(max_size: int = 1024 * 1024) -> bool:
    """
    בדיקת גודל הבקשה
    """
    content_length = request.content_length
    if content_length and content_length > max_size:
        return False
    return True


def get_session_info() -> Dict[str, Any]:
    """
    קבלת מידע על הסשן הנוכחי
    """
    return {
        'ip': get_client_ip(),
        'user_agent': get_user_agent(),
        'timestamp': datetime.now().isoformat(),
        'is_suspicious': is_suspicious_request()
    }


def clean_filename(filename: str) -> str:
    """
    ניקוי שם קובץ
    """
    # הסרת תווים מסוכנים
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # הגבלת אורך
    if len(filename) > 255:
        filename = filename[:255]
    
    return filename


def is_valid_json(json_string: str) -> bool:
    """
    בדיקה אם מחרוזת היא JSON תקין
    """
    try:
        import json
        json.loads(json_string)
        return True
    except ValueError:
        return False


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    קיצור טקסט עם נקודות
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."


def count_hebrew_words(text: str) -> int:
    """
    ספירת מילים בעברית
    """
    hebrew_words = re.findall(r'[\u0590-\u05FF]+', text)
    return len(hebrew_words)


def detect_language(text: str) -> str:
    """
    זיהוי שפה פשוט
    """
    hebrew_chars = len(re.findall(r'[\u0590-\u05FF]', text))
    english_chars = len(re.findall(r'[a-zA-Z]', text))
    
    if hebrew_chars > english_chars:
        return 'he'
    elif english_chars > hebrew_chars:
        return 'en'
    else:
        return 'mixed'


def create_backup_filename(original_name: str) -> str:
    """
    יצירת שם קובץ גיבוי
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    name, ext = original_name.rsplit('.', 1) if '.' in original_name else (original_name, '')
    return f"{name}_backup_{timestamp}.{ext}" if ext else f"{name}_backup_{timestamp}"


def is_development_mode() -> bool:
    """
    בדיקה אם אנחנו במצב פיתוח
    """
    import os
    return os.environ.get('FLASK_ENV') == 'development'


def safe_int(value: Any, default: int = 0) -> int:
    """
    המרה בטוחה למספר שלם
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    המרה בטוחה למספר עשרוני
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def generate_csrf_token() -> str:
    """
    יצירת CSRF token
    """
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, session_token: str) -> bool:
    """
    אימות CSRF token
    """
    return token == session_token


def rate_limit_key(identifier: str) -> str:
    """
    יצירת מפתח לrate limiting
    """
    return f"rate_limit:{identifier}"


def get_memory_usage() -> Dict[str, Any]:
    """
    קבלת מידע על שימוש בזיכרון
    """
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    return {
        'rss': memory_info.rss,  # Resident Set Size
        'vms': memory_info.vms,  # Virtual Memory Size
        'percent': process.memory_percent()
    }