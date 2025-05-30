// static/script.js
class ExamBotApp {
    constructor() {
        this.currentUser = null;
        this.currentSession = null;
        this.sessions = [];
        this.init();
    }

    init() {
        this.bindEvents();
        this.checkUserSession();
    }

    bindEvents() {
        // Modal events
        document.getElementById('submitName').addEventListener('click', () => this.handleNameSubmit());
        document.getElementById('nameInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleNameSubmit();
        });

        // Chat events
        document.getElementById('sendButton').addEventListener('click', () => this.sendMessage());
        document.getElementById('messageInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Character count
        document.getElementById('messageInput').addEventListener('input', () => this.updateCharCount());

        // Sidebar events
        document.getElementById('newChatBtn').addEventListener('click', () => this.createNewSession());
        document.getElementById('sidebarToggle').addEventListener('click', () => this.toggleSidebar());

        // Click outside sidebar to close on mobile
        document.addEventListener('click', (e) => {
            const sidebar = document.getElementById('sidebar');
            const toggle = document.getElementById('sidebarToggle');
            if (window.innerWidth <= 768 && sidebar.classList.contains('open')) {
                if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
                    sidebar.classList.remove('open');
                }
            }
        });
    }

    checkUserSession() {
        const savedUser = localStorage.getItem('exambot_user');
        if (savedUser) {
            this.currentUser = JSON.parse(savedUser);
            this.hideNameModal();
            this.loadUserData();
        } else {
            this.showNameModal();
        }
    }

    showNameModal() {
        document.getElementById('nameModal').style.display = 'flex';
        document.getElementById('nameInput').focus();
    }

    hideNameModal() {
        document.getElementById('nameModal').style.display = 'none';
        document.getElementById('userName').textContent = this.currentUser.name;
    }

    async handleNameSubmit() {
        const name = document.getElementById('nameInput').value.trim();
        if (!name) {
            this.showError('Please enter your name');
            return;
        }

        try {
            const response = await fetch('/api/users', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name: name })
            });

            if (response.ok) {
                this.currentUser = await response.json();
                localStorage.setItem('exambot_user', JSON.stringify(this.currentUser));
                this.hideNameModal();
                this.loadUserData();
            } else {
                throw new Error('Failed to create user');
            }
        } catch (error) {
            this.showError('Failed to create user. Please try again.');
            console.error('Error creating user:', error);
        }
    }

    async loadUserData() {
        await this.loadSessions();
        if (this.sessions.length === 0) {
            await this.createNewSession();
        } else {
            await this.loadSession(this.sessions[0]._id);
        }
    }

    async loadSessions() {
        try {
            const response = await fetch(`/api/users/${this.currentUser.user_id}/sessions`);
            if (response.ok) {
                const data = await response.json();
                this.sessions = data.sessions;
                this.renderSessions();
            }
        } catch (error) {
            console.error('Error loading sessions:', error);
        }
    }

    renderSessions() {
        const sessionsList = document.getElementById('sessionsList');
        sessionsList.innerHTML = '';

        this.sessions.forEach(session => {
            const sessionElement = this.createSessionElement(session);
            sessionsList.appendChild(sessionElement);
        });
    }

    createSessionElement(session) {
        const div = document.createElement('div');
        div.className = `session-item ${session._id === this.currentSession ? 'active' : ''}`;
        
        const createdDate = new Date(session.created_at).toLocaleDateString();
        
        div.innerHTML = `
            <div class="session-content">
                <div class="session-name">${session.session_name}</div>
                <div class="session-date">${createdDate}</div>
            </div>
            <div class="session-actions">
                <button onclick="app.editSessionName('${session._id}')" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
                <button onclick="app.deleteSession('${session._id}')" title="Delete">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;

        div.addEventListener('click', (e) => {
            if (!e.target.closest('.session-actions')) {
                this.loadSession(session._id);
            }
        });

        return div;
    }

    async createNewSession() {
        try {
            const response = await fetch(`/api/users/${this.currentUser.user_id}/sessions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({})
            });

            if (response.ok) {
                const data = await response.json();
                await this.loadSessions();
                await this.loadSession(data.session_id);
            }
        } catch (error) {
            this.showError('Failed to create new session');
            console.error('Error creating session:', error);
        }
    }

    async loadSession(sessionId) {
        try {
            this.currentSession = sessionId;
            this.updateActiveSession();
            
            const response = await fetch(`/api/sessions/${sessionId}`);
            if (response.ok) {
                const data = await response.json();
                this.renderChatHistory(data.context);
            }
        } catch (error) {
            this.showError('Failed to load session');
            console.error('Error loading session:', error);
        }
    }

    updateActiveSession() {
        document.querySelectorAll('.session-item').forEach(item => {
            item.classList.remove('active');
        });
        
        const activeSession = document.querySelector(`.session-item[data-session-id="${this.currentSession}"]`);
        if (activeSession) {
            activeSession.classList.add('active');
        }
    }

    renderChatHistory(context) {
        const chatMessages = document.getElementById('chatMessages');
        
        // Clear existing messages except welcome message
        const welcomeMessage = chatMessages.querySelector('.welcome-message');
        chatMessages.innerHTML = '';
        if (context.length === 0) {
            chatMessages.appendChild(welcomeMessage);
        }

        context.forEach(entry => {
            if (entry.user_query) {
                this.addMessage(entry.user_query, 'user');
            }
            if (entry.agent_response) {
                this.addMessage(entry.agent_response, 'bot');
            }
        });

        this.scrollToBottom();
    }

    async sendMessage() {
        const input = document.getElementById('messageInput');
        const message = input.value.trim();
        
        if (!message || !this.currentSession) return;

        // Add user message to UI
        this.addMessage(message, 'user');
        input.value = '';
        this.updateCharCount();

        // Show typing indicator
        this.showTypingIndicator();

        try {
            const response = await fetch(`/api/sessions/${this.currentSession}/messages`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });

            if (response.ok) {
                const data = await response.json();
                this.hideTypingIndicator();
                this.addMessage(data.response, 'bot');
            } else {
                throw new Error('Failed to send message');
            }
        } catch (error) {
            this.hideTypingIndicator();
            this.showError('Failed to send message. Please try again.');
            console.error('Error sending message:', error);
        }
    }

    addMessage(content, type) {
        const chatMessages = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;

        if (type === 'bot') {
            messageDiv.innerHTML = `
                <div class="bot-avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="message-content">${this.formatMessage(content)}</div>
            `;
        } else {
            messageDiv.innerHTML = `
                <div class="message-content">${this.escapeHtml(content)}</div>
            `;
        }

        chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    formatMessage(content) {
        // Basic formatting for bot messages
        content = this.escapeHtml(content);
        
        // Convert **bold** to <strong>
        content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Convert *italic* to <em>
        content = content.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // Convert line breaks
        content = content.replace(/\n/g, '<br>');
        
        // Convert code blocks
        content = content.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
        
        // Convert inline code
        content = content.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        return content;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showTypingIndicator() {
        const chatMessages = document.getElementById('chatMessages');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.id = 'typingIndicator';
        typingDiv.innerHTML = `
            <div class="bot-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        chatMessages.appendChild(typingDiv);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    scrollToBottom() {
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    updateCharCount() {
        const input = document.getElementById('messageInput');
        const charCount = document.getElementById('charCount');
        charCount.textContent = `${input.value.length}/1000`;
    }

    toggleSidebar() {
        document.getElementById('sidebar').classList.toggle('open');
    }

    async editSessionName(sessionId) {
        const currentSession = this.sessions.find(s => s._id === sessionId);
        const newName = prompt('Enter new session name:', currentSession.session_name);
        
        if (newName && newName.trim() !== currentSession.session_name) {
            try {
                const response = await fetch(`/api/sessions/${sessionId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ name: newName.trim() })
                });

                if (response.ok) {
                    await this.loadSessions();
                } else {
                    throw new Error('Failed to update session name');
                }
            } catch (error) {
                this.showError('Failed to update session name');
                console.error('Error updating session:', error);
            }
        }
    }

    async deleteSession(sessionId) {
        if (confirm('Are you sure you want to delete this chat session?')) {
            try {
                const response = await fetch(`/api/sessions/${sessionId}`, {
                    method: 'DELETE'
                });

                if (response.ok) {
                    await this.loadSessions();
                    if (this.currentSession === sessionId) {
                        if (this.sessions.length > 0) {
                            await this.loadSession(this.sessions[0]._id);
                        } else {
                            await this.createNewSession();
                        }
                    }
                } else {
                    throw new Error('Failed to delete session');
                }
            } catch (error) {
                this.showError('Failed to delete session');
                console.error('Error deleting session:', error);
            }
        }
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.appendChild(errorDiv);
        
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
        
        this.scrollToBottom();
    }

    showSuccess(message) {
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message';
        successDiv.textContent = message;
        
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.appendChild(successDiv);
        
        setTimeout(() => {
            successDiv.remove();
        }, 3000);
        
        this.scrollToBottom();
    }
}

const app = new ExamBotApp();