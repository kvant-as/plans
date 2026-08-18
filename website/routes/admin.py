from flask_admin import AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView

from flask import flash, redirect, url_for, current_app
from flask_login import current_user

from website.models import (
    User, Organization, Region, Ministry, News,
    Plan, PlanTicket, PlanApprovalPath, PlanColumnConfig,
    Unit, Direction, Event, Indicator, IndicatorUsage, 
    Notification, StatPlan, StatPlanValue, Chat, ChatMessage
)

from common_models.src import current_utc_time

from sqlalchemy.exc import SQLAlchemyError

from functools import wraps
from datetime import datetime, timedelta

from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange
from wtforms import PasswordField

from werkzeug.security import generate_password_hash

from website import db
from flask_admin import Admin

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Необходимо авторизоваться', 'error')
            return redirect(url_for('auth.login'))
        
        is_admin = False
        if hasattr(current_user, 'is_admin'):
            is_admin = getattr(current_user, 'is_admin', False)
        
        if not is_admin:
            flash('Недостаточно прав для доступа к админ-панели', 'error')
            return redirect(url_for('views.begin_page'))
        
        return f(*args, **kwargs)
    return decorated_function


class AdminSetup:
    def __init__(self, app, db):
        self.app = app
        self.db = db
        self.admin = None
        
    def setup(self):  
         
        self.admin = Admin(
            self.app, 
            name='Админ-панель', 
            index_view=MyMainView(), 
            template_mode='bootstrap4'
        )
        
        views_config = {
            'user': (UserView, User, 'Пользователи', 'Основные'),
            'organization': (OrganizationView, Organization, 'Организации', 'Основные'),
            'region': (RegionView, Region, 'Регионы', 'Основные'),
            'ministry': (MinistryView, Ministry, 'Министерства', 'Основные'),
            'news': (NewsView, News, 'Новости', 'Основные'),
            'plan': (PlanView, Plan, 'Планы', 'Основные'),
            'plan_approval_path': (PlanApprovalPathView, PlanApprovalPath, 'Пути согласования', 'Планы'),
            'plan_column_config': (PlanColumnConfigView, PlanColumnConfig, 'Конфигурации колонок', 'Планы'),
            'ticket': (PlanTicketView, PlanTicket, 'Тикеты', 'Планы'),
            'unit': (UnitView, Unit, 'Единицы измерения', 'Справочники'),
            'direction': (DirectionView, Direction, 'Направления', 'Справочники'),
            'event': (EventView, Event, 'Мероприятия', 'Данные'),
            'indicator': (IndicatorView, Indicator, 'Показатели', 'Справочники'),
            'indicator_usage': (IndicatorUsageView, IndicatorUsage, 'Использование показателей', 'Данные'),
            'notification': (NotificationView, Notification, 'Уведомления', 'Вспомогательные'),
            'stat_plan': (StatPlanView, StatPlan, 'Статистические планы', 'Статистика'),
            'stat_plan_value': (StatPlanValueView, StatPlanValue, 'Значения статистики', 'Статистика'),
            'chat': (ChatView, Chat, 'Чаты', 'Вспомогательные'),
            'chat_message': (ChatMessageView, ChatMessage, 'Сообщения чатов', 'Вспомогательные'),
        }
        
        for view_class, model, name, category in views_config.values():
            self.admin.add_view(view_class(model, self.db.session, name=name, category=category))
        return self.admin
    
    def get_admin(self):
        return self.admin


