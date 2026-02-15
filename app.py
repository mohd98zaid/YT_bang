"""
Flask application for VideoDownloader Web.
"""
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('web_downloader.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Import core modules
from core.config import ConfigManager
from core.database import DatabaseManager
from core.web_downloader import WebDownloader
from api.routes import api, init_api

# Initialize Flask app
app = Flask(__name__)

# Configuration from environment variables
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')

# Configure CORS
if CORS_ORIGINS == '*':
    CORS(app, origins='*')
else:
    # Split comma-separated origins
    origins = [origin.strip() for origin in CORS_ORIGINS.split(',')]
    CORS(app, origins=origins)

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins=CORS_ORIGINS, async_mode='eventlet')

# Initialize components
config_manager = ConfigManager()
database = DatabaseManager()
downloader = WebDownloader(config_manager, database, socketio)

# Initialize API routes
init_api(downloader, config_manager, database)
app.register_blueprint(api, url_prefix='/api')


@app.route('/')
def index():
    """Main application page"""
    return render_template('index.html')


@app.route('/api/health')
def health_check():
    """Health check endpoint for Railway"""
    return jsonify({
        'status': 'healthy',
        'environment': FLASK_ENV,
        'version': '1.0.0'
    })


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logging.info("Client connected")
    socketio.emit('connected', {'message': 'Connected to server'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logging.info("Client disconnected")


@socketio.on('get_status')
def handle_get_status():
    """Send current status to client"""
    socketio.emit('queue_updated', None)


def initialize_ffmpeg():
    """Initialize static-ffmpeg"""
    # Skip if on Vercel or if import fails
    if os.environ.get('VERCEL'):
        logging.info("Running on Vercel - skipping static-ffmpeg initialization")
        return

    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
        logging.info("static-ffmpeg paths added")
    except ImportError:
        logging.warning("static-ffmpeg not found, high quality merges might fail")


# Initialize FFmpeg
initialize_ffmpeg()

# Start queue processor
downloader.start_queue_processor()

if __name__ == '__main__':
    # Get port from environment (Railway sets this)
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    
    # Determine debug mode
    debug_mode = FLASK_ENV == 'development'
    
    # Run the app
    logging.info(f"Starting VideoDownloader Web on {host}:{port}")
    logging.info(f"Environment: {FLASK_ENV}")
    logging.info(f"Debug mode: {debug_mode}")
    
    socketio.run(app, host=host, port=port, debug=debug_mode, use_reloader=False)
