from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import random
import smtplib
import string
from flask import current_app, flash, redirect, request, session, url_for
from sqlalchemy import func
from website import db
from website.models import User
import base64

from flask import (
    Blueprint, jsonify, render_template, request, flash, redirect, session,
    url_for, send_file, Response, make_response
)

import re

from flask_login import (
    login_user, logout_user, current_user,
    login_required, LoginManager
)

from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

def mes_on_email(message_body, recipient_email, email_type):
    sender = os.getenv('EMAILNAME')
    password = os.getenv('EMAILPASS')

    if email_type == "code":
        content = f"""
        <div style='padding:20px 40px; color:#000000; font-size:15px;'>
            <p style='margin:0 0 10px 0; color:#000000;'>Здравствуйте!</p>
            <p style='margin:0 0 10px 0; color:#000000;'>Кто-то пытается войти в <b>ErespondentS</b> используя вашу электронную почту.</p>
            <p style='margin:0 0 10px 0; color:#000000;'>Ваш код активации:</p>
            <div style='text-align:center; font-size:32px; font-weight:bold; padding:15px; margin:20px 0; color:#000000;'>{message_body}</div>
        </div>
        """
    elif email_type == "pass":
        content = f"""
        <div style='padding:20px 40px; color:#000000; font-size:15px;'>
            <p style='margin:0 0 10px 0; color:#000000;'>Здравствуйте!</p>
            <p style='margin:0 0 10px 0; color:#000000;'>Вы запросили новый пароль для входа в <b>ErespondentS</b>.</p>
            <p style='margin:0 0 10px 0; color:#000000;'>Ваш новый пароль:</p>
            <div style='text-align:center; font-size:32px; font-weight:bold; padding:15px; margin:20px 0; color:#000000;'>{message_body}</div>
        </div>
        """
    elif email_type == "plan":
        content = f"""
        <div style='padding:20px 40px; color:#000000; font-size:15px;'>
            <p style='margin:0 0 10px 0; color:#000000;'>Здравствуйте!</p>
            <p style='margin:0 0 10px 0; color:#000000;'>Статус вашего отчета изменен на:</p>
            <div style='text-align:center; font-size:20px; font-weight:600; padding:10px; margin:15px 0; color:#000000; border:1px solid #000; border-radius:5px; display:inline-block;'>{message_body}</div>
        </div>
        """
    elif email_type == "reset_link":
        content = f"""
        <div style='padding:20px 40px; color:#000000; font-size:15px;'>
            <p style='margin:0 0 10px 0; color:#000000;'>Здравствуйте!</p>
            <p style='margin:0 0 10px 0; color:#000000;'>Вы запросили сброс пароля для вашей учетной записи в <b>ErespondentS</b>.</p>
            <p style='margin:0 0 15px 0; color:#000000;'>Для сброса пароля перейдите по ссылке ниже:</p>
            <div style='text-align:center; margin:25px 0;'>
                <a href='{message_body}' style='background-color:#4CAF50; color:white; padding:12px 30px; text-decoration:none; border-radius:5px; font-size:16px; font-weight:bold; display:inline-block;'>
                    Сбросить пароль
                </a>
            </div>
            <p style='margin:15px 0 5px 0; color:#666; font-size:13px;'>Ссылка действительна в течение 1 часа.</p>
            <p style='margin:5px 0 0 0; color:#666; font-size:13px;'>Если вы не запрашивали сброс пароля, проигнорируйте это письмо.</p>
        </div>
        """
    else:
        content = f"<div style='padding:20px 40px; color:#000000; font-size:15px;'>{message_body}</div>"

    html_template = f"""
    <!DOCTYPE html>
    <html lang="ru">
      <body style="font-family:'Montserrat',Arial,sans-serif; background-color:#eeeeee; margin:0; padding:20px;">
        <div style="max-width:600px; margin:0 auto; background-color:#ffffff; border-radius:8px; overflow:hidden; box-shadow:0 0 6px rgba(0,0,0,0.1);">
          <div style="text-align:center; font-size:17px; font-weight:500; padding:20px 50px; color:#000000;">
            Ваша учетная запись ErespondentS
          </div>
          {content}
          <div style="padding:10px; background-color:#eeeeee;  text-align:center; font-size:12px; color:#555555;">
            <p style="margin:5px 0;">Дополнительную информацию можно найти <a href="#" style="color:#6441a5; text-decoration:none;">здесь</a>.</p>
            <p style="margin:5px 0;">Спасибо,<br>ErespondentS</p>
          </div>
        </div>
      </body>
    </html>
    """

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()

    try:
        server.login(sender, password)
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = recipient_email
        # Обновляем тему письма в зависимости от типа
        if email_type == "reset_link":
            msg["Subject"] = "Сброс пароля - ErespondentS"
        else:
            msg["Subject"] = "Оповещение"
        
        msg.attach(MIMEText(html_template, "html"))
        server.sendmail(sender, recipient_email, msg.as_string())
        return "Email sent successfully"
    except Exception as _ex:
        return f"{_ex}\nCheck log ..."
    finally:
        server.quit()

