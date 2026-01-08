"""
Автоматическая генерация Swagger документации для всех моделей БД
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from flasgger import swag_from
from functools import wraps
from decimal import Decimal
import inspect
from sqlalchemy import inspect as sqlalchemy_inspect

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# Словарь для преобразования типов SQLAlchemy в Swagger типы
TYPE_MAPPING = {
    'Integer': {'type': 'integer', 'format': 'int32'},
    'String': {'type': 'string'},
    'Boolean': {'type': 'boolean'},
    'DateTime': {'type': 'string', 'format': 'date-time'},
    'Date': {'type': 'string', 'format': 'date'},
    'Numeric': {'type': 'number', 'format': 'float'},
    'Float': {'type': 'number', 'format': 'float'},
    'Text': {'type': 'string'},
    'JSON': {'type': 'object'}
}

def admin_required(f):
    """Декоратор для проверки прав администратора"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Требуется авторизация'}), 401
        if not getattr(current_user, 'is_admin', False):
            return jsonify({'error': 'Доступ запрещен. Требуются права администратора'}), 403
        return f(*args, **kwargs)
    return decorated

def get_swagger_type(column_type):
    """Получение Swagger типа из SQLAlchemy типа"""
    type_str = str(column_type)
    
    for sql_type, swagger_type in TYPE_MAPPING.items():
        if sql_type in type_str:
            return swagger_type
    
    return {'type': 'string'}

def serialize_value(value):
    """Сериализация значения для JSON"""
    if value is None:
        return None
    elif isinstance(value, Decimal):
        return float(value)
    elif hasattr(value, 'isoformat'):  # datetime/date
        return value.isoformat()
    elif isinstance(value, (list, dict)):
        return value
    else:
        return str(value)

def model_to_dict(model_instance):
    """Конвертация модели SQLAlchemy в словарь"""
    result = {}
    inspector = sqlalchemy_inspect(model_instance.__class__)
    
    for column in inspector.columns:
        column_name = column.name
        value = getattr(model_instance, column_name, None)
        result[column_name] = serialize_value(value)
    
    if hasattr(model_instance, '__relationships__'):
        for rel_name in model_instance.__relationships__:
            if hasattr(model_instance, rel_name):
                rel_value = getattr(model_instance, rel_name)
                if rel_value:
                    if isinstance(rel_value, list):
                        result[rel_name] = [model_to_dict(item) for item in rel_value]
                    else:
                        result[rel_name] = model_to_dict(rel_value)
    
    return result

def register_models_for_api(app, db):
    """Регистрация автоматических API endpoints для всех моделей"""
    
    models = get_models_from_db(db)

    endpoints_config = {
        'users': {'model': models['User'], 'name_ru': 'Пользователи', 'admin_only': True},
        'regions': {'model': models['Region'], 'name_ru': 'Регионы', 'admin_only': True},
        'ministries': {'model': models['Ministry'], 'name_ru': 'Министерства', 'admin_only': True},
        'organizations': {'model': models['Organization'], 'name_ru': 'Организации', 'admin_only': True},
        'plans': {'model': models['Plan'], 'name_ru': 'Планы', 'admin_only': True},
        'tickets': {'model': models['Ticket'], 'name_ru': 'Тикеты', 'admin_only': True},
        'units': {'model': models['Unit'], 'name_ru': 'Единицы измерения', 'admin_only': True},
        'directions': {'model': models['Direction'], 'name_ru': 'Направления', 'admin_only': True},
        'economic-measures': {'model': models['EconMeasure'], 'name_ru': 'Экономические меры', 'admin_only': True},
        'economic-executions': {'model': models['EconExec'], 'name_ru': 'Исполнения мер', 'admin_only': True},
        'indicators': {'model': models['Indicator'], 'name_ru': 'Показатели', 'admin_only': True},
        'indicator-usages': {'model': models['IndicatorUsage'], 'name_ru': 'Использование показателей', 'admin_only': True},
        'notifications': {'model': models['Notification'], 'name_ru': 'Уведомления', 'admin_only': True}
    }
    
    for endpoint, config in endpoints_config.items():
        create_model_endpoints(endpoint, config, db)
    
    register_custom_endpoints()
    
    app.register_blueprint(api_bp)

def get_models_from_db(db):
    """Получение всех моделей из SQLAlchemy"""
    from .models import (
        User, Region, Ministry, Organization, Plan, Ticket,
        Unit, Direction, EconMeasure, EconExec, Indicator,
        IndicatorUsage, Notification
    )
    
    return {
        'User': User,
        'Region': Region,
        'Ministry': Ministry,
        'Organization': Organization,
        'Plan': Plan,
        'Ticket': Ticket,
        'Unit': Unit,
        'Direction': Direction,
        'EconMeasure': EconMeasure,
        'EconExec': EconExec,
        'Indicator': Indicator,
        'IndicatorUsage': IndicatorUsage,
        'Notification': Notification
    }

