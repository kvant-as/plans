const ChatModule = (function() {
    let _state = {
        currentChatId: null,
        currentChatType: null,
        currentUserId: 1,
        messageCheckInterval: null
    };

    async function _loadOrCreateChat(chatType) {
        try {
            const response = await fetch('/api/chat/load-or-create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: chatType,
                    user_id: _state.currentUserId
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                _state.currentChatId = data.chat_id;
                await _loadMessages();
                _startMessageCheck();
            }
        } catch (error) {
            console.error('Error:', error);
            _addSystemMessage('Ошибка подключения к чату');
        }
    }

    async function _loadMessages() {
        if (!_state.currentChatId) return;
        
        try {
            const response = await fetch(`/api/chat/${_state.currentChatId}/messages`);
            const messages = await response.json();
            
            const messagesList = document.getElementById('messagesList');
            messagesList.innerHTML = '';
            
            messages.forEach(msg => {
                _addMessageToUI(msg, msg.sender_id === _state.currentUserId);
            });
            
            _scrollToBottom();
        } catch (error) {
            console.error('Error loading messages:', error);
        }
    }

    async function _sendMessage() {
        const input = document.getElementById('messageInput');
        const content = input.value.trim();
        
        if (!content) return;
        
        const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

        try {
            const response = await fetch('/api/chat/send-message', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    ...(_state.currentChatId && { chat_id: _state.currentChatId }),
                    content: content,
                    sender_id: _state.currentUserId,
                    chat_type: _state.currentChatType
                })
            });
            
            if (response.ok) {
                const message = await response.json();
                
                if (message.is_new_chat) {
                    _state.currentChatId = message.chat_id;
                    _startMessageCheck();
                    
                    // Разные приветствия для разных типов чата
                    const welcomeMessages = {
                        'technical': 'Здравствуйте! Опишите вашу проблему с организацией.',
                        'sales': 'Здравствуйте! Что вас интересует?',
                        'default': 'Здравствуйте! Чем могу помочь?'
                    };
                    
                    const welcomeText = welcomeMessages[_state.currentChatType] || welcomeMessages.default;
                    
                    const welcomeMessage = {
                        id: Date.now(),
                        content: welcomeText,
                        sender_id: 1,
                        created_at: new Date().toISOString()
                    };
                    _addMessageToUI(welcomeMessage, false);
                    
                    // Добавляем небольшую паузу перед сообщением пользователя
                    await new Promise(resolve => setTimeout(resolve, 300));
                    _addMessageToUI(message, true);
                } else {
                    _addMessageToUI(message, true);
                }
                
                input.value = '';
                _scrollToBottom();
                _addEndChatButton();
            }
        } catch (error) {
            console.error('Error sending message:', error);
            alert('Ошибка при отправке сообщения');
        }
    }

    async function _endChat() {
        if (!_state.currentChatId) return;
        
        try {
            const response = await fetch(`/api/chat/${_state.currentChatId}/end`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
                // Показываем сообщение о завершении
                const endMessage = {
                    id: Date.now(),
                    content: '✅ Чат завершен. Спасибо за обращение!',
                    sender_id: 1,
                    created_at: new Date().toISOString()
                };
                _addMessageToUI(endMessage, false);
                
                // Блокируем поле ввода
                document.getElementById('messageInput').disabled = true;
                document.querySelector('.send-btn').disabled = true;
                
                // Добавляем кнопку "Новый чат"
                _addNewChatButton();
                
                _stopMessageCheck();
            }
        } catch (error) {
            console.error('Error ending chat:', error);
        }
    }

    function _addEndChatButton() {
        if (document.querySelector('.end-chat-btn')) return;
        
        const chatInputArea = document.querySelector('.chat-input-area');
        const endChatBtn = document.createElement('button');
        endChatBtn.className = 'end-chat-btn';
        endChatBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                <path d="M6 6L18 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            Завершить чат
        `;
        endChatBtn.onclick = _endChat;
        chatInputArea.appendChild(endChatBtn);
    }

    function _addNewChatButton() {
        const chatInputArea = document.querySelector('.chat-input-area');
        chatInputArea.style.display = 'none';
        
        const newChatBtn = document.createElement('button');
        newChatBtn.className = 'new-chat-btn';
        newChatBtn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 5V19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                <path d="M5 12H19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            Новое обращение
        `;
        newChatBtn.onclick = () => {
            _resetChat();
            _removeBackButton();
            document.querySelector('.chat-toggle').style.display = 'flex';
            document.getElementById('chatContainer').classList.remove('active');
        };
        
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.appendChild(newChatBtn);
    }

    async function _checkNewMessages() {
        if (!_state.currentChatId) return;
        
        try {
            const response = await fetch(`/api/chat/${_state.currentChatId}/new-messages`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ last_message_id: 0 })
            });
            
            const messages = await response.json();
            
            messages.forEach(msg => {
                if (msg.sender_id !== _state.currentUserId) {
                    _addMessageToUI(msg, false);
                }
            });
            
            if (messages.length > 0) {
                _scrollToBottom();
            }
        } catch (error) {
            console.error('Error checking messages:', error);
        }
    }

    function _addMessageToUI(message, isSent) {
        const messagesList = document.getElementById('messagesList');
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isSent ? 'user' : 'bot'}`;
        messageDiv.dataset.messageId = message.id;
        
        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.textContent = isSent ? '👤' : '👩‍💻';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const textDiv = document.createElement('div');
        textDiv.textContent = message.content;
        contentDiv.appendChild(textDiv);
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        const date = new Date(message.created_at);
        timeDiv.textContent = date.toLocaleTimeString('ru-RU', {
            hour: '2-digit',
            minute: '2-digit'
        });
        contentDiv.appendChild(timeDiv);
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);
        messagesList.appendChild(messageDiv);
    }

    function _addSystemMessage(text) {
        const messagesList = document.getElementById('messagesList');
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot';
        
        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.textContent = '👩‍💻';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = text;
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);
        messagesList.appendChild(messageDiv);
    }

    function _scrollToBottom() {
        const messagesContainer = document.getElementById('chatMessages');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function _addBackButton() {
        if (document.querySelector('.chat-back-button')) return;
        
        const chatHeader = document.querySelector('.chat-header');
        const backButton = document.createElement('button');
        backButton.className = 'chat-back-button';
        backButton.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M19 12H5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M12 19L5 12L12 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Назад
        `;
        backButton.onclick = (e) => {
            e.stopPropagation();
            _resetChat();
        };
        
        chatHeader.appendChild(backButton);
    }

    function _removeBackButton() {
        const backButton = document.querySelector('.chat-back-button');
        if (backButton) backButton.remove();
    }

    function _removeEndChatButton() {
        const endChatBtn = document.querySelector('.end-chat-btn');
        if (endChatBtn) endChatBtn.remove();
    }

    function _removeNewChatButton() {
        const newChatBtn = document.querySelector('.new-chat-btn');
        if (newChatBtn) newChatBtn.remove();
    }

    function _startMessageCheck() {
        _stopMessageCheck();
        _state.messageCheckInterval = setInterval(_checkNewMessages, 3000);
    }

    function _stopMessageCheck() {
        if (_state.messageCheckInterval) {
            clearInterval(_state.messageCheckInterval);
            _state.messageCheckInterval = null;
        }
    }

    function _resetChat() {
        _stopMessageCheck();
        
        if (_state.currentChatId) {
            // Не удаляем, просто сбрасываем состояние
            _state.currentChatId = null;
        }
        
        _state.currentChatType = null;
        
        const chatTypeSelection = document.getElementById('chatTypeSelection');
        const messagesContainer = document.getElementById('messagesContainer');
        const chatInputArea = document.getElementById('chatInputArea');
        const messagesList = document.getElementById('messagesList');
        const welcomeMessage = document.querySelector('.welcome-message');
        
        if (chatTypeSelection) chatTypeSelection.style.display = 'block';
        if (messagesContainer) messagesContainer.style.display = 'none';
        if (chatInputArea) {
            chatInputArea.style.display = 'none';
            document.getElementById('messageInput').disabled = false;
            document.querySelector('.send-btn').disabled = false;
        }
        if (messagesList) messagesList.innerHTML = '';
        if (welcomeMessage) welcomeMessage.style.display = 'block';
        
        _removeBackButton();
        _removeEndChatButton();
        _removeNewChatButton();
    }

    async function _handleChatTypeSelection(type) {
        _state.currentChatType = type;
        
        const welcomeMessage = document.querySelector('.welcome-message');
        if (welcomeMessage) welcomeMessage.style.display = 'none';
        document.getElementById('chatTypeSelection').style.display = 'none';
        
        document.getElementById('messagesContainer').style.display = 'block';
        document.getElementById('chatInputArea').style.display = 'flex';
        
        _addBackButton();
        
        const typeTexts = {
            'technical': 'Нет организации',
            'sales': 'Другое'
        };
        
        const selectedTypeText = typeTexts[type] || 'Поддержка';
        
        const userChoiceMessage = {
            id: Date.now(),
            content: `Я выбрал: ${selectedTypeText}`,
            sender_id: _state.currentUserId,
            created_at: new Date().toISOString()
        };
        _addMessageToUI(userChoiceMessage, true);
        
        await _loadOrCreateChat(type);
        
        document.getElementById('messageInput').focus();
        _scrollToBottom();
    }

    return {
        init: function(userId) {
            if (userId) _state.currentUserId = userId;
            console.log('Chat module initialized');
        },

        toggleChat: function() {
            const container = document.getElementById('chatContainer');
            container.classList.toggle('active');
            
            if (container.classList.contains('active')) {
                document.querySelector('.chat-toggle').style.display = 'none';
                _resetChat();
            } else {
                document.querySelector('.chat-toggle').style.display = 'flex';
            }
        },

        selectChatType: _handleChatTypeSelection,
        resetChat: _resetChat,
        sendMessage: _sendMessage,

        handleKeyDown: function(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                _sendMessage();
            }
        },

        setUserId: function(userId) {
            _state.currentUserId = userId;
        }
    };
})();

window.ChatModule = ChatModule;