def gener_password():
    length=5
    characters = string.digits
    password = ''.join(random.choice(characters) for _ in range(length))
    return password

def send_activation_email(email):
    activation_code = gener_password()
    session['activation_code'] = activation_code
    mes_on_email(activation_code, email, 'code')

def sign_def(email, password1, password2):
    if email and password1:
        if User.query.filter(func.lower(User.email) == func.lower(email)).first():
            flash('Пользователь с таким email уже существует.', 'error')
            return redirect(url_for('auth.sign'))
        elif not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
            flash('Некорректный адрес электронной почты.', 'error')
            return redirect(url_for('auth.sign'))
        elif password1 != password2:
            flash('Ошибка в подтверждении пароля.', 'error')
            return redirect(url_for('auth.sign'))
        else:
            session['temp_user'] = {
                'email': email,
                'password': generate_password_hash(password1)
            }
            session.permanent = True
            send_activation_email(email) 
            flash('Проверьте свою почту для активации аккаунта.', 'success')
            return redirect(url_for('auth.code'))
    else:
        flash('Введите данные для регистрации.', 'error')
        return redirect(url_for('auth.sign'))

def activate_account():
    input_code = ''.join([
            request.form.get(f'activation_code_{i}', '') for i in range(5)
        ])
    if input_code == session.get('activation_code'):
        new_user = User(
            email=session['temp_user']['email'],
            password=session['temp_user']['password']
        )
        db.session.add(new_user)
        db.session.commit()
        session.pop('temp_user', None)
        session.pop('activation_code', None)

        login_user(new_user)
        flash('Почта подтверждена, заполните необходимые данные для продолжения!', 'success')
        return redirect(url_for('auth.param'))        
    else:
        flash('Некорректный код активации.', 'error')
        return redirect(url_for('auth.code')) 
         
def add_param(first_name, last_name, patronymic_name, phone, organization_id=None, ministry_id=None, region_id=None, post=None):
    required_fields = {
        'first_name': first_name,
        'last_name': last_name,
        'phone': phone
    }
    
    for field_name, value in required_fields.items():
        if not value or not str(value).strip():
            flash(f'Поле "{field_name}" обязательно для заполнения!', 'error')
            return redirect(url_for('auth.param'))
    
    if not phone or len(phone.strip()) < 5:
        flash('Номер телефона должен содержать не менее 5 символов!', 'error')
        return redirect(url_for('views.profile'))
    
    def parse_id(id_value):
        if not id_value or not str(id_value).strip():
            return None
        try:
            return int(id_value)
        except (ValueError, TypeError):
            return None
    
    org_id = parse_id(organization_id)
    min_id = parse_id(ministry_id)
    reg_id = parse_id(region_id)
    
    filled_ids = [id for id in [org_id, min_id, reg_id] if id is not None]
    
    if len(filled_ids) > 1:
        flash('Можно выбрать только одну принадлежность: организацию, министерство или регион!', 'error')
        return redirect(url_for('auth.param'))
    
    if len(filled_ids) == 0:
        flash('Необходимо выбрать принадлежность: организацию, министерство или регион!', 'error')
        return redirect(url_for('auth.param'))
    
    normalized_phone = phone.strip()
    # if normalized_phone.startswith('+'):
    #     plus = '+'
    #     digits = ''.join(filter(str.isdigit, normalized_phone[1:]))
    #     normalized_phone = plus + digits
    # else:
    #     normalized_phone = ''.join(filter(str.isdigit, normalized_phone))
    
    existing_user = User.query.filter_by(phone=normalized_phone).first()
    if existing_user and existing_user.id != current_user.id:
        flash('Пользователь с таким номером телефона уже зарегистрирован!', 'error')
        return redirect(url_for('auth.param'))
    
    current_user.first_name = first_name.strip()
    current_user.last_name = last_name.strip()
    current_user.patronymic_name = patronymic_name.strip() if patronymic_name else None
    current_user.phone = normalized_phone
    current_user.post = post.strip() if post else ''
    
    current_user.organization_id = org_id
    current_user.ministry_id = min_id
    current_user.region_id = reg_id

    if min_id:
        current_user.plan_type = 'ministry'
    elif reg_id:
        current_user.plan_type = 'region'

    try:
        db.session.commit()
        flash('Данные успешно сохранены!', 'success')
        return redirect(url_for('views.profile'))
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при сохранении данных: {str(e)}', 'error')
        return redirect(url_for('auth.param'))