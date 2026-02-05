from datetime import datetime
from logging.handlers import RotatingFileHandler
import os
import sys
from dotenv import load_dotenv

import logging

from flask import Flask, flash, render_template, session, request, g, redirect, url_for
from flask_babel import Babel
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_babel import format_date
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman

from .completion_db import create_database

# from flasgger import Swagger
# from .api_docs import register_models_for_api, api_bp

load_dotenv()

LANGUAGES = {
    'en': 'English',
    'ru': 'Русский',
    'be': 'Беларуский'
}

def get_locale():
    if 'language' in session and session['language'] in LANGUAGES:
        return session['language']

    user = getattr(g, 'user', None)
    if user and hasattr(user, 'locale') and user.locale in LANGUAGES:
        return user.locale

    return request.accept_languages.best_match(LANGUAGES)

def get_timezone():
    user = getattr(g, 'user', None)
    if user is not None and hasattr(user, 'timezone'):
        return user.timezone
    return None

"""Logging setup"""
def setup_logging(app):
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "py-app.log")
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10 mb
        backupCount=5,
        encoding='utf-8'
    )
    
    file_handler.setLevel(getattr(logging, log_level))
    file_handler.setFormatter(formatter)
    file_handler.set_name('file_handler')
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    console_handler.setFormatter(formatter)
    console_handler.set_name('console_handler')
    
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    
    root_logger.handlers.clear()
    
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    app.logger.handlers.clear()
    app.logger.propagate = True
    
    app.logger.info("=" * 60)
    app.logger.info(f"Launch time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    app.logger.info(f"Logging level: {log_level}")
    app.logger.info(f"Logs are recorded in: {log_file}")
    app.logger.info("=" * 60)
    

babel = Babel(
    locale_selector=get_locale,
    timezone_selector=get_timezone
)

db = SQLAlchemy()
socketio = SocketIO()
bcrypt = Bcrypt()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__, static_url_path='/static')

    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY'),
        SQLALCHEMY_DATABASE_URI=f"postgresql://{os.getenv('postrgeuser')}:{os.getenv('postrgepass')}@localhost:5432/{os.getenv('postrgedbname')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        BABEL_TRANSLATION_DIRECTORIES='translations',
        LANGUAGES=LANGUAGES,
        SESSION_SQLALCHEMY=db,
        SESSION_PERMANENT=True,
        SESSION_TYPE='sqlalchemy',
        FLASK_ADMIN_SWATCH='cosmo',
        BABEL_DEFAULT_LOCALE='ru',
        SEND_FILE_MAX_AGE_DEFAULT=0,
    )

    db.init_app(app)
    socketio.init_app(app)
    babel.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    csrf.init_app(app)
    
    setup_logging(app)
    
    Talisman(app, 
            force_https=False,
            content_security_policy=None)

    login_manager.init_app(app)
    login_manager.login_message = "Пожалуйста, авторизуйтесь для доступа к этой странице"
    login_manager.login_view = "auth.login"

    # Swagger(app, template={
    #     "swagger": "2.0",
    #     "info": {
    #         "title": "ErespondentS API",
    #         "description": "API для управления экономическими показателями и планами в ErespondentS\n\n**⚠️ Доступ только для администраторов ⚠️**\n\nДля использования API необходимо:\n1. Авторизоваться через /auth/login\n2. Иметь права администратора (is_admin = true)",
    #         "version": "1.0.0",
    #         "contact": {
    #             "name": "Администрация",
    #             "email": "info@kvantas-as.by"
    #         }
    #     },
    #     "securityDefinitions": {
    #         "Bearer": {
    #             "type": "apiKey",
    #             "name": "Authorization",
    #             "in": "header",
    #             "description": "Введите: Bearer <session_token>"
    #         }
    #     },
    #     "security": [{"Bearer": []}],
    #     "schemes": ["http", "https"],
    #     "consumes": ["application/json"],
    #     "produces": ["application/json"]
    # })
    
    # @app.route('/apidocs/')
    # @app.route('/apidocs/index.html')
    # @login_required
    # def swagger_ui():
    #     """Доступ к Swagger UI только для администраторов"""
    #     if not getattr(current_user, 'is_admin', False):
    #         flash('Доступ к API документации разрешен только администраторам', 'error')
    #         return redirect(url_for('views.begin_page'))
    #     return redirect('/apispec_1.json')
    
    # @api_bp.before_request
    # def restrict_api_to_admins():
    #     """Ограничиваем доступ ко всем API endpoints только для администраторов"""
    #     public_endpoints = ['api.health_check']
        
    #     if request.endpoint in public_endpoints:
    #         return
        
    #     if not current_user.is_authenticated:
    #         return jsonify({'error': 'Требуется авторизация'}), 401
        
    #     if not getattr(current_user, 'is_admin', False):
    #         return jsonify({'error': 'Доступ запрещен. Требуются права администратора'}), 403
    
    # csrf.exempt(api_bp)
    # register_models_for_api(app, db)

    from .routes.views import views
    from .routes.auth import auth
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    # app.register_blueprint(api_bp)
    
    with app.app_context():
        from .routes.admin import AdminSetup
        admin_setup = AdminSetup(app, db)
        admin_setup.setup()
        
    with app.app_context():
        db.create_all()
        create_database(app, db)
    
    app.jinja_env.globals['format_date'] = format_date
    
    @app.context_processor
    def inject_get_locale():
        return dict(get_locale=get_locale)
    
    @app.route('/static/<path:filename>')
    def custom_static(filename):
        from flask import send_from_directory
        return send_from_directory(app.static_folder, filename)
    
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        response.headers.remove('X-Frame-Options')
        return response
    
    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))
    
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html', hide_header=True), 404
    
    @app.before_request
    def check_admin_access():
        if request.path.startswith('/admin/'):
            if not current_user.is_authenticated:
                flash('Необходимо авторизоваться для доступа к админ-панели', 'error')
                return redirect(url_for('auth.login'))
            
            is_admin = False
            if hasattr(current_user, 'is_admin'):
                is_admin = getattr(current_user, 'is_admin', False)
            
            if not is_admin:
                flash('Недостаточно прав для доступа к админ-панели', 'error')
                return redirect(url_for('views.begin_page'))
    return app