class MyMainView(AdminIndexView):
    @expose('/')
    @admin_required
    def index(self):
        try:
            user_data = User.query.count()
            organization_data = Organization.query.count()
            now = current_utc_time()
            threshold = now - timedelta(minutes=3)
            active_users = User.query.filter(User.last_active >= threshold).count()
            week_ago = now - timedelta(days=7)
            new_users = User.query.filter(User.begin_time >= week_ago).count()
            admins_count = User.query.filter_by(is_admin=True).count()
            auditors_count = User.query.filter_by(is_auditor=True).count()
            respondents_count = User.query.filter(
                User.is_admin == False,
                User.is_auditor == False
            ).count()
            orgs_with_users = db.session.query(Organization).join(User).distinct().count()
            plan_data = Plan.query.count()
            draft_plans = Plan.query.filter_by(is_draft=True).count()
            approved_plans = Plan.query.filter_by(is_approved=True).count()
            tickets_count = PlanTicket.query.count()
            units_count = Unit.query.count()
            directions_count = Direction.query.count()
            execs_count = Event.query.count()
            indicators_count = Indicator.query.count()
            usages_count = IndicatorUsage.query.count()
            notifications_count = Notification.query.count()
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error in admin stats: {str(e)}")
            user_data = organization_data = active_users = new_users = 0
            admins_count = auditors_count = respondents_count = orgs_with_users = 0
            plan_data = draft_plans = approved_plans = 0
            tickets_count = units_count = directions_count = 0
            execs_count = indicators_count = usages_count = notifications_count = 0
            flash('Ошибка при получении статистики из базы данных', 'error')

        endpoints = {
            'users': 'user.index_view',
            'organizations': 'organization.index_view',
            'regions': 'region.index_view',
            'ministries': 'ministry.index_view',
            'news': 'news.index_view',
            'plans': 'plan.index_view',
            'tickets': 'ticket.index_view',
            'units': 'unit.index_view',
            'directions': 'direction.index_view',
            'events': 'event.index_view',
            'indicators': 'indicator.index_view',
            'indicator_usages': 'indicatorusage.index_view',
            'notifications': 'notification.index_view',
        }

        return self.render('admin/stats.html',
                        user_data=user_data,
                        organization_data=organization_data,
                        active_users=active_users,
                        new_users=new_users,
                        admins_count=admins_count,
                        auditors_count=auditors_count,
                        respondents_count=respondents_count,
                        orgs_with_users=orgs_with_users,
                        plan_data=plan_data,
                        draft_plans=draft_plans,
                        approved_plans=approved_plans,
                        tickets_count=tickets_count,
                        units_count=units_count,
                        directions_count=directions_count,
                        execs_count=execs_count,
                        indicators_count=indicators_count,
                        usages_count=usages_count,
                        notifications_count=notifications_count,
                        profile_url=url_for('views.profile'),
                        current_time=datetime.utcnow(),
                        endpoints=endpoints
                        )

    def is_accessible(self):
        if not current_user.is_authenticated:
            return False

        if hasattr(current_user, 'is_admin'):
            return getattr(current_user, 'is_admin', False)
        return False

    def inaccessible_callback(self, name, **kwargs):
        if not current_user.is_authenticated:
            flash('Необходимо авторизоваться для доступа к админ-панели', 'error')
            return redirect(url_for('auth.login'))

        flash('Недостаточно прав для доступа к админ-панели', 'error')
        return redirect(url_for('views.begin_page'))


class SecureModelView(ModelView):
    def is_accessible(self):
        if not current_user.is_authenticated:
            return False

        if hasattr(current_user, 'is_admin'):
            return getattr(current_user, 'is_admin', False)
        return False

    def inaccessible_callback(self, name, **kwargs):
        if not current_user.is_authenticated:
            flash('Необходимо авторизоваться для доступа к админ-панели', 'error')
            return redirect(url_for('auth.login'))

        flash('Недостаточно прав для доступа к этому разделу', 'error')
        return redirect(url_for('views.begin_page'))

    page_size = 50
    can_view_details = True
    can_export = True
    export_max_rows = 1000
    export_types = ['csv', 'json']

    column_display_pk = False
    create_modal = False
    edit_modal = False
    details_modal = False

    def handle_view_exception(self, exc):
        if isinstance(exc, SQLAlchemyError):
            current_app.logger.error(f"Database error in admin: {str(exc)}")
            flash(f'Ошибка базы данных: {str(exc)}', 'error')
            return True
        return super().handle_view_exception(exc)


# ====================== ВСЕ VIEWS ДЛЯ ENPLANS ======================

