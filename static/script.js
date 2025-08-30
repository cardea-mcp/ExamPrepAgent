class ExamBotApp {
    constructor() {
        this.currentUser = null;
        this.currentSession = null;
        this.sessions = [];
        this.audioRecorder = null;
        this.audioPlayer = null;
        this.isRecording = false;
        this.recordedAudioBlob = null;
        this.audioSupported = false;
        this.recordingTimer = null;
        this.ttsEnabled = false;
        this.currentAudio = null;
        this.ttsSupported = false;
        
        // Storage keys
        this.STORAGE_KEYS = {
            USER: 'exambot_user',
            SESSIONS: 'exambot_sessions', 
            CURRENT_SESSION: 'exambot_current_session',
            TTS_ENABLED: 'exambot_tts_enabled',
            SESSION_PREFIX: 'exambot_session_'
        };
        
        this.init();
    }

    async init() {
        this.bindEvents();
        await this.initializeAudio();
        await this.initializeTTS();
        this.initializeUser();
    }

    // ===== LOCAL STORAGE MANAGEMENT =====

    generateUserId() {
        return 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    saveToStorage(key, data) {
        try {
            localStorage.setItem(key, JSON.stringify(data));
            return true;
        } catch (error) {
            console.error('Failed to save to localStorage:', error);
            this.showError('Failed to save data. Your browser storage might be full.');
            return false;
        }
    }

    getFromStorage(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('Failed to read from localStorage:', error);
            return defaultValue;
        }
    }

    // ===== USER MANAGEMENT =====

    initializeUser() {
        let user = this.getFromStorage(this.STORAGE_KEYS.USER);
        
        if (!user) {
            this.showNameModal();
        } else {
            this.currentUser = user;
            this.ttsEnabled = this.getFromStorage(this.STORAGE_KEYS.TTS_ENABLED, false);
            this.hideNameModal();
            this.loadUserData();
        }
    }

    createUser(name) {
        const user = {
            id: this.generateUserId(),
            name: name,
            createdAt: new Date().toISOString()
        };
        
        this.saveToStorage(this.STORAGE_KEYS.USER, user);
        this.currentUser = user;
        return user;
    }

    // ===== SESSION MANAGEMENT =====

    loadUserData() {
        this.loadSessions();
        if (this.sessions.length === 0) {
            this.createNewSession();
        } else {
            // Load the last active session or the most recent one
            const lastSessionId = this.getFromStorage(this.STORAGE_KEYS.CURRENT_SESSION);
            const targetSession = lastSessionId && this.sessions.find(s => s.id === lastSessionId) 
                ? lastSessionId 
                : this.sessions[0].id;
            this.loadSession(targetSession);
        }
        this.updateUserDisplay();
    }

    updateUserDisplay() {
        document.getElementById('userName').textContent = this.currentUser.name;
    }

    loadSessions() {
        this.sessions = this.getFromStorage(this.STORAGE_KEYS.SESSIONS, []);
        // Sort sessions by last updated time (most recent first)
        this.sessions.sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
        this.renderSessions();
    }

    createNewSession(sessionName = null) {
        const now = new Date().toISOString();
        const sessionId = this.generateSessionId();
        
        const session = {
            id: sessionId,
            name: sessionName || `Chat ${new Date().toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}`,
            createdAt: now,
            updatedAt: now,
            messageCount: 0
        };

        this.sessions.unshift(session); // Add to beginning
        this.saveSessions();
        
        // Initialize empty conversation for this session
        this.saveSessionMessages(sessionId, []);
        
        this.loadSession(sessionId);
        this.renderSessions();
    }

    saveSessions() {
        this.saveToStorage(this.STORAGE_KEYS.SESSIONS, this.sessions);
    }

    loadSession(sessionId) {
        this.currentSession = sessionId;
        this.saveToStorage(this.STORAGE_KEYS.CURRENT_SESSION, sessionId);
        
        const messages = this.getSessionMessages(sessionId);
        this.renderChatHistory(messages);
        this.updateActiveSession();
    }

    getSessionMessages(sessionId) {
        return this.getFromStorage(this.STORAGE_KEYS.SESSION_PREFIX + sessionId, []);
    }

    saveSessionMessages(sessionId, messages) {
        this.saveToStorage(this.STORAGE_KEYS.SESSION_PREFIX + sessionId, messages);
        
        // Update session metadata
        const session = this.sessions.find(s => s.id === sessionId);
        if (session) {
            session.updatedAt = new Date().toISOString();
            session.messageCount = messages.length;
            this.saveSessions();
        }
    }

    addMessageToSession(sessionId, type, content, metadata = {}) {
        const messages = this.getSessionMessages(sessionId);
        const message = {
            id: Date.now() + '_' + Math.random().toString(36).substr(2, 9),
            type: type, // 'user' or 'assistant'
            content: content,
            timestamp: new Date().toISOString(),
            ...metadata
        };
        
        messages.push(message);
        this.saveSessionMessages(sessionId, messages);
        return message;
    }

    deleteSession(sessionId) {
        if (confirm('Are you sure you want to delete this chat session?')) {
            // Remove session from list
            this.sessions = this.sessions.filter(s => s.id !== sessionId);
            this.saveSessions();
            
            // Remove session messages
            localStorage.removeItem(this.STORAGE_KEYS.SESSION_PREFIX + sessionId);
            
            // If this was the current session, switch to another
            if (this.currentSession === sessionId) {
                if (this.sessions.length > 0) {
                    this.loadSession(this.sessions[0].id);
                } else {
                    this.createNewSession();
                }
            }
            
            this.renderSessions();
        }
    }

    editSessionName(sessionId) {
        const currentSession = this.sessions.find(s => s.id === sessionId);
        const newName = prompt('Enter new session name:', currentSession.name);
        
        if (newName && newName.trim() !== currentSession.name) {
            this.updateSessionName(sessionId, newName.trim());
        }
    }

    updateSessionName(sessionId, newName) {
        const session = this.sessions.find(s => s.id === sessionId);
        if (session) {
            session.name = newName;
            session.updatedAt = new Date().toISOString();
            this.saveSessions();
            this.renderSessions();
        }
    }

    // ===== MESSAGE PROCESSING =====

    buildConversationContext() {
        if (!this.currentSession) return [];
        
        const messages = this.getSessionMessages(this.currentSession);
        
        // Return last 20 messages to avoid oversized requests
        const recentMessages = messages.slice(-20);
        
        return recentMessages.map(msg => {
            const context = {
                type: msg.type,
                content: msg.content,
                timestamp: msg.timestamp
            };
            
            // Include tool call data if present
            if (msg.type === 'tool_calls') {
                context.tool_calls = msg.tool_calls;
                context.tool_responses = msg.tool_responses;
                context.assistant_content = msg.assistant_content;
            }
            
            return context;
        });
    }

    async sendMessage() {
        const input = document.getElementById('messageInput');
        const message = input.value.trim();
        
        if (!message || !this.currentSession) return;
    
        // Add user message to UI and storage
        this.addMessage(message, 'user');
        this.addMessageToSession(this.currentSession, 'user', message);
        
        input.value = '';
        this.updateCharCount();
        this.showTypingIndicator();
    
        try {
            const context = this.buildConversationContext();
            
            const response = await fetch('/api/chat/message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    message: message,
                    context: context
                })
            });
    
            if (response.ok) {
                const data = await response.json();
                this.hideTypingIndicator();
                
                // Add assistant response to UI and storage
                this.addMessage(data.response, 'bot');
                
                // Store the complete response including tool calls/responses
                const assistantMessage = {
                    content: data.response
                };
    
                // If there were tool calls, store them as a separate entry
                if (data.tool_calls && data.tool_responses) {
                    this.addMessageToSession(this.currentSession, 'tool_calls', '', {
                        tool_calls: data.tool_calls,
                        tool_responses: data.tool_responses,
                        assistant_content: data.assistant_content
                    });
                }
                
                this.addMessageToSession(this.currentSession, 'assistant', data.response);
                
                // Update session list to reflect new activity
                this.renderSessions();
            } else {
                throw new Error('Failed to send message');
            }
        } catch (error) {
            this.hideTypingIndicator();
            this.showError('Failed to send message. Please try again.');
            console.error('Error sending message:', error);
        }
    }

    // ===== EVENT HANDLERS =====

    async handleNameSubmit() {
        const name = document.getElementById('nameInput').value.trim();
        if (!name) {
            this.showError('Please enter your name');
            return;
        }

        try {
            this.createUser(name);
            this.hideNameModal();
            this.loadUserData();
        } catch (error) {
            this.showError('Failed to create user. Please try again.');
            console.error('Error creating user:', error);
        }
    }

    // ===== UI RENDERING =====

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
        div.className = `session-item ${session.id === this.currentSession ? 'active' : ''}`;
        div.setAttribute('data-session-id', session.id);
        
        const createdDate = new Date(session.createdAt).toLocaleDateString();
        
        div.innerHTML = `
            <div class="session-content">
                <div class="session-name">${session.name}</div>
                <div class="session-date">${createdDate} • ${session.messageCount || 0} messages</div>
            </div>
            <div class="session-actions">
                <button onclick="app.editSessionName('${session.id}')" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
                <button onclick="app.deleteSession('${session.id}')" title="Delete">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;

        div.addEventListener('click', (e) => {
            if (!e.target.closest('.session-actions')) {
                this.loadSession(session.id);
            }
        });

        return div;
    }

    renderChatHistory(messages) {
        const chatMessages = document.getElementById('chatMessages');
        const welcomeMessage = chatMessages.querySelector('.welcome-message');
        
        chatMessages.innerHTML = '';
        
        if (messages.length === 0) {
            chatMessages.appendChild(welcomeMessage);
        } else {
            messages.forEach(message => {
                this.addMessage(message.content, message.type);
            });
        }

        this.scrollToBottom();
    }

    updateActiveSession() {
        document.querySelectorAll('.session-item').forEach(item => {
            item.classList.remove('active');
        });
        
        const activeSession = document.querySelector(`[data-session-id="${this.currentSession}"]`);
        if (activeSession) {
            activeSession.classList.add('active');
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

    // ===== TTS FUNCTIONALITY =====

    async initializeTTS() {
        try {
            const response = await fetch('/api/tts/support');
            const data = await response.json();
            this.ttsSupported = data.supported;
            
            if (this.ttsSupported) {
                console.log('TTS supported with languages:', data.languages);
                this.addTTSControls();
            }
        } catch (error) {
            console.error('TTS initialization failed:', error);
            this.ttsSupported = false;
        }
    }

    addTTSControls() {
        // Add TTS toggle to input footer
	/*
        const inputFooter = document.getElementById('inputWrapper');
        if (inputFooter) {
            const ttsToggle = document.createElement('button');
            ttsToggle.id = 'ttsToggle';
            ttsToggle.className = 'tts-toggle';
            ttsToggle.innerHTML = '<i class="fas fa-volume-up"></i>';
            ttsToggle.title = 'Toggle voice responses';
            ttsToggle.addEventListener('click', () => this.toggleTTS());
            
            const inputButtons = inputFooter.querySelector('.input-buttons');
            inputButtons.insertBefore(ttsToggle, inputButtons.firstChild);
        }
	*/
    }

    toggleTTS() {
        this.ttsEnabled = !this.ttsEnabled;
        const toggle = document.getElementById('ttsToggle');
        if (toggle) {
            toggle.classList.toggle('active', this.ttsEnabled);
            toggle.innerHTML = this.ttsEnabled ? 
                '<i class="fas fa-volume-up"></i>' : 
                '<i class="fas fa-volume-mute"></i>';
        }
        
        // Save preference
        localStorage.setItem('exambot_tts_enabled', this.ttsEnabled.toString());
        
        // Show status message
        this.showTTSStatus(this.ttsEnabled ? 'Voice responses enabled' : 'Voice responses disabled');
    }

    showTTSStatus(message) {
        const statusDiv = document.createElement('div');
        statusDiv.className = 'tts-status-message';
        statusDiv.textContent = message;
        
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.appendChild(statusDiv);
        
        setTimeout(() => {
            statusDiv.remove();
        }, 2000);
        
        this.scrollToBottom();
    }

    async playTTSAudio(audioData, format) {
        try {
            // Stop any currently playing audio
            if (this.currentAudio) {
                this.currentAudio.pause();
                this.currentAudio = null;
            }

            // Convert base64 audio data to blob
            const binaryString = atob(audioData);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            const audioBlob = new Blob([bytes], { type: `audio/${format}` });
            
            // Create audio element and play
            this.currentAudio = new Audio();
            this.currentAudio.src = URL.createObjectURL(audioBlob);
            
            // Add visual indicator
            this.showTTSPlaying();
            
            this.currentAudio.onended = () => {
                this.hideTTSPlaying();
                URL.revokeObjectURL(this.currentAudio.src);
                this.currentAudio = null;
            };
            
            this.currentAudio.onerror = (e) => {
                console.error('TTS audio playback error:', e);
                this.hideTTSPlaying();
                this.showError('Failed to play voice response');
            };
            
            await this.currentAudio.play();
            
        } catch (error) {
            console.error('Failed to play TTS audio:', error);
            this.showError('Failed to play voice response');
        }
    }

    showTTSPlaying() {
        const indicator = document.createElement('div');
        indicator.id = 'ttsPlayingIndicator';
        indicator.className = 'tts-playing-indicator';
        indicator.innerHTML = `
            <div class="tts-icon">
                <i class="fas fa-volume-up"></i>
            </div>
            <div class="tts-text">Playing voice response...</div>
            <button onclick="app.stopTTSAudio()" class="tts-stop-btn">
                <i class="fas fa-stop"></i>
            </button>
        `;
        
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.appendChild(indicator);
        this.scrollToBottom();
    }

    hideTTSPlaying() {
        const indicator = document.getElementById('ttsPlayingIndicator');
        if (indicator) {
            indicator.remove();
        }
    }

    stopTTSAudio() {
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio = null;
            this.hideTTSPlaying();
        }
    }

    // ===== AUDIO RECORDING FUNCTIONALITY =====

    async initializeAudio() {
        try {
            // Check if audio is supported
            const support = await AudioRecorder.checkBrowserSupport();
            this.audioSupported = support.supported;

            if (this.audioSupported) {
                this.audioRecorder = new AudioRecorder();
                this.audioPlayer = new AudioPlayer();
                
                // Set up audio recorder callbacks
                this.audioRecorder.onRecordingStart = () => this.handleRecordingStart();
                this.audioRecorder.onRecordingStop = (blob, duration) => this.handleRecordingStop(blob, duration);
                this.audioRecorder.onRecordingError = (error) => this.handleRecordingError(error);

                await this.audioRecorder.initialize();
                
                // Show audio support indicator
                document.getElementById('audioSupport').style.display = 'inline-flex';
                
                // Check server audio support
                await this.checkServerAudioSupport();
            } else {
                console.warn('Audio not supported:', support.reason);
                this.disableAudioFeatures();
            }
        } catch (error) {
            console.error('Audio initialization failed:', error);
            this.disableAudioFeatures();
        }
    }

    async checkServerAudioSupport() {
        try {
            const response = await fetch('/api/audio/support');
            const data = await response.json();
            
            if (!data.supported) {
                console.warn('Server audio processing not available:', data.error);
                this.disableAudioFeatures();
            }
        } catch (error) {
            console.error('Failed to check server audio support:', error);
        }
    }

    disableAudioFeatures() {
        const micButton = document.getElementById('micButton');
        if (micButton) {
            micButton.disabled = true;
            micButton.title = 'Voice input not available';
            micButton.classList.add('disabled');
        }
        document.getElementById('audioSupport').style.display = 'none';
    }

    // Audio Recording Methods
    async toggleRecording() {
        if (!this.audioSupported || !this.audioRecorder) {
            this.showError('Voice input is not available');
            return;
        }

        if (this.isRecording) {
            this.stopRecording();
        } else {
            await this.startRecording();
        }
    }

    async startRecording() {
        try {
            this.clearAudioStates();
            const success = await this.audioRecorder.startRecording();
            
            if (success) {
                this.isRecording = true;
                this.showRecordingState();
                this.startRecordingTimer();
            }
        } catch (error) {
            console.error('Failed to start recording:', error);
            
            if (error.name === 'NotAllowedError') {
                this.showMicrophonePermissionModal();
            } else {
                this.showError('Failed to start recording: ' + error.message);
            }
        }
    }

    stopRecording() {
        if (this.audioRecorder && this.isRecording) {
            this.audioRecorder.stopRecording();
            this.isRecording = false;
            this.stopRecordingTimer();
        }
    }

    handleRecordingStart() {
        console.log('Recording started');
    }

    handleRecordingStop(audioBlob, duration) {
        this.recordedAudioBlob = audioBlob;
        this.hideRecordingState();
        this.showAudioPreview(audioBlob);
        console.log(`Recording stopped. Duration: ${duration}s, Size: ${audioBlob.size} bytes`);
    }

    handleRecordingError(error) {
        this.hideRecordingState();
        this.showError('Recording error: ' + error);
        this.isRecording = false;
        this.stopRecordingTimer();
    }

    async sendAudioMessage() {
        if (!this.recordedAudioBlob || !this.currentSession) {
            return;
        }
    
        this.hideAudioPreview();
        this.showTypingIndicator();
    
        try {
            const context = this.buildConversationContext();
            const formData = new FormData();
            formData.append('audio_file', this.recordedAudioBlob, 'recording.webm');
            formData.append('context', JSON.stringify(context));
    
            const response = await fetch('/api/chat/audio', {
                method: 'POST',
                body: formData
            });
    
            if (response.ok) {
                const data = await response.json();
                this.hideTypingIndicator();
    
                if (data.success) {
                    // Add transcription as user message
                    const userMessage = `🎤 "${data.transcription}"`;
                    this.addMessage(userMessage, 'user');
                    this.addMessageToSession(this.currentSession, 'user', userMessage, { 
                        isAudio: true, 
                        transcription: data.transcription 
                    });
                    
                    // Store tool calls if present
                    if (data.tool_calls && data.tool_responses) {
                        this.addMessageToSession(this.currentSession, 'tool_calls', '', {
                            tool_calls: data.tool_calls,
                            tool_responses: data.tool_responses,
                            assistant_content: data.assistant_content
                        });
                    }
                    
                    // Add assistant response
                    this.addMessage(data.response, 'bot');
                    this.addMessageToSession(this.currentSession, 'assistant', data.response);
                    
                    // Play TTS if available and enabled
                    if (this.ttsEnabled && data.tts_audio) {
                        await this.playTTSAudio(data.tts_audio, data.tts_format || 'wav');
                    }
                    
                    // Update session list
                    this.renderSessions();
                } else {
                    this.showError(data.error || 'Audio processing failed');
                }
            } else {
                throw new Error('Failed to send audio message');
            }
        } catch (error) {
            this.hideTypingIndicator();
            this.showError('Failed to send audio message: ' + error.message);
        } finally {
            this.clearAudioStates();
        }
    }

    discardAudio() {
        this.clearAudioStates();
    }

    sendTranscriptionMessage() {
        const transcriptionText = document.getElementById('transcriptionText').textContent;
        if (transcriptionText.trim()) {
            document.getElementById('messageInput').value = transcriptionText;
            this.clearAudioStates();
            this.sendMessage();
        }
    }

    editTranscription() {
        const transcriptionText = document.getElementById('transcriptionText').textContent;
        document.getElementById('messageInput').value = transcriptionText;
        this.clearAudioStates();
        document.getElementById('messageInput').focus();
    }

    // Audio UI State Management
    showRecordingState() {
        document.getElementById('audioStatus').style.display = 'flex';
        document.getElementById('inputWrapper').style.display = 'none';
        
        const micButton = document.getElementById('micButton');
        micButton.classList.add('recording');
        micButton.innerHTML = '<i class="fas fa-stop"></i>';
    }

    hideRecordingState() {
        document.getElementById('audioStatus').style.display = 'none';
        document.getElementById('inputWrapper').style.display = 'flex';
        
        const micButton = document.getElementById('micButton');
        micButton.classList.remove('recording');
        micButton.innerHTML = '<i class="fas fa-microphone"></i>';
    }

    showAudioPreview(audioBlob) {
        const audioPlayer = document.getElementById('audioPlayer');
        audioPlayer.src = URL.createObjectURL(audioBlob);
        document.getElementById('audioPreview').style.display = 'block';
        document.getElementById('inputWrapper').style.display = 'none';
    }

    hideAudioPreview() {
        document.getElementById('audioPreview').style.display = 'none';
        document.getElementById('inputWrapper').style.display = 'flex';
        
        const audioPlayer = document.getElementById('audioPlayer');
        if (audioPlayer.src) {
            URL.revokeObjectURL(audioPlayer.src);
            audioPlayer.src = '';
        }
    }

    showTranscriptionPreview(transcriptionText) {
        document.getElementById('transcriptionText').textContent = transcriptionText;
        document.getElementById('transcriptionPreview').style.display = 'block';
        document.getElementById('inputWrapper').style.display = 'none';
    }

    hideTranscriptionPreview() {
        document.getElementById('transcriptionPreview').style.display = 'none';
        document.getElementById('inputWrapper').style.display = 'flex';
    }

    clearAudioStates() {
        this.hideRecordingState();
        this.hideAudioPreview();
        this.hideTranscriptionPreview();
        this.recordedAudioBlob = null;
    }

    startRecordingTimer() {
        let seconds = 0;
        this.recordingTimer = setInterval(() => {
            seconds++;
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            document.getElementById('recordingTime').textContent = 
                `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
        }, 1000);
    }

    stopRecordingTimer() {
        if (this.recordingTimer) {
            clearInterval(this.recordingTimer);
            this.recordingTimer = null;
        }
    }

    showMicrophonePermissionModal() {
        document.getElementById('audioPermissionModal').style.display = 'flex';
    }

    hideMicrophonePermissionModal() {
        document.getElementById('audioPermissionModal').style.display = 'none';
    }

    async requestMicrophonePermission() {
        try {
            await navigator.mediaDevices.getUserMedia({ audio: true });
            this.hideMicrophonePermissionModal();
            this.audioSupported = true;
            await this.initializeAudio();
        } catch (error) {
            this.showError('Microphone permission denied');
            this.hideMicrophonePermissionModal();
        }
    }

    skipMicrophonePermission() {
        this.hideMicrophonePermissionModal();
        this.disableAudioFeatures();
    }

    // ===== EVENT BINDING =====

    bindEvents() {
        // Name submission events
        document.getElementById('submitName').addEventListener('click', () => this.handleNameSubmit());
        document.getElementById('nameInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleNameSubmit();
        });

        // Message sending events
        document.getElementById('sendButton').addEventListener('click', () => this.sendMessage());
        document.getElementById('messageInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // UI events
        document.getElementById('messageInput').addEventListener('input', () => this.updateCharCount());
        document.getElementById('newChatBtn').addEventListener('click', () => this.createNewSession());
        document.getElementById('sidebarToggle').addEventListener('click', () => this.toggleSidebar());

        // Audio events
        document.getElementById('micButton')?.addEventListener('click', () => this.toggleRecording());
        document.getElementById('stopRecordingBtn')?.addEventListener('click', () => this.stopRecording());
        document.getElementById('sendAudioBtn')?.addEventListener('click', () => this.sendAudioMessage());
        document.getElementById('discardAudioBtn')?.addEventListener('click', () => this.discardAudio());
        document.getElementById('sendTranscriptionBtn')?.addEventListener('click', () => this.sendTranscriptionMessage());
        document.getElementById('editTranscriptionBtn')?.addEventListener('click', () => this.editTranscription());

        // Audio permission modal events
        document.getElementById('requestMicPermission')?.addEventListener('click', () => this.requestMicrophonePermission());
        document.getElementById('skipMicPermission')?.addEventListener('click', () => this.skipMicrophonePermission());

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

    // ===== UI HELPER METHODS =====

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
        } else if (type === 'assistant') {
            messageDiv.innerHTML = `
                <div class="message-content">${this.formatMessage(content)}</div>
            `;
        } else{
            messageDiv.innerHTML = `
                <div class="message-content">${this.formatMessage(content)}</div>
            `;
        }

        chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    formatMessage(content) {
        content = this.escapeHtml(content);
        content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        content = content.replace(/\*(.*?)\*/g, '<em>$1</em>');
        content = content.replace(/\n/g, '<br>');
        content = content.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
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
