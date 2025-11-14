/**
 * StudyRAG Web Application
 * Modern interface for document analysis and chat with AI
 */

class StudyRAGApp {
    constructor() {
        this.currentConversationId = null;
        this.websocket = null;
        this.conversations = [];
        this.isConnected = false;
        this.uploadTasks = new Map();
        
        // API endpoints
        this.apiBase = '/api/v1';
        this.wsBase = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.wsUrl = `${this.wsBase}//${window.location.host}/api/v1/chat/ws`;
        
        this.init();
    }
    
    async init() {
        console.log('🚀 Initializing StudyRAG App...');
        
        // Initialize Lucide icons
        lucide.createIcons();
        
        // Bind event listeners
        this.bindEvents();
        
        // Load conversations
        await this.loadConversations();
        
        // Setup auto-resize for textarea
        this.setupTextareaAutoResize();
        
        // Setup drag and drop
        this.setupDragAndDrop();
        
        console.log('✅ StudyRAG App initialized successfully');
    }
    
    bindEvents() {
        // Sidebar navigation
        document.getElementById('new-chat-btn').addEventListener('click', () => this.startNewConversation());
        document.getElementById('documents-btn').addEventListener('click', () => this.openUploadModal());
        document.getElementById('search-btn').addEventListener('click', () => this.openSearchModal());
        document.getElementById('settings-btn').addEventListener('click', () => this.openSettings());
        
        // Header actions
        document.getElementById('upload-btn').addEventListener('click', () => this.openUploadModal());
        document.getElementById('share-btn').addEventListener('click', () => this.shareConversation());
        document.getElementById('sidebar-toggle').addEventListener('click', () => this.toggleSidebar());
        
        // Chat input
        const messageInput = document.getElementById('message-input');
        const sendBtn = document.getElementById('send-btn');
        
        messageInput.addEventListener('input', (e) => this.handleInputChange(e));
        messageInput.addEventListener('keydown', (e) => this.handleKeyDown(e));
        sendBtn.addEventListener('click', () => this.sendMessage());
        
        // Quick actions
        document.querySelectorAll('.quick-action-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleQuickAction(e.currentTarget.dataset.action));
        });
        
        // Upload modal
        document.getElementById('upload-modal-close').addEventListener('click', () => this.closeUploadModal());
        document.getElementById('upload-area').addEventListener('click', () => document.getElementById('file-input').click());
        document.getElementById('file-input').addEventListener('change', (e) => this.handleFileSelect(e));
        
        // Search modal
        document.getElementById('search-modal-close').addEventListener('click', () => this.closeSearchModal());
        document.getElementById('search-input').addEventListener('input', (e) => this.handleSearchInput(e));
        
        // Close modals on outside click
        document.getElementById('upload-modal').addEventListener('click', (e) => {
            if (e.target.id === 'upload-modal') this.closeUploadModal();
        });
        
