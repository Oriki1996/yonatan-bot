# config.py - Enhanced Production Ready Configuration
import os
import logging
from datetime import timedelta
from typing import Optional
from dotenv import load_dotenv

# טעינת משתני סביבה
load_dotenv()

class Config:
    """הגדרות בסיס"""
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production-immediately'
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # שעה
    
    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 0
    }
    
    # Flask
    JSON_AS_ASCII = False
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # API Keys
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_STRATEGY = 'fixed-window'
    RATELIMIT_HEADERS_ENABLED = True
    
    # Security Headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; img-src 'self' data:; connect-src 'self'"
    }
    
    # Chat Configuration
    MAX_MESSAGE_LENGTH = int(os.environ.get('MAX_MESSAGE_LENGTH', '5000'))
    SESSION_TIMEOUT = int(os.environ.get('SESSION_TIMEOUT', '1800'))  # 30 minutes
    MAX_SESSIONS_PER_IP = int(os.environ.get('MAX_SESSIONS_PER_IP', '10'))
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/yonatan.log')
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', '10485760'))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', '5'))
    
    # Error Monitoring
    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    
    # Features
    ENABLE_FALLBACK_SYSTEM = os.environ.get('FALLBACK_ENABLED', 'True').lower() == 'true'
    FALLBACK_TIMEOUT = int(os.environ.get('FALLBACK_TIMEOUT', '10'))
    
    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5000').split(',')
    
    @staticmethod
    def init_app(app):
        """אתחול נוסף לאפליקציה"""
        # הגדרת security headers
        @app.after_request
        def set_security_headers(response):
            for header, value in Config.SECURITY_HEADERS.items():
                response.headers[header] = value
            return response
        
        # הגדרת logging
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        # Error monitoring
        if Config.SENTRY_DSN:
            try:
                import sentry_sdk
                from sentry_sdk.integrations.flask import FlaskIntegration
                from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
                
                sentry_sdk.init(
                    dsn=Config.SENTRY_DSN,
                    integrations=[
                        FlaskIntegration(),
                        SqlalchemyIntegration()
                    ],
                    traces_sample_rate=1.0,
                    environment=os.environ.get('FLASK_ENV', 'production')
                )
            except ImportError:
                print("⚠️ Sentry SDK לא מותקן")