class UserView(SecureModelView):
    column_list = ['id', 'email', 'last_name', 'first_name', 'patronymic_name', 
                   'post', 'telephone', 'organization', 'is_admin', 'is_auditor', 
                   'last_active', 'begin_time']
    column_default_sort = ('id', True)
    column_sortable_list = ('id', 'email', 'last_name', 'first_name', 'last_active', 'begin_time')
    can_delete = True
    can_create = True
    can_edit = True
    can_export = True
    export_max_rows = 500
    export_types = ['csv']
    form_columns = ['email', 'last_name', 'first_name', 'patronymic_name', 
                    'post', 'telephone', 'organization', 
                    'is_admin', 'is_auditor']
    form_args = {
        'email': {
            'label': 'Email',
            'validators': [DataRequired(), Email(), Length(max=255)],
            'description': 'Введите email пользователя'
        },
        'last_name': {
            'label': 'Фамилия',
            'validators': [DataRequired(), Length(max=100)],
            'description': 'Введите фамилию'
        },
        'first_name': {
            'label': 'Имя',
            'validators': [DataRequired(), Length(max=100)],
            'description': 'Введите имя'
        },
        'patronymic_name': {
            'label': 'Отчество',
            'validators': [Length(max=100)],
            'description': 'Введите отчество (необязательно)'
        },
        'post': {
            'label': 'Должность',
            'validators': [Length(max=100)],
            'description': 'Введите должность'
        },
        'telephone': {
            'label': 'Телефон',
            'validators': [Length(max=20)],
            'description': 'Введите номер телефона'
        }
    }
    form_extra_fields = {
        'password': PasswordField(
            'Пароль',
            validators=[DataRequired(), Length(min=6)],
            description='Введите пароль для нового пользователя'
        )
    }
    column_exclude_list = ['password', 'reset_password_token', 'reset_password_expires']
    column_searchable_list = ['email', 'last_name', 'first_name', 'patronymic_name', 'telephone']
    column_filters = ['id', 'email', 'is_admin', 'is_auditor', 'organization_id']
    column_formatters = {
        'organization': lambda v, c, m, p: m.organization.full_name if m.organization else 'Не назначена',
        'is_admin': lambda v, c, m, p: '✅' if m.is_admin else '❌',
        'is_auditor': lambda v, c, m, p: '✅' if m.is_auditor else '❌',
        'last_active': lambda v, c, m, p: m.last_active.strftime('%d.%m.%Y %H:%M') if m.last_active else '',
        'begin_time': lambda v, c, m, p: m.begin_time.strftime('%d.%m.%Y %H:%M') if m.begin_time else ''
    }

    def on_model_change(self, form, model, is_created):
        if is_created:
            password = form.password.data
            if not password:
                flash('При создании пользователя необходимо указать пароль!', 'error')
                raise ValueError('Пароль обязателен при создании пользователя')
            model.password = generate_password_hash(password)

        model.last_active = datetime.utcnow()
        
        if model.is_admin or model.is_auditor:
            model.organization_id = None

    def get_edit_form(self):
        form = super().get_edit_form()
        if hasattr(form, 'password'):
            form.password = None
        return form

    def get_create_form(self):
        form = super().get_create_form()
        if not hasattr(form, 'password'):
            from wtforms import PasswordField
            form.password = PasswordField(
                'Пароль',
                validators=[DataRequired(), Length(min=6)],
                description='Введите пароль для нового пользователя'
            )
        return form


