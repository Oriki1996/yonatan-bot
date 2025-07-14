# config.py - Production Ready Configuration
import os
from dotenv import load_dotenv

# טעינת משתני סביבה
load_dotenv()

class Config:
    """הגדרות בסיס"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    
    # הגדרות נוספות
    PERMANENT_SESSION_LIFETIME = 1800  # 30 דקות
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    @staticmethod
    def init_app(app):
        """אתחול נוסף לאפליקציה"""
        pass

class DevelopmentConfig(Config):
    """הגדרות פיתוח"""
    DEBUG = True
    
    # יצירת נתיב בטוח לבסיס הנתונים
    basedir = os.path.abspath(os.path.dirname(__file__))
    instance_path = os.path.join(basedir, 'instance')
    
    # יצירת התיקייה אם לא קיימת
    try:
        os.makedirs(instance_path, exist_ok=True)
        db_path = os.path.join(instance_path, 'yonatan.db')
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
    except OSError as e:
        print(f"Warning: Could not create instance directory: {e}")
        # fallback to memory database
        SQLALCHEMY_DATABASE_URI = "sqlite:///yonatan.db"

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
    
    @staticmethod
    def init_app(app):
        """אתחול נוסף לפרודקשן"""
        Config.init_app(app)
        
        # הגדרת לוגים לפרודקשן
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler('logs/yonatan.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Yonatan startup')

class TestingConfig(Config):
    """הגדרות בדיקות"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# מפת הגדרות
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}