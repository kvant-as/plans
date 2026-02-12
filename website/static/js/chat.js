const ChatModule = (function() {
    let _state = {
        currentChatId: null,
        currentChatType: null,
        currentUserId: 1,
        messageCheckInterval: null,
        selectedTypeText: null,
        lastMessageCount: 0
    };

    function _showPage(pageId) {
        document.querySelectorAll('.chat-page').forEach(page => {
            page.classList.remove('active');
        });
        
        const page = document.getElementById(pageId);
        if (page) page.classList.add('active');
        
        const chatInputArea = document.getElementById('chatInputArea');
        if (pageId === 'pageActiveChat') {
            chatInputArea.style.display = 'flex';
            document.getElementById('messageInput').focus();
            // _addEndChatButton();
        } else {
            chatInputArea.style.display = 'none';
            _removeEndChatButton();
        }
    }

    async function _checkExistingChatAndOpen() {
        try {
            const response = await fetch('/api/chat/check-existing-chat');
            const data = await response.json();
            
            if (data.has_active_chat) {
                _state.currentChatId = data.chat_id;
                _state.currentChatType = data.chat_type;
                await _loadMessages();
                _showPage('pageActiveChat');
                _startMessageCheck();
                _scrollToBottom();
            } else {
                _showPage('pageChatType');
            }
        } catch (error) {
            console.error('Error checking existing chat:', error);
            _showPage('pageChatType');
        }
    }

    async function _handleChatTypeSelection(type) {
        _state.currentChatType = type;
        
        const typeTexts = {
            'no-org': 'Нет организации',
            'compl-plan': 'Заполнение плана',
            'dif': 'Другое'
        };

        _state.selectedTypeText = typeTexts[type];
        
        const welcomeMessage = document.querySelector('#pageActiveChat .welcome-message .message-text');
        if (welcomeMessage) {
            welcomeMessage.innerHTML = `Добрый день! <br>Вы выбрали <strong>${_state.selectedTypeText}</strong>, какой вопрос у вас возник? <br> 
            <br>Для смены темы нажмите <strong>Назад к выбору тем</strong>, для продолжения напишите ваш вопрос
                                    `
            
            ;
        }
        
        _showPage('pageActiveChat');
        _addBackButton();
    }

    async function _sendMessage() {
        const input = document.getElementById('messageInput');
        const content = input.value.trim();
        
        if (!content) return;
        
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

        try {
            const response = await fetch('/api/chat/send-message', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    ...(csrfToken && { 'X-CSRFToken': csrfToken })
                },
                body: JSON.stringify({
                    content: content,
                    sender_id: _state.currentUserId
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                
                if (data.success) {
                    _state.currentChatId = data.chat_id;
                    await _loadMessages();
                    input.value = '';
                }
            }
        } catch (error) {
            console.error('Error sending message:', error);
            alert('Ошибка при отправке сообщения');
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

    async function _endChat() {
        if (!_state.currentChatId) return;
            
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

        try {
            const response = await fetch(`/api/chat/${_state.currentChatId}/end`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    ...(csrfToken && { 'X-CSRFToken': csrfToken })
                }
            });
            
            if (response.ok) {
                const messagesList = document.getElementById('messagesList');
                const endedMessagesList = document.getElementById('endedMessagesList');
                endedMessagesList.innerHTML = messagesList.innerHTML;

                const endMessage = {
                    id: Date.now(),
                    content: '✅ Чат завершен. Спасибо за обращение!',
                    sender_id: _state.currentUserId, 
                    created_at: new Date().toISOString()
                };
                _addMessageToUI(endMessage, false, 'endedMessagesList');
                
                _showPage('pageChatEnded');
                _stopMessageCheck();
                
                _state.currentChatId = null;
                _state.currentChatType = null;
            }
        } catch (error) {
            console.error('Error ending chat:', error);
        }
    }

    function _startMessageCheck() {
        _stopMessageCheck();
        _state.messageCheckInterval = setInterval(_checkNewMessages, 10000);
    }

    function _stopMessageCheck() {
        if (_state.messageCheckInterval) {
            clearInterval(_state.messageCheckInterval);
            _state.messageCheckInterval = null;
        }
    }

    async function _checkNewMessages() {
        if (!_state.currentChatId) return;
        
        try {
            const response = await fetch(`/api/chat/${_state.currentChatId}/messages`);
            const messages = await response.json();
            
            if (messages.length > _state.lastMessageCount) {
                const newMessages = messages.slice(_state.lastMessageCount);
                
                newMessages.forEach(msg => {
                    const existingMsg = document.querySelector(`[data-message-id="${msg.id}"]`);
                    if (!existingMsg) {
                        _addMessageToUI(msg, msg.sender_id === _state.currentUserId);
                    }
                });
                
                _state.lastMessageCount = messages.length;
                _scrollToBottom();
            }
        } catch (error) {
            console.error('Error checking new messages:', error);
        }
    }

    function _addMessageToUI(message, isSent, containerId = 'messagesList') {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isSent ? 'user' : 'bot'}`;
        messageDiv.dataset.messageId = message.id;
        
        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.textContent = isSent ? '👤' : '👩‍💻';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        textDiv.textContent = message.content;
        contentDiv.appendChild(textDiv);
        
        if (message.created_at) {
            const timeDiv = document.createElement('div');
            timeDiv.className = 'message-time';
            const date = new Date(message.created_at);
            timeDiv.textContent = date.toLocaleTimeString('ru-RU', {
                hour: '2-digit',
                minute: '2-digit'
            });
            contentDiv.appendChild(timeDiv);
        }
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);
        container.appendChild(messageDiv);
        
        if (containerId === 'messagesList') {
            _scrollToBottom();
        }
    }

    function _addBackButton() {
        const existingBtn = document.querySelector('.back-to-type-btn');
        if (existingBtn) existingBtn.remove();
        
        const chatPage = document.getElementById('pageActiveChat');
        if (!chatPage) return;
        
        const backBtn = document.createElement('button');
        backBtn.className = 'back-to-type-btn';
        backBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M19 12H5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                <path d="M12 19L5 12L12 5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <span>Назад к выбору темы</span>
        `;
        backBtn.onclick = function() {
            _showPage('pageChatType');
            this.remove();
        };
        chatPage.appendChild(backBtn);
    }

    function _addEndChatButton() {
        const existingBtn = document.querySelector('.chat-btn-back');
        if (existingBtn) existingBtn.remove();
        
        const chatPage = document.getElementById('pageActiveChat');
        if (!chatPage) return;
        
        const endChatBtn = document.createElement('button');
        endChatBtn.className = 'chat-btn-back';
        endChatBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                <path d="M6 6L18 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <span>Завершить чат</span>
        `;
        endChatBtn.onclick = _endChat;
        chatPage.appendChild(endChatBtn);
    }

    function _removeEndChatButton() {
        const endChatBtn = document.querySelector('.chat-btn-back');
        if (endChatBtn) endChatBtn.remove();
    }

    function _resetChat() {
        _stopMessageCheck();
        
        _state.currentChatId = null;
        _state.currentChatType = null;
        _state.selectedTypeText = null;
        _state.lastMessageCount = 0;
        
        const messagesList = document.getElementById('messagesList');
        if (messagesList) messagesList.innerHTML = '';
        
        const endedMessagesList = document.getElementById('endedMessagesList');
        if (endedMessagesList) endedMessagesList.innerHTML = '';
        
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.disabled = false;
            messageInput.value = '';
        }
        
        _removeEndChatButton();
    }

    function _scrollToBottom() {
        const messagesContainer = document.getElementById('chatMessages');
        setTimeout(() => {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }, 50);
    }

    return {
        init: async function(userId) {
            if (userId) _state.currentUserId = userId;
        },

        toggleChat: function() {
            const container = document.getElementById('chatContainer');
            container.classList.toggle('active');
            
            if (container.classList.contains('active')) {
                const toggleBtn = document.querySelector('.chat-toggle');
                if (toggleBtn) toggleBtn.style.display = 'none';
                _resetChat();
                _checkExistingChatAndOpen();
            } else {
                const toggleBtn = document.querySelector('.chat-toggle');
                if (toggleBtn) toggleBtn.style.display = 'flex';
            }
        },

        selectChatType: _handleChatTypeSelection,
        sendMessage: _sendMessage,
        endChat: _endChat,

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