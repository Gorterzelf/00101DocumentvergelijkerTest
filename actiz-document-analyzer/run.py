from app import create_app
import os

# Create Flask app
app = create_app()

if __name__ == '__main__':
    # Development server settings
    debug_mode = os.getenv('FLASK_DEBUG', '1') == '1'
    port = int(os.getenv('PORT', 5000))
    
    print("🚀 Starting ActiZ Document Analyzer...")
    print(f"📡 Server will be available at: http://localhost:{port}")
    print("🛑 Use Ctrl+C to stop the server")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode
    )