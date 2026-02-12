from flask import current_app, request, jsonify, Blueprint
from flask_login import current_user, login_required

from ..models import TimeByMinsk, Chat, ChatMessage
from .. import db

chat_bp = Blueprint('chat_bp', __name__, url_prefix='/api/chat')

@chat_bp.route('/<int:chat_id>/end', methods=['POST'])
@login_required
def end_chat(chat_id):
    try:
        chat = Chat.query.get_or_404(chat_id)
        
        if chat.created_by_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403

        db.session.delete(chat)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in end_chat: {str(e)}")
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/<int:chat_id>/messages', methods=['GET'])
@login_required
def get_messages(chat_id):
    try:
        messages = ChatMessage.query.filter_by(chat_id=chat_id).order_by(ChatMessage.created_at.asc()).all()
        
        messages_data = [{
            'id': msg.id,
            'chat_id': msg.chat_id,
            'content': msg.content,
            'created_at': msg.created_at.isoformat() if msg.created_at else None
        } for msg in messages]
        
        return jsonify(messages_data)
        
    except Exception as e:
        print(f"Error in get_messages: {str(e)}")
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/send-message', methods=['POST'])
@login_required
def send_message():
    try:
        data = request.get_json()
        
        sender_id = data.get('sender_id')
        content = data.get('content').strip()
        
        if not sender_id or not content:
            current_app.logger.info(f"Send message failed: missing fields - sender_id: {sender_id}, content: {content}")
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400
        
        chat = Chat.query.filter_by(created_by_id=sender_id).order_by(Chat.created_at.desc()).first()
        
        if not chat:
            chat = Chat(
                title=f"Чат поддержки",
                created_by_id=sender_id,
                created_at=TimeByMinsk(),
                updated_at=TimeByMinsk()
            )
            db.session.add(chat)
            db.session.flush()
            current_app.logger.info(f"Created new chat {chat.id} for user {sender_id}")
        
        message = ChatMessage(
            chat_id=chat.id,
            sender_id=sender_id,
            content=content,
            created_at=TimeByMinsk(),
            updated_at=TimeByMinsk()
        )
        db.session.add(message)
        
        message_answ = ChatMessage(
            chat_id=chat.id,
            sender_id=None,
            content="Да красава",
            created_at=TimeByMinsk(),
            updated_at=TimeByMinsk()
        )
        db.session.add(message_answ)
        
        chat.updated_at = TimeByMinsk()
        db.session.commit()
        
        current_app.logger.info(f"Message {message.id} sent to chat {chat.id} by user {sender_id}")
        
        return jsonify({
            'success': True,
            'chat_id': chat.id,
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in send_message: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500   
    
@chat_bp.route('/check-existing-chat', methods=['GET'])
@login_required
def check_existing_chat():
    try:
        chat = Chat.query.filter_by(created_by_id=current_user.id).order_by(Chat.created_at.desc()).first()
        
        if chat:
            return jsonify({
                'has_active_chat': True,
                'chat_id': chat.id,
                'chat_type': None
            })
        else:
            return jsonify({
                'has_active_chat': False
            })
            
    except Exception as e:
        current_app.logger.error(f"Error in check_existing_chat: {str(e)}")
        return jsonify({'error': str(e)}), 500