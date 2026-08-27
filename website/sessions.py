import uuid
import jwt
from flask import request, redirect, url_for, flash, make_response, current_app
from functools import wraps
from datetime import datetime, timedelta
from user_agents import parse
import requests
from common_models.src import current_utc_time

JWT_ALGORITHM = 'HS256'
SESSION_COOKIE_NAME = 'session_token'
SESSION_DURATION = timedelta(days=7)

def get_user_session_timeout(user):
    if user.is_admin or user.is_auditor or user.is_approver or user.is_reader:
        return timedelta(hours=9)
    return timedelta(minutes=60)

def create_session_token(user):
    ua_string = request.headers.get('User-Agent', '')
    user_agent = parse(ua_string)
    
    ip = request.remote_addr or '127.0.0.1'
    now = current_utc_time()
    
    payload = {
        'user_id': user.id,
        'email': user.email,
        'is_admin': user.is_admin,
        'is_auditor': user.is_auditor,
        'full_name': f"{user.last_name} {user.first_name} {user.patronymic_name or ''}".strip(),
        'session_id': str(uuid.uuid4()),
        'created_at': now.isoformat(),
        'last_active': now.isoformat(),
        'exp': (now + SESSION_DURATION).timestamp()
    }
    
    token = jwt.encode(
        payload,
        current_app.config['SECRET_KEY'],
        algorithm=JWT_ALGORITHM
    )
    
    return token

def set_session_cookie(response, token):
    response.set_cookie(
        SESSION_COOKIE_NAME,
        value=token,
        max_age=int(SESSION_DURATION.total_seconds()),
        httponly=True,
        secure=False,
        samesite='Lax',
        path='/'
    )
    return response

def create_login_response(user, redirect_endpoint='views.account'):
    response = redirect(url_for(redirect_endpoint))
    token = create_session_token(user)
    return set_session_cookie(response, token)

def verify_session_token(token):
    try:
        payload = jwt.decode(
            token,
            current_app.config['SECRET_KEY'],
            algorithms=[JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        print("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        print(f"Invalid token: {e}")
        return None

def get_session_from_cookie():
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    return verify_session_token(token)

def update_session_activity(token):
    try:
        payload = jwt.decode(
            token,
            current_app.config['SECRET_KEY'],
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": False}
        )
        
        payload['last_active'] = current_utc_time().isoformat()
        
        new_token = jwt.encode(
            payload,
            current_app.config['SECRET_KEY'],
            algorithm=JWT_ALGORITHM
        )
        
        return new_token
    except jwt.InvalidTokenError:
        return None

def describe_device(ua_string):
    try:
        ua = parse(ua_string or '')
        browser = ua.browser.family or 'Браузер'
        os_name = ua.os.family or ''
        return f"{browser} · {os_name}".strip(' ·') or 'Неизвестное устройство'
    except Exception:
        return 'Неизвестное устройство'

def build_session_info(user, payload=None):
    """Session data used by the 'Сессии' section on the profile page
    and by the /api/session-info endpoint."""
    timeout = get_user_session_timeout(user)
    now = current_utc_time()

    last_active = now
    created_at = now
    device = describe_device(request.headers.get('User-Agent', ''))

    if payload:
        try:
            last_active = datetime.fromisoformat(payload.get('last_active'))
        except (TypeError, ValueError):
            pass
        try:
            created_at = datetime.fromisoformat(payload.get('created_at'))
        except (TypeError, ValueError):
            pass

    expires_at = last_active + timeout

    if user.is_admin:
        role_label = 'Администратор'
    elif user.is_auditor:
        role_label = 'Аудитор'
    elif user.is_approver:
        role_label = 'Утверждающий'
    elif user.is_reader:
        role_label = 'Читатель'
    else:
        role_label = 'Респондент'

    return {
        'role_label': role_label,
        'timeout_minutes': int(timeout.total_seconds() // 60),
        'created_at': created_at.isoformat(),
        'last_active': last_active.isoformat(),
        'expires_at': expires_at.isoformat(),
        'server_time': now.isoformat(),
        'device': device,
        'ip': request.remote_addr or '',
    }

def get_or_refresh_session(user):
    """Read the idle-tracking token for the current request, refreshing its
    last_active timestamp, or mint a fresh one if it's missing/expired
    (e.g. debug mode, where @session_required never sets the cookie, or a
    session created before this token existed). Returns (token, payload)."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    payload = verify_session_token(token) if token else None

    if payload:
        token = update_session_activity(token) or token
    else:
        token = create_session_token(user)

    return token, verify_session_token(token)

def force_logout():
    response = make_response(redirect(url_for('views.login')))
    response.delete_cookie(SESSION_COOKIE_NAME, path='/')
    flash('Сессия недействительна или истекла. Пожалуйста, войдите снова', 'error')
    return response

def session_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        from flask_login import current_user
        from .models import User
        from . import db

        if current_app.debug:
            return view_func(*args, **kwargs)

        token = request.cookies.get(SESSION_COOKIE_NAME)
        session_data = verify_session_token(token) if token else None

        if not session_data:
            if not current_user.is_authenticated:
                print("No session token in cookie")
                return force_logout()
            # Flask-Login's own session is still valid, but our idle-tracking
            # token is missing/expired (e.g. it didn't exist yet when this
            # user logged in). Self-heal instead of forcing a disruptive
            # logout on an otherwise legitimate session.
            user = current_user._get_current_object()
            token = create_session_token(user)
            session_data = verify_session_token(token)
        else:
            user = User.query.get(session_data['user_id'])
            if not user:
                print(f"User not found: {session_data['user_id']}")
                return force_logout()

        last_active = datetime.fromisoformat(session_data['last_active'])
        current_time = current_utc_time()
        
        if hasattr(current_time, 'tzinfo') and current_time.tzinfo is not None:
            current_time = current_time.replace(tzinfo=None)
        if hasattr(last_active, 'tzinfo') and last_active.tzinfo is not None:
            last_active = last_active.replace(tzinfo=None)
        
        session_timeout = get_user_session_timeout(user)
        time_diff = current_time - last_active
        
        if time_diff > session_timeout:
            return force_logout()
        
        user.last_active = current_utc_time()
        db.session.commit()

        new_token = update_session_activity(token)
        response = view_func(*args, **kwargs)
        
        if isinstance(response, str):
            response = make_response(response)
        
        if new_token and new_token != token:
            response = set_session_cookie(response, new_token)
        return response
    
    return wrapper

def get_current_user():
    from .models import User
    
    session_data = get_session_from_cookie()
    if session_data:
        return User.query.get(session_data['user_id'])
    return None

def clear_session_cookie(response):
    response.delete_cookie(SESSION_COOKIE_NAME, path='/')
    return response