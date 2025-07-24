"""
ActiZ Document Analyzer Flask Application
V1.4 - With proper configuration management
"""

from app.config import get_config
from flask import Flask


def create_app() -> Flask:
    """Application factory with configuration"""
    app = Flask(__name__)

    # Load configuration
    config = get_config()
    app.config.from_object(config)

    # Store config object for easy access
    app.config["APP_CONFIG"] = config

    # Register blueprints
    from app.main import main as main_blueprint

    app.register_blueprint(main_blueprint)

    return app


# For backwards compatibility
app = create_app()
