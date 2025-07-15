# errors.py - מערכת שגיאות מותאמות ליונתן הבוט
from typing import Optional, Dict, Any


class BotError(Exception):
    """
    מחלקת בסיס לכל שגיאות הבוט
    """
    status_code: int = 500
    error_type: str = "bot_error"
    user_message: str = "אירעה שגיאה במערכת"
    
    def __init__(self, 
                 message: str, 
                 status_code: Optional[int] = None,
                 user_message: Optional[str] = None,
                 error_details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code
        if user_message is not None:
            self.user_message = user_message
        self.error_details = error_details or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """המרה למילון לJSON response"""
        return {
            "error": self.user_message,
            "error_type": self.error_type,
            "status_code": self.status_code,
            "details": self.error_details
        }


class ValidationError(BotError):
    """שגיאת בדיקת נתונים"""
    status_code = 400
    error_type = "validation_error"
    user_message = "הנתונים שנשלחו לא תקינים"


class SessionNotFoundError(BotError):
    """שגיאת סשן לא נמצא"""
    status_code = 404
    error_type = "session_not_found"
    user_message = "הסשן לא נמצא או פג תוקף"


class SessionExpiredError(BotError):
    """שגיאת פג תוקף סשן"""
    status_code = 401
    error_type = "session_expired"
    user_message = "הסשן פג תוקף, אנא התחל מחדש"


class QuotaExceededError(BotError):
    """שגיאת חריגה מ-quota"""
    status_code = 429
    error_type = "quota_exceeded"
    user_message = "המערכת עמוסה, אנא נסה שוב מאוחר יותר"


class RateLimitExceededError(BotError):
    """שגיאת חריגה מ-rate limit"""
    status_code = 429
    error_type = "rate_limit_exceeded"
    user_message = "יותר מדי בקשות, אנא האט קצת"


class AIModelError(BotError):
    """שגיאת מודל AI"""
    status_code = 503
    error_type = "ai_model_error"
    user_message = "שגיאה במודל הבינה המלאכותית"


class DatabaseError(BotError):
    """שגיאת מסד נתונים"""
    status_code = 500
    error_type = "database_error"
    user_message = "שגיאה בשמירת נתונים"


class FallbackSystemError(BotError):
    """שגיאת מערכת fallback"""
    status_code = 503
    error_type = "fallback_system_error"
    user_message = "מערכת הגיבוי לא זמינה"


class ConfigurationError(BotError):
    """שגיאת הגדרות"""
    status_code = 500
    error_type = "configuration_error"
    user_message = "שגיאה בהגדרות המערכת"


class SecurityError(BotError):
    """שגיאת אבטחה"""
    status_code = 403
    error_type = "security_error"
    user_message = "בקשה חשודה נחסמה"


class MessageTooLongError(ValidationError):
    """שגיאת הודעה ארוכה מדי"""
    user_message = "ההודעה ארוכה מדי, אנא קצר אותה"


class InvalidMessageError(ValidationError):
    """שגיאת הודעה לא תקינה"""
    user_message = "ההודעה מכילה תוכן לא מתאים"


class ParentNotFoundError(SessionNotFoundError):
    """שגיאת הורה לא נמצא"""
    user_message = "פרטי ההורה לא נמצאו"


class ChildNotFoundError(SessionNotFoundError):
    """שגיאת ילד לא נמצא"""
    user_message = "פרטי הילד לא נמצאו"


class QuestionnaireNotFoundError(SessionNotFoundError):
    """שגיאת שאלון לא נמצא"""
    user_message = "השאלון לא נמצא, אנא מלא שוב"


class ConversationNotFoundError(SessionNotFoundError):
    """שגיאת שיחה לא נמצאה"""
    user_message = "השיחה לא נמצאה"


def handle_generic_error(error: Exception) -> BotError:
    """
    טיפול בשגיאות כלליות שלא נתפסו
    """
    error_message = str(error)
    
    # בדיקת סוגי שגיאות מוכרים
    if "quota" in error_message.lower() or "429" in error_message:
        return QuotaExceededError(
            message=f"Quota exceeded: {error_message}",
            error_details={"original_error": error_message}
        )
    elif "rate limit" in error_message.lower():
        return RateLimitExceededError(
            message=f"Rate limit exceeded: {error_message}",
            error_details={"original_error": error_message}
        )
    elif "database" in error_message.lower() or "sql" in error_message.lower():
        return DatabaseError(
            message=f"Database error: {error_message}",
            error_details={"original_error": error_message}
        )
    elif "google" in error_message.lower() or "api" in error_message.lower():
        return AIModelError(
            message=f"AI Model error: {error_message}",
            error_details={"original_error": error_message}
        )
    else:
        return BotError(
            message=f"Unexpected error: {error_message}",
            error_details={"original_error": error_message}
        )


def get_error_response(error: Exception) -> Dict[str, Any]:
    """
    קבלת תגובה מתאימה לשגיאה
    """
    if isinstance(error, BotError):
        return error.to_dict()
    else:
        # טיפול בשגיאות לא מוכרות
        handled_error = handle_generic_error(error)
        return handled_error.to_dict()


# מילון תרגומים לשגיאות נפוצות
ERROR_TRANSLATIONS = {
    "Internal Server Error": "שגיאה פנימית במערכת",
    "Bad Request": "בקשה לא תקינה",
    "Unauthorized": "גישה לא מורשית",
    "Forbidden": "פעולה אסורה",
    "Not Found": "לא נמצא",
    "Method Not Allowed": "שיטה לא מורשית",
    "Request Timeout": "זמן הבקשה פג",
    "Too Many Requests": "יותר מדי בקשות",
    "Service Unavailable": "השירות לא זמין"
}


def translate_error(error_message: str) -> str:
    """
    תרגום שגיאות אנגלית לעברית
    """
    return ERROR_TRANSLATIONS.get(error_message, error_message)