class DevelopmentConfig(Config):
    """הגדרות פיתוח"""
    DEBUG = True
    
    # יצירת נתיב בטוח לבסיס הנתונים
    basedir = os.path.abspath(os.path.dirname(__file__))
    instance_path = os.path.join(basedir, 'instance')
    
    # יצירת התיקייה אם לא קיימת
    try:
        os.makedirs(instance_path, exist_ok=True)
        db_path = os.path.join(instance_path, 'yonatan_dev.db')
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
    except OSError as e:
        print(f"Warning: Could not create instance directory: {e}")
        # fallback to memory database
        SQLALCHEMY_DATABASE_URI = "sqlite:///yonatan_dev.db"
    
    # Development specific settings
    WTF_CSRF_ENABLED = False  # להקל על פיתוח
    
    # Enhanced logging for development
    SQLALCHEMY_ECHO = True
    
    # CORS פתוח יותר לפיתוח
    CORS_ORIGINS = ['http://localhost:5000', 'http://127.0.0.1:5000']
    
    # Rate limiting רחב יותר לפיתוח
    RATELIMIT_STORAGE_URL = 'memory://'
    
    @staticmethod
    def init_app(app):
        """אתחול נוסף לפיתוח"""
        Config.init_app(app)
        
        # הגדרת logging מפורט לפיתוח
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # הדפסת הגדרות חשובות
        print("🔧 מצב פיתוח:")
        print(f"   - Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print(f"   - Debug: {app.config['DEBUG']}")
        print(f"   - CSRF: {app.config['WTF_CSRF_ENABLED']}")

class ProductionConfig(Config):
    """הגדרות פרודקשן"""
    DEBUG = False
    
    # קבלת URL של בסיס הנתונים
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # תיקון עבור Heroku/Render שמשתמשים בפרוטוקול postgres:// ישן
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    
    # אם אין URL, נשתמש בסיס נתונים מקומי
    if not SQLALCHEMY_DATABASE_URI:
        print("Warning: DATABASE_URL not set, using SQLite")
        SQLALCHEMY_DATABASE_URI = "sqlite:///yonatan_prod.db"
    
    # Production security
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Production performance
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 10,
        'pool_size': 20
    }
    
    # Production rate limiting - more restrictive
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    
    @staticmethod
    def init_app(app):
        """אתחול נוסף לפרודקשן"""
        Config.init_app(app)
        
        # הגדרת לוגים לפרודקשן
        from logging.handlers import RotatingFileHandler
        
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        file_handler = RotatingFileHandler(
            Config.LOG_FILE,
            maxBytes=Config.LOG_MAX_BYTES,
            backupCount=Config.LOG_BACKUP_COUNT
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        
        file_handler.setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
        app.logger.addHandler(file_handler)
        app.logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
        app.logger.info('🚀 Yonatan Bot Production Startup')
        
        # הדפסת הגדרות חשובות (ללא sensitive data)
        print("🏭 מצב פרודקשן:")
        print(f"   - Database: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
        print(f"   - Debug: {app.config['DEBUG']}")
        print(f"   - CSRF: {app.config['WTF_CSRF_ENABLED']}")
        print(f"   - Secure Cookies: {app.config.get('SESSION_COOKIE_SECURE', False)}")

class TestingConfig(Config):
    """הגדרות בדיקות"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    
    # Testing specific settings
    RATELIMIT_ENABLED = False
    LOGIN_DISABLED = True
    
    @staticmethod
    def init_app(app):
        """אתחול נוסף לבדיקות"""
        Config.init_app(app)
        
        # הגדרת logging מינימלי לבדיקות
        logging.basicConfig(level=logging.ERROR)
        
        print("🧪 מצב בדיקות:")
        print(f"   - Database: In-Memory SQLite")
        print(f"   - Rate Limiting: Disabled")
        print(f"   - CSRF: Disabled")

class StagingConfig(ProductionConfig):
    """הגדרות סביבת ביניים"""
    DEBUG = True
    
    # Staging specific settings
    SQLALCHEMY_ECHO = False
    
    # Less restrictive rate limiting for staging
    RATELIMIT_STORAGE_URL = 'memory://'
    
    @staticmethod
    def init_app(app):
        """אתחול נוסף לסביבת ביניים"""
        ProductionConfig.init_app(app)
        
        print("🎭 מצב סביבת ביניים:")
        print(f"   - Debug: {app.config['DEBUG']}")
        print(f"   - Database: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")

# מפת הגדרות
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'staging': StagingConfig,
    'default': DevelopmentConfig
}

# פונקציה לקבלת הגדרות נוכחיות
def get_config(config_name: Optional[str] = None) -> Config:
    """קבלת הגדרות לפי שם"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    config_class = config_by_name.get(config_name, DevelopmentConfig)
    return config_class()

# בדיקת הגדרות
def validate_config(config: Config) -> bool:
    """בדיקת תקינות הגדרות"""
    errors = []
    
    # בדיקות בסיסיות
    if not config.SECRET_KEY or config.SECRET_KEY == 'dev-secret-key-change-in-production-immediately':
        if os.environ.get('FLASK_ENV') == 'production':
            errors.append("SECRET_KEY must be set in production")
    
    if not config.GOOGLE_API_KEY:
        errors.append("GOOGLE_API_KEY is required")
    
    # בדיקת database URL
    if not config.SQLALCHEMY_DATABASE_URI:
        errors.append("Database URL is required")
    
    # בדיקת rate limiting
    if config.RATELIMIT_STORAGE_URL == 'memory://' and os.environ.get('FLASK_ENV') == 'production':
        print("⚠️ Warning: Using memory storage for rate limiting in production")
    
    if errors:
        print("❌ Configuration errors:")
        for error in errors:
            print(f"   - {error}")
        return False
    
    return True

# הגדרות נוספות לביטחון
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin'
}

# הגדרות לוגים
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# הגדרות מתקדמות
ADVANCED_SETTINGS = {
    'ENABLE_PROFILING': os.environ.get('ENABLE_PROFILING', 'False').lower() == 'true',
    'ENABLE_METRICS': os.environ.get('ENABLE_METRICS', 'False').lower() == 'true',
    'ENABLE_HEALTH_CHECK': os.environ.get('ENABLE_HEALTH_CHECK', 'True').lower() == 'true',
    'ENABLE_BACKGROUND_TASKS': os.environ.get('ENABLE_BACKGROUND_TASKS', 'False').lower() == 'true'
}

# Export הגדרות נוספות
__all__ = [
    'Config',
    'DevelopmentConfig', 
    'ProductionConfig',
    'TestingConfig',
    'StagingConfig',
    'config_by_name',
    'get_config',
    'validate_config',
    'SECURITY_HEADERS',
    'ADVANCED_SETTINGS'
]