class OrganizationView(SecureModelView):
    column_list = ['id', 'full_name', 'okpo', 'ynp', 'region', 'ministry', 'is_active', 'is_regular', 'is_coordinator', 'is_approver', 'is_region_management', 'users']
    column_default_sort = ('id', True)
    column_sortable_list = ('id', 'full_name', 'is_active', 'is_regular', 'is_coordinator', 'is_approver', 'is_region_management')
    can_delete = True
    can_create = True
    can_edit = True
    can_export = True
    form_columns = ['full_name', 'okpo', 'ynp', 'region_id', 'ministry_id', 'is_active', 'is_regular', 'is_coordinator', 'is_approver', 'is_region_management']
    form_args = {
        'full_name': {
            'label': 'Полное наименование',
            'validators': [DataRequired(), Length(max=500)],
            'description': 'Полное название организации'
        },
        'okpo': {
            'label': 'ОКПО',
            'validators': [DataRequired(), Length(max=20)],
            'description': 'Код ОКПО организации'
        },
        'ynp': {
            'label': 'УНП',
            'validators': [Length(max=20)],
            'description': 'Учетный номер плательщика'
        },
        'region_id': {
            'label': 'Регион',
            'validators': [DataRequired()],
            'description': 'Выберите регион организации'
        },
        'ministry_id': {
            'label': 'Министерство',
            'validators': [],
            'description': 'Выберите министерство (необязательно)'
        },
        'is_active': {
            'label': 'Активна',
            'description': 'Активна ли организация'
        },
        'is_regular': {
            'label': 'Регулярная',
            'description': 'Является ли организация регулярной'
        },
        'is_coordinator': {
            'label': 'Координатор',
            'description': 'Является ли организация координатором'
        },
        'is_approver': {
            'label': 'Утверждающая',
            'description': 'Является ли организация утверждающей'
        },
        'is_region_management': {
            'label': 'Региональное управление',
            'description': 'Является ли организация региональным управлением'
        }
    }
    column_searchable_list = ['full_name', 'okpo', 'ynp']
    column_filters = ['id', 'is_active', 'region_id', 'ministry_id', 'is_regular', 'is_coordinator', 'is_approver', 'is_region_management']
    column_formatters = {
        'is_active': lambda v, c, m, p: '✅' if m.is_active else '❌',
        'is_regular': lambda v, c, m, p: '✅' if m.is_regular else '❌',
        'is_coordinator': lambda v, c, m, p: '✅' if m.is_coordinator else '❌',
        'is_approver': lambda v, c, m, p: '✅' if m.is_approver else '❌',
        'is_region_management': lambda v, c, m, p: '✅' if m.is_region_management else '❌',
        'users': lambda v, c, m, p: f'{len(m.users)} пользователей' if m.users else 'Нет пользователей',
        'region': lambda v, c, m, p: m.region.name if m.region else 'Не назначен',
        'ministry': lambda v, c, m, p: m.ministry.name if m.ministry else 'Не назначено'
    }

    def get_form(self):
        form = super().get_form()
        from wtforms import SelectField
        from website.models import Region, Ministry
        
        regions = Region.query.order_by(Region.name).all()
        region_choices = [(r.id, r.name) for r in regions]
        
        ministries = Ministry.query.order_by(Ministry.name).all()
        ministry_choices = [(r.id, r.name) for r in ministries]
        ministry_choices.insert(0, ('', 'Не выбрано'))
        
        form.region_id = SelectField(
            'Регион',
            validators=[DataRequired()],
            choices=region_choices,
            description='Выберите регион организации'
        )
        
        form.ministry_id = SelectField(
            'Министерство',
            validators=[],
            choices=ministry_choices,
            description='Выберите министерство (необязательно)',
            default=''
        )
        
        return form

class RegionView(SecureModelView):
    column_list = ['id', 'number', 'name']
    column_default_sort = ('id', True)
    column_sortable_list = ('id', 'number', 'name')
    can_delete = True
    can_create = True
    can_edit = True
    can_export = True
    form_columns = ['number', 'name']
    form_args = {
        'number': {
            'label': 'Номер',
            'validators': [DataRequired()],
            'description': 'Номер региона'
        },
        'name': {
            'label': 'Название',
            'validators': [DataRequired(), Length(max=255)],
            'description': 'Название региона'
        }
    }
    column_searchable_list = ['name']
    column_filters = ['id', 'number']


class MinistryView(SecureModelView):
    column_list = ['id', 'name']
    column_default_sort = ('id', True)
    column_sortable_list = ('id', 'name')
    can_delete = True
    can_create = True
    can_edit = True
    can_export = True
    form_columns = ['name']
    form_args = {
        'name': {
            'label': 'Название',
            'validators': [DataRequired(), Length(max=200)],
            'description': 'Название министерства'
        }
    }
    column_searchable_list = ['name']
    column_filters = ['id']


