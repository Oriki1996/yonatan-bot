# config.py - Manages application configuration for different environments
import os
from dotenv import load_dotenv

# Load environment variables from .env file for local development
load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a_default_secret_key_for_development')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    # For local development, use a SQLite database in the instance folder
    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    os.makedirs(instance_path, exist_ok=True)
    db_path = os.path.join(instance_path, 'yonatan.db')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    # In production, get the database URL from the environment variable set by Render
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)


# Dictionary to map environment names to configuration classes
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}
