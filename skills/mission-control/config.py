import os

class Config:
    """Mission Control Flask App Configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mission-control-secret-key')
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'mission_control.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Memory search settings
    MEMORY_DIR = os.path.expanduser('~/.openclaw/workspace-memory-builder/memory')
