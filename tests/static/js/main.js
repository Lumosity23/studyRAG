/**
 * StudyRAG Main Application
 * Entry point for the StudyRAG web application
 */

window.StudyRAG = window.StudyRAG || {};
window.StudyRAG.App = {
  
  // Application state
  state: {
    isInitialized: false,
    apiBaseUrl: '/api/v1',
    currentUser: null,
    settings: {
      theme: 'light',
      language: 'en',
      notifications: true
    }
  },
  
  // API client
  api: {
    
    /**
     * Make API request
     * @param {string} endpoint - API endpoint
     * @param {Object} options - Request options
     * @returns {Promise} Response promise
     */
    async request(endpoint, options = {}) {
      const {
        method = 'GET',
        data = null,
        headers = {},
        timeout = 30000
      } = options;
      
      const url = `${window.StudyRAG.App.state.apiBaseUrl}${endpoint}`;
      
      const requestOptions = {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...headers
        }
      };
      
      if (data) {
        if (data instanceof FormData) {
          delete requestOptions.headers['Content-Type'];
          requestOptions.body = data;
        } else {
          requestOptions.body = JSON.stringify(data);
        }
      }
      
      // Create timeout promise
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('Request timeout')), timeout);
      });
      
      try {
        const response = await Promise.race([
          fetch(url, requestOptions),
          timeoutPromise
        ]);
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.message || `HTTP ${response.status}`);
        }
        
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          return await response.json();
        }
        
        return await response.text();
        
      } catch (error) {
        console.error('API request failed:', error);
        throw error;
      }
    },
    
    /**
     * Upload files
     * @param {FileList} files - Files to upload
     * @param {Function} onProgress - Progress callback
     * @returns {Promise} Upload promise
     */
    async uploadFiles(files, onProgress = null) {
      const formData = new FormData();
      Array.from(files).forEach(file => {
        formData.append('files', file);
      });
      
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        
        // Progress tracking
        if (onProgress) {
          xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
              const percentComplete = (e.loaded / e.total) * 100;
              onProgress(percentComplete);
            }
          });
        }
        
        // Response handling
        xhr.addEventListener('load', () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              const response = JSON.parse(xhr.responseText);
              resolve(response);
            } catch (error) {
              resolve(xhr.responseText);
            }
          } else {
            reject(new Error(`Upload failed: ${xhr.status}`));
          }
        });
        
        xhr.addEventListener('error', () => {
          reject(new Error('Upload failed'));
        });
        
        // Send request
        xhr.open('POST', `${this.state.apiBaseUrl}/documents/upload`);
        xhr.send(formData);
      });
    },
    
    /**
     * Get health status
     */
    async getHealth() {
      return this.request('/health');
    },
    
    /**
     * Search documents
     * @param {string} query - Search query
     * @param {Object} options - Search options
     */
    async search(query, options = {}) {
      return this.request('/search', {
        method: 'POST',
        data: { query, ...options }
      });
    },
    
    /**
     * Send chat message
     * @param {string} message - Chat message
     * @param {string} conversationId - Conversation ID
     */
    async sendMessage(message, conversationId = null) {
      return this.request('/chat/message', {
        method: 'POST',
        data: { message, conversation_id: conversationId }
      });
    },
    
    /**
     * Get documents list
     */
    async getDocuments() {
      return this.request('/database/documents');
    },
    
    /**
     * Delete document
     * @param {string} documentId - Document ID
     */
    async deleteDocument(documentId) {
      return this.request(`/database/documents/${documentId}`, {
        method: 'DELETE'
      });
    },
    
    /**
     * Get configuration
     */
    async getConfig() {
      return this.request('/config/models/embeddings');
    }
  },
  
  /**
   * Initialize the application
   */
  async init() {
    try {
      console.log('Initializing StudyRAG application...');
      
      // Show loading
      window.StudyRAG.Components.LoadingOverlay.show('Initializing application...');
      
      // Check API health
      await this.checkApiHealth();
      
      // Load user settings
      this.loadSettings();
      
      // Initialize theme
      this.initializeTheme();
      
      // Initialize keyboard shortcuts
      this.initializeKeyboardShortcuts();
      
      // Initialize error handling
      this.initializeErrorHandling();
      
      // Initialize service worker (if available)
      this.initializeServiceWorker();
      
      // Mark as initialized
      this.state.isInitialized = true;
      
      console.log('StudyRAG application initialized successfully');
      
      // Show welcome message
      window.StudyRAG.Components.Toast.success(
        'Welcome to StudyRAG! Your AI-powered research assistant is ready.',
        { title: 'Application Ready', duration: 3000 }
      );
      
    } catch (error) {
      console.error('Failed to initialize application:', error);
      
      window.StudyRAG.Components.Toast.error(
        'Failed to initialize the application. Please refresh the page.',
        { title: 'Initialization Error', duration: 0 }
      );
    } finally {
      // Hide loading
      window.StudyRAG.Components.LoadingOverlay.hide();
    }
  },
  
  /**
   * Check API health
   */
  async checkApiHealth() {
    try {
      const health = await this.api.getHealth();
      console.log('API health check passed:', health);
    } catch (error) {
      console.warn('API health check failed:', error);
      throw new Error('API is not available');
    }
  },
  
  /**
   * Load user settings from localStorage
   */
  loadSettings() {
    try {
      const savedSettings = localStorage.getItem('studyrag-settings');
      if (savedSettings) {
        this.state.settings = {
          ...this.state.settings,
          ...JSON.parse(savedSettings)
        };
      }
    } catch (error) {
      console.warn('Failed to load settings:', error);
    }
  },
  
  /**
   * Save user settings to localStorage
   */
  saveSettings() {
    try {
      localStorage.setItem('studyrag-settings', JSON.stringify(this.state.settings));
    } catch (error) {
      console.warn('Failed to save settings:', error);
    }
  },
  
  /**
   * Initialize theme
   */
  initializeTheme() {
    const { theme } = this.state.settings;
    document.documentElement.setAttribute('data-theme', theme);
    
    // Listen for system theme changes
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      mediaQuery.addEventListener('change', (e) => {
        if (this.state.settings.theme === 'auto') {
          document.documentElement.setAttribute('data-theme', e.matches ? 'dark' : 'light');
        }
      });
    }
  },
  
  /**
   * Initialize keyboard shortcuts
   */
  initializeKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      // Ctrl/Cmd + K for search
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        window.StudyRAG.Router.navigate('search');
        
        // Focus search input after navigation
        setTimeout(() => {
          const searchInput = document.getElementById('search-query');
          if (searchInput) {
            searchInput.focus();
          }
        }, 100);
      }
      
      // Ctrl/Cmd + / for help
      if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        e.preventDefault();
        window.StudyRAG.Router.navigate('help');
      }
      
      // Escape to close modals
      if (e.key === 'Escape') {
        // Close mobile menu
        const mobileMenu = document.querySelector('.navbar-menu.active');
        if (mobileMenu) {
          mobileMenu.classList.remove('active');
          const menuBtn = document.querySelector('.mobile-menu-btn');
          if (menuBtn) {
            menuBtn.setAttribute('aria-expanded', 'false');
          }
        }
      }
    });
  },
  
  /**
   * Initialize global error handling
   */
  initializeErrorHandling() {
    // Handle unhandled promise rejections
    window.addEventListener('unhandledrejection', (e) => {
      console.error('Unhandled promise rejection:', e.reason);
      
      window.StudyRAG.Components.Toast.error(
        'An unexpected error occurred. Please try again.',
        { title: 'Application Error' }
      );
      
      e.preventDefault();
    });
    
    // Handle JavaScript errors
    window.addEventListener('error', (e) => {
      console.error('JavaScript error:', e.error);
      
      // Don't show toast for every JS error to avoid spam
      if (e.error && e.error.message && !e.error.message.includes('Script error')) {
        window.StudyRAG.Components.Toast.error(
          'A technical error occurred. Please refresh the page if problems persist.',
          { title: 'Script Error' }
        );
      }
    });
  },
  
  /**
   * Initialize service worker for offline support
   */
  async initializeServiceWorker() {
    if ('serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('/static/sw.js');
        console.log('Service worker registered:', registration);
      } catch (error) {
        console.warn('Service worker registration failed:', error);
      }
    }
  },
  
  /**
   * Handle file uploads with progress tracking
   * @param {FileList} files - Files to upload
   */
  async handleFileUpload(files) {
    if (!files || files.length === 0) return;
    
    // Create progress modal
    const progressModal = window.StudyRAG.Components.Modal.create({
      title: 'Uploading Documents',
      closable: false,
      content: '<div id="upload-progress-container"></div>'
    });
    
    progressModal.show();
    
    // Create progress bar
    const progressBar = window.StudyRAG.Components.ProgressBar.create({
      label: 'Uploading files...',
      animated: true
    });
    
    const progressContainer = document.getElementById('upload-progress-container');
    progressContainer.appendChild(progressBar.element);
    
    try {
      // Upload files with progress tracking
      const result = await this.api.uploadFiles(files, (progress) => {
        progressBar.setValue(progress);
      });
      
      // Success
      progressModal.hide();
      
      window.StudyRAG.Components.Toast.success(
        `Successfully uploaded ${files.length} file(s)`,
        { title: 'Upload Complete' }
      );
      
      // Refresh documents list if on documents page
      if (window.StudyRAG.Router.currentRoute === 'documents') {
        // TODO: Refresh documents list
      }
      
    } catch (error) {
      progressModal.hide();
      
      window.StudyRAG.Components.Toast.error(
        `Upload failed: ${error.message}`,
        { title: 'Upload Error' }
      );
    }
  },
  
  /**
   * Handle search with loading state
   * @param {string} query - Search query
   */
  async handleSearch(query) {
    if (!query.trim()) return;
    
    const searchResults = document.getElementById('search-results');
    if (!searchResults) return;
    
    // Show loading
    searchResults.innerHTML = `
      <div class="text-center" style="padding: 2rem;">
        <div class="spinner" style="margin: 0 auto 1rem;"></div>
        <p>Searching documents...</p>
      </div>
    `;
    
    try {
      const results = await this.api.search(query);
      
      // Display results
      if (results.length === 0) {
        searchResults.innerHTML = `
          <div class="card">
            <div class="card-body text-center">
              <p>No results found for "${window.StudyRAG.Utils.escapeHtml(query)}"</p>
              <p class="text-muted">Try different keywords or check your spelling.</p>
            </div>
          </div>
        `;
      } else {
        const resultsHtml = results.map(result => `
          <div class="card" style="margin-bottom: 1rem;">
            <div class="card-body">
              <h3>${window.StudyRAG.Utils.escapeHtml(result.title || 'Untitled')}</h3>
              <p>${window.StudyRAG.Utils.escapeHtml(result.content || '')}</p>
              <div class="text-muted">
                <small>Score: ${result.score?.toFixed(2) || 'N/A'}</small>
              </div>
            </div>
          </div>
        `).join('');
        
        searchResults.innerHTML = resultsHtml;
      }
      
    } catch (error) {
      searchResults.innerHTML = `
        <div class="card">
          <div class="card-body text-center">
            <p style="color: var(--error-500);">Search failed: ${window.StudyRAG.Utils.escapeHtml(error.message)}</p>
            <button class="btn btn-secondary" onclick="window.StudyRAG.App.handleSearch('${window.StudyRAG.Utils.escapeHtml(query)}')">
              Try Again
            </button>
          </div>
        </div>
      `;
    }
  },
  
  /**
   * Handle chat message
   * @param {string} message - Chat message
   */
  async handleChatMessage(message) {
    if (!message.trim()) return;
    
    const chatMessages = document.querySelector('.chat-messages');
    if (!chatMessages) return;
    
    // Add user message
    const userMessage = document.createElement('div');
    userMessage.className = 'chat-message user-message';
    userMessage.innerHTML = `
      <div class="message-content">
        <p>${window.StudyRAG.Utils.escapeHtml(message)}</p>
        <small class="message-time">${window.StudyRAG.Utils.formatDate(new Date())}</small>
      </div>
    `;
    chatMessages.appendChild(userMessage);
    
    // Add loading message
    const loadingMessage = document.createElement('div');
    loadingMessage.className = 'chat-message assistant-message loading';
    loadingMessage.innerHTML = `
      <div class="message-content">
        <div class="spinner" style="width: 20px; height: 20px;"></div>
        <p>AI is thinking...</p>
      </div>
    `;
    chatMessages.appendChild(loadingMessage);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    try {
      const response = await this.api.sendMessage(message);
      
      // Remove loading message
      loadingMessage.remove();
      
      // Add assistant response
      const assistantMessage = document.createElement('div');
      assistantMessage.className = 'chat-message assistant-message';
      assistantMessage.innerHTML = `
        <div class="message-content">
          <p>${window.StudyRAG.Utils.escapeHtml(response.message || 'No response')}</p>
          <small class="message-time">${window.StudyRAG.Utils.formatDate(new Date())}</small>
        </div>
      `;
      chatMessages.appendChild(assistantMessage);
      
      // Scroll to bottom
      chatMessages.scrollTop = chatMessages.scrollHeight;
      
    } catch (error) {
      // Remove loading message
      loadingMessage.remove();
      
      // Add error message
      const errorMessage = document.createElement('div');
      errorMessage.className = 'chat-message error-message';
      errorMessage.innerHTML = `
        <div class="message-content">
          <p style="color: var(--error-500);">Failed to send message: ${window.StudyRAG.Utils.escapeHtml(error.message)}</p>
          <button class="btn btn-sm btn-secondary" onclick="window.StudyRAG.App.handleChatMessage('${window.StudyRAG.Utils.escapeHtml(message)}')">
            Retry
          </button>
        </div>
      `;
      chatMessages.appendChild(errorMessage);
      
      // Scroll to bottom
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
  }
};

// Initialize application when DOM is ready
window.StudyRAG.DOM.ready().then(() => {
  window.StudyRAG.App.init();
  
  // Handle welcome screen actions
  const uploadBtn = document.querySelector('[data-action="upload-document"]');
  const chatBtn = document.querySelector('[data-action="start-chat"]');
  
  if (uploadBtn) {
    uploadBtn.addEventListener('click', () => {
      window.StudyRAG.Router.navigate('documents');
    });
  }
  
  if (chatBtn) {
    chatBtn.addEventListener('click', () => {
      window.StudyRAG.Router.navigate('chat');
    });
  }
});

// Expose app to global scope for debugging
window.app = window.StudyRAG.App;