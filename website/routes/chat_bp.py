from datetime import datetime, timedelta
from flask import Flask, current_app, render_template, request, jsonify, session, Blueprint

from flask_login import login_required

from werkzeug.utils import secure_filename

import os
import uuid

from ..models import TimeByMinsk, Chat, ChatMessage, ChatAttachment, User
from .. import db

from functools import wraps

chat_bp = Blueprint('chat_bp', __name__, url_prefix='/api/chat')

@chat_bp.route('/<int:chat_id>/end', methods=['POST'])
@login_required
def end_chat(chat_id):
    try:
        chat = Chat.query.get_or_404(chat_id)
        
        if chat.created_by_id != session.get('user_id'):
            return jsonify({'error': 'Access denied'}), 403
        
        db.session.delete(chat)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in end_chat: {str(e)}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/send-message', methods=['POST'])
@login_required
def send_message():
    try:
        data = request.get_json()
        
        chat_id = data.get('chat_id')
        sender_id = data.get('sender_id')
        content = data.get('content', '').strip()
        reply_to_id = data.get('reply_to_id')
        chat_type = data.get('chat_type', 'support')
        
        if not sender_id or not content:
            return jsonify({'error': 'Missing required fields'}), 400
        
        if not chat_id:
            chat = Chat(
                title=f"Чат {chat_type}",
                created_by_id=sender_id,
                created_at=TimeByMinsk(),
                updated_at=TimeByMinsk()
            )
            db.session.add(chat)
            db.session.flush()
            chat_id = chat.id
            is_new_chat = True
        else:
            is_new_chat = False
        
        chat = Chat.query.get(chat_id)
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
        
        message = ChatMessage(
            chat_id=chat_id,
            sender_id=sender_id,
            content=content,
            reply_to_id=reply_to_id,
            created_at=TimeByMinsk(),
            updated_at=TimeByMinsk()
        )
        db.session.add(message)
        
        chat.updated_at = TimeByMinsk()
        db.session.commit()
        
        sender = User.query.get(sender_id)
        
        return jsonify({
            'id': message.id,
            'chat_id': message.chat_id,
            'sender_id': message.sender_id,
            'content': message.content,
            'created_at': message.created_at.isoformat() if message.created_at else None,
            'reply_to_id': message.reply_to_id,
            'is_new_chat': is_new_chat
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in send_message: {str(e)}")
        return jsonify({'error': str(e)}), 500