def create_model_endpoints(endpoint, config, db):
    """Создание CRUD endpoints для модели"""
    model = config['model']
    name_ru = config['name_ru']
    admin_only = config.get('admin_only', True)
    
    list_spec = generate_list_spec(endpoint, name_ru, model)
    detail_spec = generate_detail_spec(endpoint, name_ru)
    create_spec = generate_create_spec(endpoint, name_ru, model)
    update_spec = generate_update_spec(endpoint, name_ru, model)
    delete_spec = generate_delete_spec(endpoint, name_ru)
    
    # GET /api/v1/{endpoint} - получение всех записей
    @api_bp.route(f'/{endpoint}', methods=['GET'])
    @login_required
    @admin_required
    @swag_from(list_spec)
    def get_all():
        """Получить все записи"""
     
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        
        query = model.query
        
        if search:
            from sqlalchemy import or_
            filters = []
            for column in model.__table__.columns:
                if hasattr(column.type, 'length'):
                    filters.append(getattr(model, column.name).ilike(f'%{search}%'))
            if filters:
                query = query.filter(or_(*filters))
    
        for key, value in request.args.items():
            if key not in ['page', 'per_page', 'search'] and hasattr(model, key):
                try:
                    query = query.filter(getattr(model, key) == value)
                except:
                    pass

        items = query.paginate(page=page, per_page=per_page, error_out=False)
        
        result = []
        for item in items.items:
            result.append(model_to_dict(item))
        
        return jsonify({
            endpoint: result,
            'total': items.total,
            'page': page,
            'per_page': per_page,
            'pages': items.pages
        })
    
    # GET /api/v1/{endpoint}/{id} - получение одной записи
    @api_bp.route(f'/{endpoint}/<int:id>', methods=['GET'])
    @login_required
    @admin_required
    @swag_from(detail_spec)
    def get_one(id):
        """Получить запись по ID"""
        item = model.query.get_or_404(id)
        return jsonify(model_to_dict(item))
    
    # POST /api/v1/{endpoint} - создание записи
    @api_bp.route(f'/{endpoint}', methods=['POST'])
    @login_required
    @admin_required
    @swag_from(create_spec)
    def create():
        """Создать новую запись"""
        if admin_only and not getattr(current_user, 'is_admin', False):
            return jsonify({'error': 'Доступ запрещен'}), 403
            
        if not request.is_json:
            return jsonify({'error': 'Content-Type должен быть application/json'}), 400
        
        data = request.get_json()
        
        try:
            new_item = model()
            
            for key, value in data.items():
                if hasattr(new_item, key) and key not in ['id']:
                    setattr(new_item, key, value)
            
            db.session.add(new_item)
            db.session.commit()
            
            return jsonify(model_to_dict(new_item)), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
    
    # PUT /api/v1/{endpoint}/{id} - обновление записи
    @api_bp.route(f'/{endpoint}/<int:id>', methods=['PUT'])
    @login_required
    @admin_required
    @swag_from(update_spec)
    def update(id):
        """Обновить запись"""
        item = model.query.get_or_404(id)
        
        if not request.is_json:
            return jsonify({'error': 'Content-Type должен быть application/json'}), 400
        
        data = request.get_json()
        
        try:
            for key, value in data.items():
                if hasattr(item, key) and key not in ['id', 'created_at']:
                    setattr(item, key, value)
            
            db.session.commit()
            
            return jsonify(model_to_dict(item))
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
    
    # DELETE /api/v1/{endpoint}/{id} - удаление записи
    @api_bp.route(f'/{endpoint}/<int:id>', methods=['DELETE'])
    @login_required
    @admin_required
    @swag_from(delete_spec)
    def delete(id):
        """Удалить запись"""
        item = model.query.get_or_404(id)
        
        try:
            db.session.delete(item)
            db.session.commit()
            
            return jsonify({'message': f'{name_ru[:-1]} удален(a) успешно'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
    
    get_all.__name__ = f'get_all_{endpoint.replace("-", "_")}'
    get_one.__name__ = f'get_one_{endpoint.replace("-", "_")}'
    create.__name__ = f'create_{endpoint.replace("-", "_")}'
    update.__name__ = f'update_{endpoint.replace("-", "_")}'
    delete.__name__ = f'delete_{endpoint.replace("-", "_")}'

def generate_list_spec(endpoint, name_ru, model):
    """Генерация спецификации для списка"""
    return {
        'tags': [name_ru],
        'description': f'Получить список {name_ru.lower()}',
        'parameters': [
            {
                'name': 'page',
                'in': 'query',
                'type': 'integer',
                'required': False,
                'default': 1
            },
            {
                'name': 'per_page',
                'in': 'query',
                'type': 'integer',
                'required': False,
                'default': 20
            },
            {
                'name': 'search',
                'in': 'query',
                'type': 'string',
                'required': False
            }
        ],
        'responses': {
            200: {
                'description': f'Список {name_ru.lower()}',
                'schema': {
                    'type': 'object',
                    'properties': {
                        endpoint: {
                            'type': 'array',
                            'items': {'type': 'object'}
                        },
                        'total': {'type': 'integer'},
                        'page': {'type': 'integer'},
                        'per_page': {'type': 'integer'},
                        'pages': {'type': 'integer'}
                    }
                }
            }
        }
    }

def generate_detail_spec(endpoint, name_ru):
    return {
        'tags': [name_ru],
        'description': f'Получить {name_ru[:-1].lower()} по ID',
        'parameters': [{
            'name': 'id',
            'in': 'path',
            'type': 'integer',
            'required': True
        }],
        'responses': {
            200: {'description': f'{name_ru[:-1]} найден(a)'},
            404: {'description': f'{name_ru[:-1]} не найден(a)'}
        }
    }

def generate_create_spec(endpoint, name_ru, model):
    properties = {}
    
    for column in model.__table__.columns:
        if column.primary_key:
            continue
            
        column_type = get_swagger_type(column.type)
        properties[column.name] = {
            **column_type,
            'description': f'Поле {column.name}'
        }
    
    return {
        'tags': [name_ru],
        'description': f'Создать новую {name_ru[:-1].lower()}',
        'parameters': [{
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': properties
            }
        }],
        'responses': {
            201: {'description': f'{name_ru[:-1]} создан(a) успешно'},
            400: {'description': 'Ошибка валидации'}
        },
        'security': [{'Bearer': []}]
    }

def generate_update_spec(endpoint, name_ru, model):
    properties = {}
    
    for column in model.__table__.columns:
        if column.primary_key:
            continue
            
        column_type = get_swagger_type(column.type)
        properties[column.name] = {
            **column_type,
            'description': f'Поле {column.name}'
        }
    
    return {
        'tags': [name_ru],
        'description': f'Обновить {name_ru[:-1].lower()}',
        'parameters': [
            {
                'name': 'id',
                'in': 'path',
                'type': 'integer',
                'required': True
            },
            {
                'name': 'body',
                'in': 'body',
                'required': True,
                'schema': {
                    'type': 'object',
                    'properties': properties
                }
            }
        ],
        'responses': {
            200: {'description': f'{name_ru[:-1]} обновлен(a)'},
            404: {'description': f'{name_ru[:-1]} не найден(a)'}
        },
        'security': [{'Bearer': []}]
    }

def generate_delete_spec(endpoint, name_ru):
    return {
        'tags': [name_ru],
        'description': f'Удалить {name_ru[:-1].lower()} (только для администраторов)',
        'parameters': [{
            'name': 'id',
            'in': 'path',
            'type': 'integer',
            'required': True
        }],
        'responses': {
            200: {'description': f'{name_ru[:-1]} удален(a) успешно'},
            403: {'description': 'Доступ запрещен'},
            404: {'description': f'{name_ru[:-1]} не найден(a)'}
        },
        'security': [{'Bearer': []}]
    }

def register_custom_endpoints():
    """Регистрация пользовательских API endpoints"""
    
    @api_bp.route('/health', methods=['GET'])
    @swag_from({
        'tags': ['Система'],
        'description': 'Проверка работоспособности API (публичный доступ)',
        'responses': {
            200: {
                'description': 'Система работает',
                'schema': {
                    'type': 'object',
                    'properties': {
                        'status': {'type': 'string'},
                        'timestamp': {'type': 'string'}
                    }
                }
            }
        }
    })
    def health_check():
        """Проверка здоровья API (публичный доступ)"""
        from datetime import datetime
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'Economic Indicators API'
        })
    
    @api_bp.route('/stats', methods=['GET'])
    @login_required
    @admin_required
    @swag_from({
        'tags': ['Система'],
        'description': 'Статистика системы (только для администраторов)',
        'responses': {
            200: {
                'description': 'Статистика',
                'schema': {'type': 'object'}
            }
        },
        'security': [{'Bearer': []}]
    })
    def system_stats():
        """Статистика системы"""
        from .models import User, Plan, Organization
        return jsonify({
            'users_count': User.query.count(),
            'plans_count': Plan.query.count(),
            'organizations_count': Organization.query.count(),
            'active_plans': Plan.query.filter_by(is_draft=False).count()
        })
    
    @api_bp.route('/me', methods=['GET'])
    @login_required
    @admin_required
    @swag_from({
        'tags': ['Пользователи'],
        'description': 'Информация о текущем пользователе (только для администраторов)',
        'responses': {
            200: {
                'description': 'Информация о пользователе',
                'schema': {'type': 'object'}
            },
            401: {'description': 'Не авторизован'}
        },
        'security': [{'Bearer': []}]
    })
    def current_user_info():
        """Информация о текущем пользователе"""
        return jsonify(model_to_dict(current_user))
    
    