        document.getElementById('search-modal').addEventListener('click', (e) => {
            if (e.target.id === 'search-modal') this.closeSearchModal();
        });
    }
    
    setupTextareaAutoResize() {
        const textarea = document.getElementById('message-input');
        
        textarea.addEventListener('input', () => {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 128) + 'px';
        });
    }
    
    setupDragAndDrop() {
        const uploadArea = document.getElementById('upload-area');
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, this.preventDefaults, false);
            document.body.addEventListener(eventName, this.preventDefaults, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => uploadArea.classList.add('drag-over'), false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => uploadArea.classList.remove('drag-over'), false);
        });
        
        uploadArea.addEventListener('drop', (e) => this.handleFileDrop(e), false);
    }
    
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    // WebSocket Management
    connectWebSocket(conversationId) {
        if (this.websocket) {
            this.websocket.close();
        }
        
        const wsUrl = `${this.wsUrl}/${conversationId}`;
        console.log(`🔌 Connecting to WebSocket: ${wsUrl}`);
        
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = () => {
            console.log('✅ WebSocket connected');
            this.isConnected = true;
            this.updateConnectionStatus(true);
        };
        
        this.websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            } catch (error) {
                console.error('❌ Error parsing WebSocket message:', error);
            }
        };
        
        this.websocket.onclose = () => {
            console.log('🔌 WebSocket disconnected');
            this.isConnected = false;
            this.updateConnectionStatus(false);
            
            // Attempt to reconnect after 3 seconds
            setTimeout(() => {
                if (this.currentConversationId) {
                    this.connectWebSocket(this.currentConversationId);
                }
            }, 3000);
        };
        
        this.websocket.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
            this.showToast('Erreur de connexion WebSocket', 'error');
        };
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'streaming_response':
                this.handleStreamingResponse(data.data);
                break;
            case 'message_received':
                console.log('📨 Message received by server');
                break;
            case 'error':
                console.error('❌ WebSocket error:', data.data.message);
                this.showToast(data.data.message, 'error');
                break;
            case 'pong':
                console.log('🏓 Pong received');
                break;
            default:
                console.log('📨 Unknown WebSocket message type:', data.type);
        }
    }
    
    sendWebSocketMessage(message) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify(message));
            return true;
        }
        return false;
    }
    
    updateConnectionStatus(connected) {
        const statusEl = document.getElementById('connection-status');
        
        if (connected) {
            statusEl.className = 'flex items-center gap-2 px-3 py-1 rounded-full bg-green-500/10 text-green-500';
            statusEl.innerHTML = `
                <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span class="text-xs font-medium">Connecté</span>
            `;
        } else {
            statusEl.className = 'flex items-center gap-2 px-3 py-1 rounded-full bg-red-500/10 text-red-500';
            statusEl.innerHTML = `
                <div class="w-2 h-2 bg-red-500 rounded-full"></div>
                <span class="text-xs font-medium">Déconnecté</span>
            `;
        }
    }
    
    // Conversation Management
    async loadConversations() {
        try {
            const response = await fetch(`${this.apiBase}/chat/conversations`);
            if (response.ok) {
                const data = await response.json();
                this.conversations = data.conversations || [];
                this.renderConversations();
            }
        } catch (error) {
            console.error('❌ Error loading conversations:', error);
        }
    }
    
    renderConversations() {
        const container = document.getElementById('conversations-list');
        
        if (this.conversations.length === 0) {
            container.innerHTML = `
                <div class="px-4 py-8 text-center text-muted-foreground">
                    <i data-lucide="message-circle" class="w-8 h-8 mx-auto mb-2 opacity-50"></i>
                    <p class="text-sm">Aucune conversation</p>
                </div>
            `;
            lucide.createIcons();
            return;
        }
        
        container.innerHTML = this.conversations.map(conv => `
            <button 
                class="conversation-item w-full text-left px-4 py-3 rounded-lg hover:bg-accent hover:text-accent-foreground transition-colors ${conv.id === this.currentConversationId ? 'bg-accent text-accent-foreground' : ''}"
                data-conversation-id="${conv.id}"
            >
                <div class="flex items-start justify-between">
                    <div class="flex-1 min-w-0">
                        <p class="text-sm font-medium truncate">${conv.title || 'Nouvelle conversation'}</p>
                        <p class="text-xs text-muted-foreground truncate">${conv.last_message || 'Pas de messages'}</p>
                    </div>
                    <span class="text-xs text-muted-foreground ml-2">${this.formatDate(conv.updated_at)}</span>
                </div>
            </button>
        `).join('');
        
        // Bind conversation click events
        container.querySelectorAll('.conversation-item').forEach(item => {
            item.addEventListener('click', () => {
                const conversationId = item.dataset.conversationId;
                this.loadConversation(conversationId);
            });
        });
    }
    
    async startNewConversation() {
        try {
            const response = await fetch(`${this.apiBase}/chat/conversations`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    title: 'Nouvelle conversation',
                    model_name: 'llama3.2'
                })
            });
            
            if (response.ok) {
                const conversation = await response.json();
                this.currentConversationId = conversation.id;
                
                // Clear chat and show welcome
                this.showWelcomeScreen();
                this.updateCurrentTitle('Nouvelle conversation');
                
                // Connect WebSocket
                this.connectWebSocket(conversation.id);
                
                // Reload conversations list
                await this.loadConversations();
                
                this.showToast('Nouvelle conversation créée', 'success');
            }
        } catch (error) {
            console.error('❌ Error creating conversation:', error);
            this.showToast('Erreur lors de la création de la conversation', 'error');
        }
    }
    
    async loadConversation(conversationId) {
        try {
            // Load conversation details
            const response = await fetch(`${this.apiBase}/chat/conversations/${conversationId}`);
            if (!response.ok) throw new Error('Conversation not found');
            
            const conversation = await response.json();
            this.currentConversationId = conversationId;
            
            // Load messages
            const messagesResponse = await fetch(`${this.apiBase}/chat/conversations/${conversationId}/messages`);
            if (messagesResponse.ok) {
                const messagesData = await messagesResponse.json();
                this.renderMessages(messagesData.messages || []);
            }
            
            // Update UI
            this.updateCurrentTitle(conversation.title);
            this.hidewelcomeScreen();
            
            // Connect WebSocket
            this.connectWebSocket(conversationId);
            
            // Update conversations list
            this.renderConversations();
            
        } catch (error) {
            console.error('❌ Error loading conversation:', error);
            this.showToast('Erreur lors du chargement de la conversation', 'error');
        }
    }
    
    // Message Handling
    handleInputChange(e) {
        const input = e.target;
        const sendBtn = document.getElementById('send-btn');
        const charCount = document.getElementById('char-count');
        
        const length = input.value.length;
        charCount.textContent = `${length} / 4000`;
        
        sendBtn.disabled = length === 0 || length > 4000;
        
        if (length > 4000) {
            charCount.classList.add('text-red-500');
        } else {
            charCount.classList.remove('text-red-500');
        }
    }
    
    handleKeyDown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.sendMessage();
        }
    }
    
    async sendMessage() {
        const input = document.getElementById('message-input');
        const message = input.value.trim();
        
        if (!message || !this.currentConversationId) return;
        
        // Clear input
        input.value = '';
        input.style.height = 'auto';
        this.handleInputChange({ target: input });
        
        // Hide welcome screen if visible
        this.hidewelcomeScreen();
        
        // Add user message to UI
        this.addMessageToUI({
            role: 'user',
            content: message,
            timestamp: new Date().toISOString()
        });
        
        // Show typing indicator
        this.showTypingIndicator();
        
        try {
            // Send via WebSocket if connected, otherwise use HTTP
            if (this.isConnected) {
                this.sendWebSocketMessage({
                    type: 'message',
                    content: message,
                    id: Date.now().toString()
                });
            } else {
                // Fallback to HTTP API
                await this.sendMessageHTTP(message);
            }
        } catch (error) {
            console.error('❌ Error sending message:', error);
            this.hideTypingIndicator();
            this.showToast('Erreur lors de l\'envoi du message', 'error');
        }
    }
    
    async sendMessageHTTP(message) {
        try {
            const response = await fetch(`${this.apiBase}/chat/message`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: this.currentConversationId,
                    include_sources: true,
                    stream: false
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.hideTypingIndicator();
                this.addMessageToUI({
                    role: 'assistant',
                    content: data.message.content,
                    timestamp: data.message.timestamp,
                    sources: data.sources_used
                });
            } else {
                throw new Error('Failed to send message');
            }
        } catch (error) {
            this.hideTypingIndicator();
            throw error;
        }
    }
    
    handleStreamingResponse(data) {
        if (data.is_complete) {
            this.hideTypingIndicator();
            if (data.message) {
                this.addMessageToUI({
                    role: 'assistant',
                    content: data.message.content,
                    timestamp: data.message.timestamp,
                    sources: data.sources_used
                });
            }
        } else if (data.delta) {
            // Handle streaming chunks (if implementing streaming UI)
            this.updateStreamingMessage(data.delta);
        }
    }
    
    addMessageToUI(message) {
        const messagesContainer = document.getElementById('chat-messages');
        const messageEl = document.createElement('div');
        messageEl.className = 'message-enter';
        
        const isUser = message.role === 'user';
        const timestamp = new Date(message.timestamp).toLocaleTimeString('fr-FR', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        messageEl.innerHTML = `
            <div class="flex items-start gap-4 ${isUser ? 'flex-row-reverse' : ''}">
                <div class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                    isUser 
                        ? 'bg-gradient-to-br from-blue-500 to-purple-600' 
                        : 'bg-gradient-to-br from-green-500 to-blue-500'
                }">
                    <i data-lucide="${isUser ? 'user' : 'bot'}" class="w-4 h-4 text-white"></i>
                </div>
                
                <div class="flex-1 max-w-3xl">
                    <div class="bg-card border border-border rounded-lg p-4 ${isUser ? 'bg-primary/10' : ''}">
                        <div class="prose prose-sm max-w-none dark:prose-invert">
                            ${this.formatMessageContent(message.content)}
                        </div>
                        
                        ${message.sources ? this.renderSources(message.sources) : ''}
                    </div>
                    
                    <div class="flex items-center gap-2 mt-2 text-xs text-muted-foreground ${isUser ? 'justify-end' : ''}">
                        <span>${isUser ? 'Vous' : 'StudyRAG'}</span>
                        <span>•</span>
                        <span>${timestamp}</span>
                    </div>
                </div>
            </div>
        `;
        
        messagesContainer.appendChild(messageEl);
        
        // Re-initialize Lucide icons for new content
        lucide.createIcons();
        
        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    formatMessageContent(content) {
        // Basic markdown-like formatting
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code class="bg-muted px-1 py-0.5 rounded text-sm">$1</code>')
            .replace(/\n/g, '<br>');
    }
    
    renderSources(sources) {
        if (!sources || sources.length === 0) return '';
        
        return `
            <div class="mt-4 pt-4 border-t border-border">
                <p class="text-xs font-medium text-muted-foreground mb-2">Sources :</p>
                <div class="space-y-2">
                    ${sources.map(source => `
                        <div class="flex items-center gap-2 text-xs">
                            <i data-lucide="file-text" class="w-3 h-3 text-muted-foreground"></i>
                            <span class="font-medium">${source.document_title || 'Document'}</span>
                            <span class="text-muted-foreground">• Score: ${(source.similarity_score * 100).toFixed(1)}%</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    renderMessages(messages) {
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.innerHTML = '';
        
        messages.forEach(message => {
            this.addMessageToUI(message);
        });
    }
    
    showTypingIndicator() {
        document.getElementById('typing-indicator').classList.remove('hidden');
    }
    
    hideTypingIndicator() {
        document.getElementById('typing-indicator').classList.add('hidden');
    }
    
    // UI State Management
    showWelcomeScreen() {
        document.getElementById('welcome-screen').classList.remove('hidden');
        document.getElementById('chat-messages').classList.add('hidden');
    }
    
    hidewelcomeScreen() {
        document.getElementById('welcome-screen').classList.add('hidden');
        document.getElementById('chat-messages').classList.remove('hidden');
    }
    
    updateCurrentTitle(title) {
        document.getElementById('current-title').textContent = title;
    }
    
    // Quick Actions
    handleQuickAction(action) {
        const input = document.getElementById('message-input');
        
        const actions = {
            upload: () => this.openUploadModal(),
            search: () => this.openSearchModal(),
            analyze: () => {
                input.value = 'Pouvez-vous analyser le contenu de mes documents ?';
                this.handleInputChange({ target: input });
            },
            summarize: () => {
                input.value = 'Pouvez-vous me faire un résumé de mes documents ?';
                this.handleInputChange({ target: input });
            }
        };
        
        if (actions[action]) {
            actions[action]();
        }
    }
    
    // File Upload
    openUploadModal() {
        document.getElementById('upload-modal').classList.remove('hidden');
        document.getElementById('upload-modal').classList.add('flex');
    }
    
    closeUploadModal() {
        document.getElementById('upload-modal').classList.add('hidden');
        document.getElementById('upload-modal').classList.remove('flex');
    }
    
    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.uploadFiles(files);
    }
    
    handleFileDrop(e) {
        const files = Array.from(e.dataTransfer.files);
        this.uploadFiles(files);
    }
    
    async uploadFiles(files) {
        const progressContainer = document.getElementById('upload-progress');
        progressContainer.classList.remove('hidden');
        
        for (const file of files) {
            await this.uploadSingleFile(file);
        }
    }
    
    async uploadSingleFile(file) {
        const taskId = Date.now().toString() + Math.random().toString(36).substr(2, 9);
        const progressContainer = document.getElementById('upload-progress');
        
        // Create progress item
        const progressItem = document.createElement('div');
        progressItem.className = 'bg-muted rounded-lg p-4';
        progressItem.innerHTML = `
            <div class="flex items-center justify-between mb-2">
                <span class="text-sm font-medium truncate">${file.name}</span>
                <span class="text-xs text-muted-foreground">${this.formatFileSize(file.size)}</span>
            </div>
            <div class="w-full bg-background rounded-full h-2">
                <div class="bg-primary h-2 rounded-full transition-all duration-300" style="width: 0%"></div>
            </div>
            <div class="text-xs text-muted-foreground mt-1">Préparation...</div>
        `;
        
        progressContainer.appendChild(progressItem);
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch(`${this.apiBase}/documents/upload`, {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const data = await response.json();
                this.uploadTasks.set(taskId, data.document_id);
                
                // Start polling for progress
                this.pollUploadProgress(data.document_id, progressItem);
                
            } else {
                throw new Error('Upload failed');
            }
            
        } catch (error) {
            console.error('❌ Upload error:', error);
            progressItem.innerHTML = `
                <div class="flex items-center justify-between">
                    <span class="text-sm font-medium text-red-500">${file.name}</span>
                    <span class="text-xs text-red-500">Échec</span>
                </div>
            `;
        }
    }
    
    async pollUploadProgress(documentId, progressItem) {
        try {
            const response = await fetch(`${this.apiBase}/documents/status/${documentId}`);
            
            if (response.ok) {
                const status = await response.json();
                
                // Update progress bar
                const progressBar = progressItem.querySelector('.bg-primary');
                const statusText = progressItem.querySelector('.text-xs.text-muted-foreground');
                
                progressBar.style.width = `${status.progress * 100}%`;
                statusText.textContent = status.message;
                
                if (status.status === 'completed') {
                    statusText.textContent = 'Traitement terminé ✅';
                    statusText.className = 'text-xs text-green-500 mt-1';
                    this.showToast('Document traité avec succès', 'success');
                    
                } else if (status.status === 'failed') {
                    statusText.textContent = `Erreur: ${status.error || 'Traitement échoué'}`;
                    statusText.className = 'text-xs text-red-500 mt-1';
                    this.showToast('Erreur lors du traitement du document', 'error');
                    
                } else {
                    // Continue polling
                    setTimeout(() => this.pollUploadProgress(documentId, progressItem), 1000);
                }
            }
        } catch (error) {
            console.error('❌ Error polling upload progress:', error);
        }
    }
    
    // Search
    openSearchModal() {
        document.getElementById('search-modal').classList.remove('hidden');
        document.getElementById('search-modal').classList.add('flex');
        document.getElementById('search-input').focus();
    }
    
    closeSearchModal() {
        document.getElementById('search-modal').classList.add('hidden');
        document.getElementById('search-modal').classList.remove('flex');
    }
    
    async handleSearchInput(e) {
        const query = e.target.value.trim();
        
        if (query.length < 2) {
            document.getElementById('search-results').innerHTML = '';
            return;
        }
        
        try {
            const response = await fetch(`${this.apiBase}/search/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    top_k: 10,
                    min_similarity: 0.3
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.renderSearchResults(data.results);
            }
        } catch (error) {
            console.error('❌ Search error:', error);
        }
    }
    
    renderSearchResults(results) {
        const container = document.getElementById('search-results');
        
        if (results.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8 text-muted-foreground">
                    <i data-lucide="search-x" class="w-8 h-8 mx-auto mb-2 opacity-50"></i>
                    <p class="text-sm">Aucun résultat trouvé</p>
                </div>
            `;
            lucide.createIcons();
            return;
        }
        
        container.innerHTML = results.map(result => `
            <div class="bg-card border border-border rounded-lg p-4 hover:bg-accent hover:text-accent-foreground transition-colors cursor-pointer">
                <div class="flex items-start justify-between mb-2">
                    <h4 class="font-medium text-sm">${result.document_title || 'Document'}</h4>
                    <span class="text-xs text-muted-foreground">${(result.similarity_score * 100).toFixed(1)}%</span>
                </div>
                <p class="text-sm text-muted-foreground line-clamp-3">${result.content}</p>
                <div class="flex items-center gap-2 mt-2">
                    <i data-lucide="file-text" class="w-3 h-3 text-muted-foreground"></i>
                    <span class="text-xs text-muted-foreground">Chunk ${result.chunk_index}</span>
                </div>
            </div>
        `).join('');
        
        lucide.createIcons();
        
        // Add click handlers to use results in chat
        container.querySelectorAll('.bg-card').forEach((item, index) => {
            item.addEventListener('click', () => {
                const result = results[index];
                this.useSearchResultInChat(result);
            });
        });
    }
    
    useSearchResultInChat(result) {
        const input = document.getElementById('message-input');
        input.value = `Pouvez-vous m'expliquer ce passage : "${result.content.substring(0, 200)}..."`;
        this.handleInputChange({ target: input });
        this.closeSearchModal();
        
        // Start new conversation if needed
        if (!this.currentConversationId) {
            this.startNewConversation();
        }
    }
    
    // Utility Functions
    formatDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        
        if (diffDays === 0) {
            return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
        } else if (diffDays === 1) {
            return 'Hier';
        } else if (diffDays < 7) {
            return `${diffDays}j`;
        } else {
            return date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' });
        }
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        
        const colors = {
            success: 'bg-green-500/10 border-green-500/20 text-green-500',
            error: 'bg-red-500/10 border-red-500/20 text-red-500',
            info: 'bg-blue-500/10 border-blue-500/20 text-blue-500',
            warning: 'bg-yellow-500/10 border-yellow-500/20 text-yellow-500'
        };
        
        toast.className = `${colors[type]} border rounded-lg p-4 shadow-lg animate-slide-up`;
        toast.innerHTML = `
            <div class="flex items-center gap-3">
                <i data-lucide="${type === 'success' ? 'check-circle' : type === 'error' ? 'x-circle' : 'info'}" class="w-4 h-4"></i>
                <span class="text-sm font-medium">${message}</span>
            </div>
        `;
        
        container.appendChild(toast);
        lucide.createIcons();
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }
    
    // Additional Features
    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        sidebar.classList.toggle('-translate-x-full');
    }
    
    shareConversation() {
        if (!this.currentConversationId) {
            this.showToast('Aucune conversation à partager', 'warning');
            return;
        }
        
        const url = `${window.location.origin}?conversation=${this.currentConversationId}`;
        navigator.clipboard.writeText(url).then(() => {
            this.showToast('Lien copié dans le presse-papiers', 'success');
        }).catch(() => {
            this.showToast('Erreur lors de la copie du lien', 'error');
        });
    }
    
    openSettings() {
        this.showToast('Paramètres - Fonctionnalité à venir', 'info');
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.studyRAG = new StudyRAGApp();
});

// Handle page visibility changes to manage WebSocket connections
document.addEventListener('visibilitychange', () => {
    if (window.studyRAG) {
        if (document.hidden) {
            // Page is hidden, could pause some operations
            console.log('📱 Page hidden');
        } else {
            // Page is visible, ensure WebSocket is connected
            console.log('📱 Page visible');
            if (window.studyRAG.currentConversationId && !window.studyRAG.isConnected) {
                window.studyRAG.connectWebSocket(window.studyRAG.currentConversationId);
            }
        }
    }
});