class NewsView(SecureModelView):
    column_list = ['id', 'title', 'is_published', 'published_at', 'views_count', 'is_enplans', 'is_erespondentn', 'created_time']
    column_default_sort = ('id', True)
    column_sortable_list = ('id', 'title', 'is_published', 'published_at', 'views_count', 'created_time')
    can_delete = True
    can_create = True
    can_edit = True
    can_export = True
    form_columns = ['title', 'text', 'img_name', 'is_erespondentn', 'is_enplans', 'is_published', 'published_at']
    form_args = {
        'title': {
            'label': 'Заголовок',
            'validators': [DataRequired(), Length(max=100)],
            'description': 'Заголовок новости'
        },
        'text': {
            'label': 'Текст',
            'validators': [DataRequired()],
            'description': 'Текст новости'
        },
        'img_name': {
            'label': 'Имя изображения',
            'validators': [Length(max=20)],
            'description': 'Имя файла изображения'
        }
    }
    column_searchable_list = ['title', 'text']
    column_filters = ['id', 'is_published']


class PlanView(SecureModelView):
    column_list = ['id', 'year', 'organization', 'user', 'is_draft', 'is_sent', 'is_approved', 'is_error', 'begin_time']
    column_default_sort = ('id', True)
    column_sortable_list = ('id', 'year', 'begin_time', 'change_time', 'sent_time')
    can_delete = True
    can_create = True
    can_edit = True
    can_export = True
    form_columns = ['year', 'organization', 'user', 'energy_saving', 'share_fuel',
                    'saving_fuel', 'share_energy', 'is_draft', 'is_control',
                    'is_sent', 'is_error', 'is_approved', 'afch', 'plan_type']
    form_args = {
        'year': {
            'label': 'Год',
            'validators': [DataRequired(), NumberRange(min=2000, max=2100)],
            'description': 'Год плана'
        }
    }
    column_searchable_list = ['year']
    column_filters = ['id', 'year', 'is_draft', 'is_control', 'is_sent', 'is_error', 'is_approved', 'afch']
    column_formatters = {
        'is_draft': lambda v, c, m, p: '📝 Черновик' if m.is_draft else '',
        'is_control': lambda v, c, m, p: '👁 Контроль' if m.is_control else '',
        'is_sent': lambda v, c, m, p: '📤 Отправлен' if m.is_sent else '',
        'is_error': lambda v, c, m, p: '❌ Ошибка' if m.is_error else '',
        'is_approved': lambda v, c, m, p: '✅ Утвержден' if m.is_approved else '',
        'afch': lambda v, c, m, p: '🏭 АФЧ' if m.afch else '',
        'begin_time': lambda v, c, m, p: m.begin_time.strftime('%d.%m.%Y %H:%M') if m.begin_time else '',
        'change_time': lambda v, c, m, p: m.change_time.strftime('%d.%m.%Y %H:%M') if m.change_time else '',
        'sent_time': lambda v, c, m, p: m.sent_time.strftime('%d.%m.%Y %H:%M') if m.sent_time else '',
        'organization': lambda v, c, m, p: m.organization.full_name if m.organization else '',
        'user': lambda v, c, m, p: f"{m.user.last_name} {m.user.first_name}" if m.user else ''
    }


class PlanTicketView(SecureModelView):
    column_list = ['id', 'plan', 'begin_time', 'luck', 'is_system', 'note']
    column_default_sort = ('begin_time', True)
    column_sortable_list = ('id', 'begin_time', 'luck', 'is_system')
    can_delete = True
    can_create = True
    can_edit = True
    can_export = True
    form_columns = ['plan', 'luck', 'is_system', 'note']
    form_args = {
        'plan': {'label': 'План', 'description': 'Связанный план'},
        'luck': {'label': 'Успешно', 'description': 'Успешно ли выполнен тикет'},
        'is_system': {'label': 'Системный', 'description': 'Является ли системным'},
        'note': {
            'label': 'Примечание',
            'validators': [DataRequired(), Length(max=500)],
            'description': 'Текст примечания'
        }
    }
    column_searchable_list = ['note']
    column_filters = ['id', 'luck', 'is_system', 'plan_id']
    column_formatters = {
        'luck': lambda v, c, m, p: '✅' if m.luck else '❌',
        'is_system': lambda v, c, m, p: '👤 Да' if m.is_system else '👥 Нет',
        'begin_time': lambda v, c, m, p: m.begin_time.strftime('%d.%m.%Y %H:%M') if m.begin_time else '',
        'plan': lambda v, c, m, p: f"План #{m.plan.id}" if m.plan else ''
    }


