from flask import Flask, flash, jsonify, render_template, session, request, g, redirect, url_for
from flask_babel import Babel
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user, login_required
from flask_migrate import Migrate
from flask_babel import Babel, format_date
from .completion_db import create_database
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman
from flask_admin import Admin

from flasgger import Swagger
from .api_docs import register_models_for_api, api_bp

import os
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
socketio = SocketIO()
bcrypt = Bcrypt()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()

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

babel = Babel(
    locale_selector=get_locale,
    timezone_selector=get_timezone
)

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
        BABEL_DEFAULT_LOCALE = 'ru',

        SEND_FILE_MAX_AGE_DEFAULT=0,  # Отключить кэширование в разработке
    )

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
  
        
    db.init_app(app)
    socketio.init_app(app)
    babel.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    csrf.init_app(app)

    # csrf.exempt(api_bp)
    # register_models_for_api(app, db)
    
    Talisman(app, 
             force_https=False,  # True для продакшена
             content_security_policy=None)  # Временно отключить CSP
    
    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    # app.register_blueprint(api_bp)
    
    with app.app_context():
        db.create_all()
        create_database(app, db)

    from .admin_views import (
        MyMainView, UserView, OrganizationView, PlanView, TicketView, 
        UnitView, DirectionView, EconMeasureView, EconExecView, 
        IndicatorView, IndicatorUsageView, NotificationView
    )
    from .models import (
        User, Organization, Plan, Ticket, Unit, Direction, 
        EconMeasure, EconExec, Indicator, IndicatorUsage, Notification
    )

    admin = Admin(app, 'Админ-панель', index_view=MyMainView(), template_mode='bootstrap4')
    
    admin.add_view(UserView(User, db.session, name='Пользователи', category='Основные'))
    admin.add_view(OrganizationView(Organization, db.session, name='Организации', category='Основные'))
    admin.add_view(PlanView(Plan, db.session, name='Планы', category='Основные'))
    admin.add_view(TicketView(Ticket, db.session, name='Тикеты', category='Вспомогательные'))
    admin.add_view(UnitView(Unit, db.session, name='Единицы измерения', category='Справочники'))
    admin.add_view(DirectionView(Direction, db.session, name='Направления', category='Справочники'))
    admin.add_view(EconMeasureView(EconMeasure, db.session, name='Экономические меры', category='Данные'))
    admin.add_view(EconExecView(EconExec, db.session, name='Исполнения мер', category='Данные'))
    admin.add_view(IndicatorView(Indicator, db.session, name='Показатели', category='Справочники'))
    admin.add_view(IndicatorUsageView(IndicatorUsage, db.session, name='Использование показателей', category='Данные'))
    admin.add_view(NotificationView(Notification, db.session, name='Уведомления', category='Вспомогательные'))
    
    login_manager.init_app(app)
    login_manager.login_message = "Пожалуйста, авторизуйтесь для доступа к этой странице"
    login_manager.login_view = "auth.login"
    
    app.jinja_env.globals['format_date'] = format_date
    
    @app.context_processor
    def inject_get_locale():
        from . import get_locale
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