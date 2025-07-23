from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv

def create_app():
    """
    Flask app factory pattern - dit is best practice voor grotere apps
    """
    # Load environment variables
    load_dotenv()
    
    # Create Flask app
    app = Flask(__name__)
    
    # Basic configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # Enable CORS for API calls
    CORS(app)
    
    # Register routes
    from app.main import main_bp
    app.register_blueprint(main_bp)
    
    return app