class UnitView(SecureModelView):
    column_list = ['id', 'name']
    column_default_sort = ('id', True)
    column_sortable_list = ('id', 'name')
    can_delete = True
    can_create = True
    can_edit = True
    can_export = True
    form_columns = ['name']
    form_args = {
        'name': {
            'label': 'Название',
            'validators': [DataRequired(), Length(max=400)],
            'description': 'Название единицы измерения'
        }
    }
    column_searchable_list = ['name']
    column_filters = ['id', 'name']


class DirectionView(SecureModelView):
    column_list = ['id', 'code', 'name', 'unit', 'is_econom', 'is_increase', 'DateStart', 'DateEnd']
    column_default_sort = ('id', True)
    column_sortable_list = ('id', 'code', 'name', 'DateStart', 'DateEnd')
    can_delete = True
    can_create = True
    can_edit = True
    can_export = True
    form_columns = ['code', 'name', 'unit', 'is_econom', 'is_increase', 'DateStart', 'DateEnd']
    form_args = {
        'code': {'label': 'Код', 'validators': [Length(max=400)], 'description': 'Код направления'},
        'name': {'label': 'Название', 'validators': [Length(max=400)], 'description': 'Название направления'},
        'unit': {'label': 'Единица измерения', 'description': 'Единица измерения'},
        'is_econom': {'label': 'Экономия', 'description': 'Является ли экономией'},
        'is_increase': {'label': 'Увеличение', 'description': 'Является ли увеличением'}
    }
    column_searchable_list = ['code', 'name']
    column_filters = ['id', 'is_econom', 'is_increase']
    column_formatters = {
        'is_econom': lambda v, c, m, p: '✅' if m.is_econom else '❌',
        'is_increase': lambda v, c, m, p: '✅' if m.is_increase else '❌',
        'DateStart': lambda v, c, m, p: m.DateStart.strftime('%d.%m.%Y') if m.DateStart else '',
        'DateEnd': lambda v, c, m, p: m.DateEnd.strftime('%d.%m.%Y') if m.DateEnd else '',
        'unit': lambda v, c, m, p: m.unit.name if m.unit else ''
    }


class EventView(SecureModelView):
    column_list = ['id', 'plan', 'name', 'Volume', 'EffTut', 'EffRub',
                   'ExpectedQuarter', 'EffCurrYear', 'Payback', 'is_local', 'is_corrected']
    column_default_sort = ('id', True)
    can_delete = True
    can_create = True
    can_edit = True
    can_export = True
    form_columns = ['plan', 'name', 'Volume', 'EffTut', 'EffRub',
                    'ExpectedQuarter', 'EffCurrYear', 'Payback', 'VolumeFinCurrentYear',
                    'BudgetState', 'BudgetRep', 'BudgetLoc', 'BudgetOther',
                    'MoneyOwn', 'MoneyLoan', 'MoneyOther', 'is_local', 'is_corrected', 'order']
    form_args = {
        'name': {
            'label': 'Название',
            'validators': [DataRequired(), Length(max=4000)],
            'description': 'Название мероприятия'
        },
        'is_local': {'label': 'Локальный', 'description': 'Является ли локальным'},
        'is_corrected': {'label': 'Корректированный', 'description': 'Был ли скорректирован'},
        'order': {'label': 'Порядок', 'validators': [Optional(), NumberRange(min=0)], 'description': 'Порядок сортировки'}
    }
    column_searchable_list = ['name']
    column_filters = ['id', 'is_local', 'is_corrected']
    column_formatters = {
        'is_local': lambda v, c, m, p: '✅' if m.is_local else '❌',
        'is_corrected': lambda v, c, m, p: 'Да' if m.is_corrected else 'Нет',
        'plan': lambda v, c, m, p: f"План #{m.plan.id}" if m.plan else ''
    }


