"""
ActiZ Document Analyzer - Flask App Initialization
Enhanced version with proper configuration and error handling
"""

import logging
import os

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS


def create_app():
    """
    Flask app factory pattern - Enhanced voor ActiZ Document Analyzer
    """
    # Load environment variables
    load_dotenv()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Create Flask app
    app = Flask(__name__)

    # Enhanced configuration
    app.config["SECRET_KEY"] = os.getenv(
        "FLASK_SECRET_KEY", "dev-key-change-in-production"
    )
    app.config["MAX_CONTENT_LENGTH"] = int(
        os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)
    )  # 16MB default

    # Flask specific settings
    app.config["JSON_AS_ASCII"] = False  # Voor Nederlandse karakters
    app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True

    # Security headers
    @app.after_request
    def after_request(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

    # Enable CORS for API calls - configured voor development
    CORS(app, origins=["http://localhost:5000", "http://127.0.0.1:5000"])

    # Register blueprints
    try:
        from app.main import main_bp

        app.register_blueprint(main_bp)
        logger.info("✅ Main blueprint registered successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import main blueprint: {e}")
        raise

    # Error handlers
    @app.errorhandler(413)
    def too_large(e):
        """Handle file too large error"""
        return {
            "success": False,
            "error": f'Bestand te groot. Maximum grootte is {app.config["MAX_CONTENT_LENGTH"] // (1024*1024)}MB.',
        }, 413

    @app.errorhandler(404)
    def not_found(e):
        """Handle page not found"""
        if "/api/" in str(e) or "application/json" in str(e):
            return {"success": False, "error": "API endpoint niet gevonden"}, 404
        # For web pages, you might want to render an error template
        return {"success": False, "error": "Pagina niet gevonden"}, 404

    @app.errorhandler(500)
    def internal_error(e):
        """Handle internal server error"""
        logger.error(f"Internal server error: {str(e)}")
        return {
            "success": False,
            "error": "Interne server fout - neem contact op met IT support",
        }, 500

    # Health check endpoint op app niveau
    @app.route("/status")
    def status():
        """Global status endpoint"""
        return {
            "status": "healthy",
            "service": "ActiZ Document Analyzer",
            "version": "1.0",
        }

    logger.info("🚀 ActiZ Document Analyzer app initialized successfully")
    return app
