import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
from logging.handlers import RotatingFileHandler
from flask import render_template





limiter = Limiter(key_func=get_remote_address, default_limits=["50 per minute"])

# Load variables from .env file
load_dotenv()

# Initialize the database extension
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    
    # Fix for Neon/PostgreSQL URI (Render/Neon sometimes pass 'postgres://', but SQLAlchemy requires 'postgresql://')
    uri = os.getenv('DATABASE_URL')
    if uri and uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Bind the database to this app
    db.init_app(app)

    # Register blueprints/routes (We will create these next)
    from app.routes import auth_bp
    app.register_blueprint(auth_bp)

# Inject wallet balance into all HTML templates globally
    @app.context_processor
    def inject_wallet():
        from flask import session
        from app.models import User
        if session.get('user_id'):
            user = User.query.get(session['user_id'])
            if user:
                return dict(current_wallet_balance=user.wallet_balance)
        return dict(current_wallet_balance=0.00)
    
    # Native Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    # Production Server Logging
    if not app.debug:
        # Save logs to a file named 'parodymart.log', rotating at 1MB size limit
        file_handler = RotatingFileHandler('parodymart.log', maxBytes=1024 * 1024, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('ParodyMart Startup Sequence Activated')

    return app