class IndicatorView(SecureModelView):
    column_list = ['id', 'code', 'name', 'unit', 'CoeffToTut', 'IsMandatory', 'Group', 'RowN']
    column_default_sort = ('id', True)
    can_delete = True
    can_create = True
    can_edit = True
    can_export = True
    form_columns = ['code', 'name', 'unit', 'CoeffToTut', 'IsMandatory', 'Group', 'RowN', 'DateStart', 'DateEnd']
    form_args = {
        'code': {'label': 'Код', 'validators': [Length(max=400)], 'description': 'Код показателя'},
        'name': {'label': 'Название', 'validators': [Length(max=400)], 'description': 'Название показателя'},
        'unit': {'label': 'Единица измерения', 'description': 'Единица измерения'}
    }
    column_searchable_list = ['code', 'name']
    column_filters = ['id', 'IsMandatory', 'Group']
    column_formatters = {
        'IsMandatory': lambda v, c, m, p: '✅' if m.IsMandatory else '❌',
        'DateStart': lambda v, c, m, p: m.DateStart.strftime('%d.%m.%Y') if m.DateStart else '',
        'DateEnd': lambda v, c, m, p: m.DateEnd.strftime('%d.%m.%Y') if m.DateEnd else '',
        'unit': lambda v, c, m, p: m.unit.name if m.unit else ''
    }


class IndicatorUsageView(SecureModelView):
    column_list = ['id', 'plan', 'indicator', 'QYearBeforePrev', 'QYearPrev', 'QYearCurrent']
    column_default_sort = ('id', True)
    can_delete = True
    can_create = True
    can_edit = True
    can_export = True
    form_columns = ['plan', 'indicator', 'QYearBeforePrev', 'QYearPrev', 'QYearCurrent']
    form_args = {
        'plan': {'label': 'План', 'description': 'Связанный план'},
        'indicator': {'label': 'Показатель', 'description': 'Показатель'}
    }
    column_filters = ['id']
    column_formatters = {
        'plan': lambda v, c, m, p: f"План #{m.plan.id}" if m.plan else '',
        'indicator': lambda v, c, m, p: f"{m.indicator.code} - {m.indicator.name}" if m.indicator else ''
    }


class NotificationView(SecureModelView):
    column_list = ['id', 'user', 'message', 'is_read', 'created_at']
    column_default_sort = ('created_at', True)
    column_sortable_list = ('id', 'created_at', 'is_read')
    can_delete = True
    can_create = True
    can_edit = True
    can_export = True
    form_columns = ['user', 'message', 'is_read']
    form_args = {
        'user': {'label': 'Пользователь', 'description': 'Пользователь'},
        'message': {
            'label': 'Сообщение',
            'validators': [DataRequired(), Length(max=140)],
            'description': 'Текст уведомления'
        },
        'is_read': {'label': 'Прочитано', 'description': 'Прочитано ли уведомление'}
    }
    column_searchable_list = ['message']
    column_filters = ['id', 'is_read', 'user_id']
    column_formatters = {
        'is_read': lambda v, c, m, p: '✅' if m.is_read else '❌',
        'created_at': lambda v, c, m, p: m.created_at.strftime('%d.%m.%Y %H:%M') if m.created_at else '',
        'user': lambda v, c, m, p: f"{m.user.email}" if m.user else ''
    }


class PlanApprovalPathView(SecureModelView):
    column_list = ['id', 'plan', 'organization', 'step_order', 'step_type', 'is_viewed', 'created_at']
    column_default_sort = ('id', True)
    can_delete = True
    can_create = True
    can_edit = True
    can_export = True
    form_columns = ['plan', 'organization', 'step_order', 'step_type', 'is_viewed']
    form_args = {
        'plan': {'label': 'План', 'description': 'Связанный план'},
        'organization': {'label': 'Организация', 'description': 'Организация на шаге'},
        'step_order': {'label': 'Порядок шага', 'validators': [DataRequired()], 'description': 'Порядок шага согласования'},
        'step_type': {'label': 'Тип шага', 'description': 'Тип шага согласования'},
        'is_viewed': {'label': 'Просмотрено', 'description': 'Был ли просмотрен'}
    }
    column_filters = ['id', 'step_order', 'step_type', 'is_viewed']
    column_formatters = {
        'is_viewed': lambda v, c, m, p: '✅' if m.is_viewed else '❌',
        'step_type': lambda v, c, m, p: m.step_type_label,
        'created_at': lambda v, c, m, p: m.created_at.strftime('%d.%m.%Y %H:%M') if m.created_at else ''
    }


class PlanColumnConfigView(SecureModelView):
    column_list = ['id', 'plan', 'year', 'label']
    column_default_sort = ('id', True)
    can_delete = True
    can_create = True
    can_edit = True
    can_export = True
    form_columns = ['plan', 'year', 'label']
    form_args = {
        'plan': {'label': 'План', 'description': 'Связанный план'},
        'year': {'label': 'Год', 'validators': [DataRequired()], 'description': 'Год конфигурации'},
        'label': {'label': 'Метка', 'validators': [DataRequired(), Length(max=50)], 'description': 'Метка колонки'}
    }
    column_filters = ['id', 'year']


class StatPlanView(SecureModelView):
    column_list = ['id', 'organization', 'type', 'year', 'uploaded_by', 'uploaded_at']
    column_default_sort = ('id', True)
    can_delete = True
    can_create = True
    can_edit = True
    can_export = True
    form_columns = ['organization', 'type', 'year', 'uploaded_by']
    form_args = {
        'organization': {'label': 'Организация', 'description': 'Организация'},
        'type': {'label': 'Тип', 'validators': [DataRequired(), Length(max=10)], 'description': 'Тип статистического плана'},
        'year': {'label': 'Год', 'validators': [DataRequired()], 'description': 'Год статистического плана'},
        'uploaded_by': {'label': 'Загрузил', 'description': 'Кто загрузил'}
    }
    column_filters = ['id', 'type', 'year', 'organization_id']
    column_formatters = {
        'uploaded_at': lambda v, c, m, p: m.uploaded_at.strftime('%d.%m.%Y %H:%M') if m.uploaded_at else ''
    }


class StatPlanValueView(SecureModelView):
    column_list = ['id', 'stat_plan', 'row_code', 'row_name', 'column_code', 'value']
    column_default_sort = ('id', True)
    can_delete = True
    can_create = True
    can_edit = True
    can_export = True
    form_columns = ['stat_plan', 'row_code', 'row_name', 'column_code', 'value']
    form_args = {
        'stat_plan': {'label': 'Стат. план', 'description': 'Связанный статистический план'},
        'row_code': {'label': 'Код строки', 'validators': [DataRequired(), Length(max=20)], 'description': 'Код строки'},
        'row_name': {'label': 'Название строки', 'validators': [Length(max=500)], 'description': 'Название строки'},
        'column_code': {'label': 'Код колонки', 'validators': [DataRequired(), Length(max=10)], 'description': 'Код колонки'},
        'value': {'label': 'Значение', 'description': 'Числовое значение'}
    }
    column_filters = ['id', 'row_code', 'column_code']


class ChatView(SecureModelView):
    column_list = ['id', 'title', 'created_by', 'created_at', 'updated_at']
    column_default_sort = ('id', True)
    can_delete = True
    can_create = True
    can_edit = True
    can_export = True
    form_columns = ['title', 'created_by']
    form_args = {
        'title': {'label': 'Заголовок', 'validators': [Length(max=200)], 'description': 'Заголовок чата'},
        'created_by': {'label': 'Создатель', 'description': 'Кто создал чат'}
    }
    column_filters = ['id']
    column_formatters = {
        'created_at': lambda v, c, m, p: m.created_at.strftime('%d.%m.%Y %H:%M') if m.created_at else '',
        'updated_at': lambda v, c, m, p: m.updated_at.strftime('%d.%m.%Y %H:%M') if m.updated_at else ''
    }


class ChatMessageView(SecureModelView):
    column_list = ['id', 'chat', 'is_user', 'content', 'created_at']
    column_default_sort = ('id', True)
    can_delete = True
    can_create = True
    can_edit = True
    can_export = True
    form_columns = ['chat', 'is_user', 'content']
    form_args = {
        'chat': {'label': 'Чат', 'description': 'Связанный чат'},
        'is_user': {'label': 'От пользователя', 'description': 'Сообщение от пользователя или системы'},
        'content': {'label': 'Содержание', 'validators': [DataRequired()], 'description': 'Текст сообщения'}
    }
    column_filters = ['id', 'is_user']
    column_formatters = {
        'is_user': lambda v, c, m, p: '👤 Да' if m.is_user else '🤖 Нет',
        'created_at': lambda v, c, m, p: m.created_at.strftime('%d.%m.%Y %H:%M') if m.created_at else ''
    }