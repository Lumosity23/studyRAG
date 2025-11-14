/**
 * StudyRAG Router
 * Simple client-side routing for single-page application
 */

window.StudyRAG = window.StudyRAG || {};
window.StudyRAG.Router = {
  routes: new Map(),
  currentRoute: null,
  defaultRoute: 'documents',
  
  /**
   * Initialize the router
   */
  init() {
    // Listen for hash changes
    window.addEventListener('hashchange', () => this.handleRouteChange());
    window.addEventListener('load', () => this.handleRouteChange());
    
    // Handle navigation clicks
    document.addEventListener('click', (e) => {
      const link = e.target.closest('[data-route]');
      if (link) {
        e.preventDefault();
        const route = link.getAttribute('data-route');
        this.navigate(route);
      }
    });
    
    // Register default routes
    this.registerDefaultRoutes();
  },
  
  /**
   * Register a route
   * @param {string} path - Route path
   * @param {Function} handler - Route handler function
   * @param {Object} options - Route options
   */
  register(path, handler, options = {}) {
    this.routes.set(path, {
      handler,
      title: options.title || path,
      requiresAuth: options.requiresAuth || false,
      middleware: options.middleware || []
    });
  },
  
  /**
   * Navigate to a route
   * @param {string} path - Route path
   * @param {Object} params - Route parameters
   */
  navigate(path, params = {}) {
    // Update URL hash
    window.location.hash = path;
    
    // Handle route change
    this.handleRouteChange(params);
  },
  
  /**
   * Handle route changes
   * @param {Object} params - Route parameters
   */
  async handleRouteChange(params = {}) {
    const hash = window.location.hash.slice(1) || this.defaultRoute;
    const [routePath, ...queryParts] = hash.split('?');
    
    // Parse query parameters
    const queryParams = {};
    if (queryParts.length > 0) {
      const queryString = queryParts.join('?');
      const urlParams = new URLSearchParams(queryString);
      for (const [key, value] of urlParams) {
        queryParams[key] = value;
      }
    }
    
    const route = this.routes.get(routePath);
    
    if (!route) {
      console.warn(`Route not found: ${routePath}`);
      this.navigate(this.defaultRoute);
      return;
    }
    
    // Update current route
    this.currentRoute = routePath;
    
    // Update navigation active states
    this.updateNavigation(routePath);
    
    // Update page title
    document.title = `StudyRAG - ${route.title}`;
    
    // Show loading
    window.StudyRAG.Components.LoadingOverlay.show(`Loading ${route.title}...`);
    
    try {
      // Run middleware
      for (const middleware of route.middleware) {
        await middleware(routePath, { ...params, ...queryParams });
      }
      
      // Execute route handler
      await route.handler(routePath, { ...params, ...queryParams });
      
    } catch (error) {
      console.error('Route handler error:', error);
      window.StudyRAG.Components.Toast.error(
        'Failed to load page. Please try again.',
        { title: 'Navigation Error' }
      );
    } finally {
      // Hide loading
      window.StudyRAG.Components.LoadingOverlay.hide();
    }
  },
  
  /**
   * Update navigation active states
   * @param {string} currentPath - Current route path
   */
  updateNavigation(currentPath) {
    // Update nav links
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
      const route = link.getAttribute('data-route');
      if (route === currentPath) {
        link.classList.add('active');
        link.setAttribute('aria-current', 'page');
      } else {
        link.classList.remove('active');
        link.removeAttribute('aria-current');
      }
    });
  },
  
  /**
   * Register default application routes
   */
  registerDefaultRoutes() {
    // Documents route
    this.register('documents', async (path, params) => {
      await this.loadPage('documents', {
        title: 'Document Management',
        content: this.getDocumentsPageContent()
      });
    }, { title: 'Documents' });
    
    // Search route
    this.register('search', async (path, params) => {
      await this.loadPage('search', {
        title: 'Search Documents',
        content: this.getSearchPageContent()
      });
    }, { title: 'Search' });
    
    // Chat route
    this.register('chat', async (path, params) => {
      await this.loadPage('chat', {
        title: 'AI Chat Assistant',
        content: this.getChatPageContent()
      });
    }, { title: 'Chat' });
    
    // Settings route
    this.register('settings', async (path, params) => {
      await this.loadPage('settings', {
        title: 'Application Settings',
        content: this.getSettingsPageContent()
      });
    }, { title: 'Settings' });
    
    // About route
    this.register('about', async (path, params) => {
      await this.loadPage('about', {
        title: 'About StudyRAG',
        content: this.getAboutPageContent()
      });
    }, { title: 'About' });
    
    // Help route
    this.register('help', async (path, params) => {
      await this.loadPage('help', {
        title: 'Help & Documentation',
        content: this.getHelpPageContent()
      });
    }, { title: 'Help' });
  },
  
  /**
   * Load a page with content
   * @param {string} pageId - Page identifier
   * @param {Object} options - Page options
   */
  async loadPage(pageId, options = {}) {
    const { title, content } = options;
    
    const pageContent = document.getElementById('page-content');
    if (!pageContent) return;
    
    // Add fade out effect
    pageContent.style.opacity = '0';
    
    // Wait for fade out
    await window.StudyRAG.Utils.delay(150);
    
    // Update content
    pageContent.innerHTML = content;
    
    // Add fade in effect
    pageContent.style.opacity = '1';
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
    
    // Initialize page-specific functionality
    this.initializePage(pageId);
  },
  
  /**
   * Initialize page-specific functionality
   * @param {string} pageId - Page identifier
   */
  initializePage(pageId) {
    switch (pageId) {
      case 'documents':
        this.initializeDocumentsPage();
        break;
      case 'search':
        this.initializeSearchPage();
        break;
      case 'chat':
        this.initializeChatPage();
        break;
      case 'settings':
        this.initializeSettingsPage();
        break;
    }
  },
  
  /**
   * Initialize documents page
   */
  initializeDocumentsPage() {
    // Initialize file upload
    const uploadContainer = document.getElementById('file-upload-container');
    if (uploadContainer) {
      const fileUpload = window.StudyRAG.Components.FileUpload.create({
        onFileSelect: (files) => {
          this.handleFileUpload(files);
        },
        onError: (errors) => {
          errors.forEach(error => {
            window.StudyRAG.Components.Toast.error(error, { title: 'Upload Error' });
          });
        }
      });
      
      uploadContainer.appendChild(fileUpload.element);
    }

    // Load existing documents
    this.loadDocumentsList();

    // Initialize WebSocket for real-time updates
    this.initializeDocumentWebSocket();
  },

  /**
   * Handle file upload with progress tracking
   * @param {Array} files - Selected files
   */
  async handleFileUpload(files) {
    if (!files || files.length === 0) return;

    // Create upload progress modal
    const progressModal = window.StudyRAG.Components.Modal.create({
      title: `Uploading ${files.length} file(s)`,
      closable: false,
      content: '<div id="upload-progress-list"></div>'
    });

    progressModal.show();

    const progressList = document.getElementById('upload-progress-list');
    const uploadPromises = [];

    // Create progress tracking for each file
    files.forEach((file, index) => {
      const fileProgressContainer = window.StudyRAG.DOM.create('div', {
        className: 'file-upload-progress',
        style: 'margin-bottom: 1rem;'
      });

      const fileInfo = window.StudyRAG.DOM.create('div', {
        className: 'file-info',
        style: 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;'
      });

      fileInfo.innerHTML = `
        <span class="file-name" style="font-weight: 500;">${window.StudyRAG.Utils.escapeHtml(file.name)}</span>
        <span class="file-size" style="color: var(--gray-500); font-size: 0.875rem;">${window.StudyRAG.Utils.formatFileSize(file.size)}</span>
      `;

      const progressBar = window.StudyRAG.Components.ProgressBar.create({
        label: 'Uploading...',
        animated: true,
        showPercentage: true
      });

      fileProgressContainer.appendChild(fileInfo);
      fileProgressContainer.appendChild(progressBar.element);
      progressList.appendChild(fileProgressContainer);

      // Upload file with progress tracking
      const uploadPromise = this.uploadSingleFile(file, (progress) => {
        progressBar.setValue(progress);
        if (progress === 100) {
          const label = progressBar.element.querySelector('.progress-label span');
          if (label) label.textContent = 'Processing...';
        }
      });

      uploadPromises.push(uploadPromise);
    });

    try {
      // Wait for all uploads to complete
      const results = await Promise.allSettled(uploadPromises);
      
      // Process results
      const successful = results.filter(r => r.status === 'fulfilled').length;
      const failed = results.filter(r => r.status === 'rejected').length;

      progressModal.hide();

      if (successful > 0) {
        window.StudyRAG.Components.Toast.success(
          `Successfully uploaded ${successful} file(s)${failed > 0 ? `, ${failed} failed` : ''}`,
          { title: 'Upload Complete' }
        );

        // Refresh documents list
        this.loadDocumentsList();
      }

      if (failed > 0) {
        window.StudyRAG.Components.Toast.error(
          `${failed} file(s) failed to upload`,
          { title: 'Upload Errors' }
        );
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
   * Upload a single file with progress tracking
   * @param {File} file - File to upload
   * @param {Function} onProgress - Progress callback
   */
  async uploadSingleFile(file, onProgress) {
    const formData = new FormData();
    formData.append('files', file);

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      // Progress tracking
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percentComplete = (e.loaded / e.total) * 100;
          onProgress(percentComplete);
        }
      });

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
      xhr.open('POST', `${window.StudyRAG.App.state.apiBaseUrl}/documents/upload`);
      xhr.send(formData);
    });
  },

  /**
   * Load documents list
   */
  async loadDocumentsList() {
    const documentsContainer = document.getElementById('documents-list');
    if (!documentsContainer) return;

    try {
      // Show loading
      documentsContainer.innerHTML = `
        <div class="text-center" style="padding: 2rem;">
          <div class="spinner" style="margin: 0 auto 1rem;"></div>
          <p>Loading documents...</p>
        </div>
      `;

      const documents = await window.StudyRAG.App.api.getDocuments();

      if (documents.length === 0) {
        documentsContainer.innerHTML = `
          <div class="text-center" style="color: var(--gray-500); padding: 2rem;">
            <svg style="width: 48px; height: 48px; margin-bottom: 1rem; opacity: 0.5;" viewBox="0 0 24 24" fill="currentColor">
              <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
            </svg>
            <p>No documents uploaded yet.</p>
            <p>Upload your first document to get started.</p>
          </div>
        `;
        return;
      }

      // Render documents list
      const documentsHtml = documents.map(doc => this.renderDocumentCard(doc)).join('');
      documentsContainer.innerHTML = documentsHtml;

      // Initialize document actions
      this.initializeDocumentActions();

    } catch (error) {
      documentsContainer.innerHTML = `
        <div class="text-center" style="color: var(--error-500); padding: 2rem;">
          <p>Failed to load documents: ${window.StudyRAG.Utils.escapeHtml(error.message)}</p>
          <button class="btn btn-secondary" onclick="window.StudyRAG.Router.loadDocumentsList()">
            Try Again
          </button>
        </div>
      `;
    }
  },

  /**
   * Render document card
   * @param {Object} document - Document object
   */
  renderDocumentCard(document) {
    const statusBadge = this.getStatusBadge(document.processing_status);
    const uploadDate = new Date(document.upload_date).toLocaleDateString();
    
    return `
      <div class="document-card card" data-document-id="${document.id}">
        <div class="card-body">
          <div class="document-header" style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
            <div class="document-info" style="flex: 1; min-width: 0;">
              <h3 class="document-title" style="margin: 0 0 0.5rem 0; font-size: 1.125rem; font-weight: 600; word-break: break-word;">
                ${window.StudyRAG.Utils.escapeHtml(document.filename)}
              </h3>
              <div class="document-meta" style="display: flex; flex-wrap: wrap; gap: 1rem; font-size: 0.875rem; color: var(--gray-600);">
                <span>📄 ${document.file_type.toUpperCase()}</span>
                <span>📊 ${window.StudyRAG.Utils.formatFileSize(document.file_size)}</span>
                <span>📅 ${uploadDate}</span>
                ${document.chunk_count > 0 ? `<span>🔗 ${document.chunk_count} chunks</span>` : ''}
              </div>
            </div>
            <div class="document-status" style="margin-left: 1rem;">
              ${statusBadge}
            </div>
          </div>
          
          <div class="document-actions" style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
            <button class="btn btn-sm btn-secondary document-view-btn" data-document-id="${document.id}">
              <svg class="btn-icon" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z"/>
              </svg>
              View
            </button>
            
            ${document.processing_status === 'completed' ? `
              <button class="btn btn-sm btn-secondary document-reindex-btn" data-document-id="${document.id}">
                <svg class="btn-icon" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z"/>
                </svg>
                Reindex
              </button>
            ` : ''}
            
            <button class="btn btn-sm btn-danger document-delete-btn" data-document-id="${document.id}">
              <svg class="btn-icon" viewBox="0 0 24 24" fill="currentColor">
                <path d="M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"/>
              </svg>
              Delete
            </button>
          </div>
        </div>
      </div>
    `;
  },

  /**
   * Get status badge for document
   * @param {string} status - Processing status
   */
  getStatusBadge(status) {
    const badges = {
      pending: '<span class="badge badge-warning">⏳ Pending</span>',
      processing: '<span class="badge badge-primary">⚙️ Processing</span>',
      completed: '<span class="badge badge-success">✅ Ready</span>',
      failed: '<span class="badge badge-error">❌ Failed</span>'
    };
    return badges[status] || badges.pending;
  },

  /**
   * Initialize document actions
   */
  initializeDocumentActions() {
    // View document
    document.querySelectorAll('.document-view-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const documentId = e.target.closest('[data-document-id]').dataset.documentId;
        this.viewDocument(documentId);
      });
    });

    // Reindex document
    document.querySelectorAll('.document-reindex-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const documentId = e.target.closest('[data-document-id]').dataset.documentId;
        this.reindexDocument(documentId);
      });
    });

    // Delete document
    document.querySelectorAll('.document-delete-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const documentId = e.target.closest('[data-document-id]').dataset.documentId;
        this.deleteDocument(documentId);
      });
    });
  },

  /**
   * View document details
   * @param {string} documentId - Document ID
   */
  async viewDocument(documentId) {
    try {
      const document = await window.StudyRAG.App.api.request(`/database/documents/${documentId}`);
      
      const modal = window.StudyRAG.Components.Modal.create({
        title: document.filename,
        size: 'lg',
        content: `
          <div class="document-details">
            <div class="document-metadata" style="margin-bottom: 2rem;">
              <h3>Document Information</h3>
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1rem;">
                <div><strong>File Type:</strong> ${document.file_type.toUpperCase()}</div>
                <div><strong>File Size:</strong> ${window.StudyRAG.Utils.formatFileSize(document.file_size)}</div>
                <div><strong>Upload Date:</strong> ${new Date(document.upload_date).toLocaleString()}</div>
                <div><strong>Status:</strong> ${this.getStatusBadge(document.processing_status)}</div>
                <div><strong>Chunks:</strong> ${document.chunk_count}</div>
                <div><strong>Embedding Model:</strong> ${document.embedding_model}</div>
              </div>
            </div>
            
            ${document.metadata && Object.keys(document.metadata).length > 0 ? `
              <div class="document-metadata">
                <h3>Metadata</h3>
                <pre style="background: var(--gray-100); padding: 1rem; border-radius: 0.5rem; overflow-x: auto; font-size: 0.875rem;">${JSON.stringify(document.metadata, null, 2)}</pre>
              </div>
            ` : ''}
          </div>
        `
      });

      modal.show();

    } catch (error) {
      window.StudyRAG.Components.Toast.error(
        `Failed to load document details: ${error.message}`,
        { title: 'View Error' }
      );
    }
  },

  /**
   * Reindex document
   * @param {string} documentId - Document ID
   */
  async reindexDocument(documentId) {
    const confirmModal = window.StudyRAG.Components.Modal.create({
      title: 'Reindex Document',
      content: `
        <p>This will regenerate embeddings for the document using the current embedding model. This process may take a few minutes.</p>
        <p><strong>Are you sure you want to continue?</strong></p>
      `
    });

    confirmModal.addFooter(`
      <button class="btn btn-secondary" onclick="document.getElementById('${confirmModal.id}').parentElement.querySelector('.modal-close').click()">Cancel</button>
      <button class="btn btn-primary" id="confirm-reindex">Reindex</button>
    `);

    confirmModal.show();

    document.getElementById('confirm-reindex').addEventListener('click', async () => {
      confirmModal.hide();

      try {
        await window.StudyRAG.App.api.request(`/database/reindex/${documentId}`, {
          method: 'POST'
        });

        window.StudyRAG.Components.Toast.success(
          'Document reindexing started. This may take a few minutes.',
          { title: 'Reindex Started' }
        );

        // Refresh documents list
        this.loadDocumentsList();

      } catch (error) {
        window.StudyRAG.Components.Toast.error(
          `Failed to reindex document: ${error.message}`,
          { title: 'Reindex Error' }
        );
      }
    });
  },

  /**
   * Delete document
   * @param {string} documentId - Document ID
   */
  async deleteDocument(documentId) {
    const confirmModal = window.StudyRAG.Components.Modal.create({
      title: 'Delete Document',
      content: `
        <p>This will permanently delete the document and all associated data including embeddings and chunks.</p>
        <p><strong>This action cannot be undone. Are you sure?</strong></p>
      `
    });

    confirmModal.addFooter(`
      <button class="btn btn-secondary" onclick="document.getElementById('${confirmModal.id}').parentElement.querySelector('.modal-close').click()">Cancel</button>
      <button class="btn btn-danger" id="confirm-delete">Delete</button>
    `);

    confirmModal.show();

    document.getElementById('confirm-delete').addEventListener('click', async () => {
      confirmModal.hide();

      try {
        await window.StudyRAG.App.api.deleteDocument(documentId);

        window.StudyRAG.Components.Toast.success(
          'Document deleted successfully',
          { title: 'Delete Complete' }
        );

        // Refresh documents list
        this.loadDocumentsList();

      } catch (error) {
        window.StudyRAG.Components.Toast.error(
          `Failed to delete document: ${error.message}`,
          { title: 'Delete Error' }
        );
      }
    });
  },

  /**
   * Initialize WebSocket for real-time document processing updates
   */
  initializeDocumentWebSocket() {
    if (this.documentWebSocket) {
      this.documentWebSocket.close();
    }

    try {
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${wsProtocol}//${window.location.host}/ws/processing`;
      
      this.documentWebSocket = new WebSocket(wsUrl);

      this.documentWebSocket.onopen = () => {
        console.log('Document processing WebSocket connected');
      };

      this.documentWebSocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleDocumentProcessingUpdate(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.documentWebSocket.onclose = () => {
        console.log('Document processing WebSocket disconnected');
        // Attempt to reconnect after 5 seconds
        setTimeout(() => {
          if (this.currentRoute === 'documents') {
            this.initializeDocumentWebSocket();
          }
        }, 5000);
      };

      this.documentWebSocket.onerror = (error) => {
        console.error('Document processing WebSocket error:', error);
      };

    } catch (error) {
      console.warn('WebSocket not available:', error);
    }
  },

  /**
   * Handle document processing updates from WebSocket
   * @param {Object} data - Update data
   */
  handleDocumentProcessingUpdate(data) {
    const { document_id, status, progress, message } = data;

    // Update document card status
    const documentCard = document.querySelector(`[data-document-id="${document_id}"]`);
    if (documentCard) {
      const statusElement = documentCard.querySelector('.document-status');
      if (statusElement) {
        statusElement.innerHTML = this.getStatusBadge(status);
      }

      // Update progress if available
      if (progress !== undefined) {
        // Show progress in document card or toast
        if (progress < 100) {
          window.StudyRAG.Components.Toast.info(
            `Processing: ${Math.round(progress)}%`,
            { title: 'Document Processing', duration: 2000 }
          );
        }
      }
    }

    // Show completion notification
    if (status === 'completed') {
      window.StudyRAG.Components.Toast.success(
        message || 'Document processing completed',
        { title: 'Processing Complete' }
      );
      
      // Refresh documents list to get updated data
      this.loadDocumentsList();
    } else if (status === 'failed') {
      window.StudyRAG.Components.Toast.error(
        message || 'Document processing failed',
        { title: 'Processing Failed' }
      );
    }
  },
  
  /**
   * Initialize search page
   */
  initializeSearchPage() {
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
      searchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const query = new FormData(searchForm).get('query');
        if (query.trim()) {
          this.performSearch(query);
        }
      });
    }
  },
  
  /**
   * Initialize chat page
   */
  initializeChatPage() {
    const chatForm = document.getElementById('chat-form');
    if (chatForm) {
      chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const message = new FormData(chatForm).get('message');
        if (message.trim()) {
          this.sendChatMessage(message);
          chatForm.reset();
        }
      });
    }
  },
  
  /**
   * Initialize settings page
   */
  initializeSettingsPage() {
    // TODO: Initialize settings page functionality
  },
  
  /**
   * Perform search
   * @param {string} query - Search query
   */
  async performSearch(query) {
    console.log('Performing search:', query);
    // TODO: Implement search logic
    window.StudyRAG.Components.Toast.info(
      `Searching for: "${query}"`,
      { title: 'Search Started' }
    );
  },
  
  /**
   * Send chat message
   * @param {string} message - Chat message
   */
  async sendChatMessage(message) {
    console.log('Sending chat message:', message);
    // TODO: Implement chat logic
    window.StudyRAG.Components.Toast.info(
      'Message sent to AI assistant',
      { title: 'Message Sent' }
    );
  },
  
  /**
   * Get documents page content
   */
  getDocumentsPageContent() {
    return `
      <div class="page-header">
        <h1>Document Management</h1>
        <p>Upload and manage your documents for AI-powered analysis.</p>
      </div>
      
      <div class="page-content">
        <div class="card">
          <div class="card-header">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <h2 class="card-title">Upload Documents</h2>
              <div class="upload-stats" style="font-size: 0.875rem; color: var(--gray-600);">
                Supported: PDF, DOCX, HTML, TXT, MD (max 50MB)
              </div>
            </div>
          </div>
          <div class="card-body">
            <div id="file-upload-container"></div>
            <div class="upload-help" style="margin-top: 1rem; padding: 1rem; background: var(--gray-50); border-radius: 0.5rem; font-size: 0.875rem; color: var(--gray-600);">
              <strong>💡 Tips:</strong>
              <ul style="margin: 0.5rem 0 0 1rem;">
                <li>Drag and drop multiple files at once</li>
                <li>Use descriptive filenames for better organization</li>
                <li>Processing time depends on file size and complexity</li>
                <li>You'll receive real-time updates during processing</li>
              </ul>
            </div>
          </div>
        </div>
        
        <div class="card" style="margin-top: 2rem;">
          <div class="card-header">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <h2 class="card-title">Your Documents</h2>
              <button class="btn btn-sm btn-secondary" onclick="window.StudyRAG.Router.loadDocumentsList()">
                <svg class="btn-icon" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z"/>
                </svg>
                Refresh
              </button>
            </div>
          </div>
          <div class="card-body">
            <div id="documents-list" style="display: grid; gap: 1rem;">
              <!-- Documents will be loaded here -->
            </div>
          </div>
        </div>
      </div>
    `;
  },
  
  /**
   * Get search page content
   */
  getSearchPageContent() {
    return `
      <div class="page-header">
        <h1>Search Documents</h1>
        <p>Find information across all your uploaded documents using semantic search.</p>
      </div>
      
      <div class="page-content">
        <div class="card">
          <div class="card-body">
            <form id="search-form">
              <div class="form-group">
                <label for="search-query" class="form-label">Search Query</label>
                <input type="text" id="search-query" name="query" class="form-input" 
                       placeholder="Enter your search query..." required>
                <div class="form-help">
                  Use natural language to search for concepts, topics, or specific information.
                </div>
              </div>
              <button type="submit" class="btn btn-primary">
                <svg class="btn-icon" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z"/>
                </svg>
                Search
              </button>
            </form>
          </div>
        </div>
        
        <div id="search-results" class="search-results" style="margin-top: 2rem;">
          <!-- Search results will appear here -->
        </div>
      </div>
    `;
  },
  
  /**
   * Get chat page content
   */
  getChatPageContent() {
    return `
      <div class="page-header">
        <h1>AI Chat Assistant</h1>
        <p>Ask questions about your documents and get intelligent responses.</p>
      </div>
      
      <div class="page-content">
        <div class="chat-container" style="height: 60vh; display: flex; flex-direction: column;">
          <div class="chat-messages" style="flex: 1; overflow-y: auto; padding: 1rem; background: white; border-radius: 0.5rem; margin-bottom: 1rem;">
            <div class="chat-welcome" style="text-align: center; color: var(--gray-500); padding: 2rem;">
              <p>Welcome! Ask me anything about your uploaded documents.</p>
            </div>
          </div>
          
          <form id="chat-form" style="display: flex; gap: 0.5rem;">
            <input type="text" name="message" class="form-input" 
                   placeholder="Type your message..." required style="flex: 1;">
            <button type="submit" class="btn btn-primary">
              <svg class="btn-icon" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2,21L23,12L2,3V10L17,12L2,14V21Z"/>
              </svg>
              Send
            </button>
          </form>
        </div>
      </div>
    `;
  },
  
  /**
   * Get settings page content
   */
  getSettingsPageContent() {
    return `
      <div class="page-header">
        <h1>Settings</h1>
        <p>Configure your StudyRAG application preferences.</p>
      </div>
      
      <div class="page-content">
        <div class="card">
          <div class="card-header">
            <h2 class="card-title">Model Configuration</h2>
          </div>
          <div class="card-body">
            <div class="form-group">
              <label for="embedding-model" class="form-label">Embedding Model</label>
              <select id="embedding-model" class="form-select">
                <option value="all-MiniLM-L6-v2">all-MiniLM-L6-v2 (Default)</option>
                <option value="all-mpnet-base-v2">all-mpnet-base-v2 (Better Quality)</option>
              </select>
              <div class="form-help">
                Choose the embedding model for document processing and search.
              </div>
            </div>
            
            <div class="form-group">
              <label for="ollama-model" class="form-label">Ollama Model</label>
              <select id="ollama-model" class="form-select">
                <option value="llama2">Llama 2</option>
                <option value="mistral">Mistral</option>
                <option value="codellama">Code Llama</option>
              </select>
              <div class="form-help">
                Select the Ollama model for chat responses.
              </div>
            </div>
            
            <button type="button" class="btn btn-primary">Save Settings</button>
          </div>
        </div>
      </div>
    `;
  },
  
  /**
   * Get about page content
   */
  getAboutPageContent() {
    return `
      <div class="page-header">
        <h1>About StudyRAG</h1>
        <p>Learn more about your AI-powered research assistant.</p>
      </div>
      
      <div class="page-content">
        <div class="card">
          <div class="card-body">
            <h2>What is StudyRAG?</h2>
            <p>StudyRAG is a Retrieval-Augmented Generation (RAG) system designed specifically for academic research and document analysis. It combines the power of modern AI with intelligent document processing to help you find, understand, and interact with your research materials.</p>
            
            <h3>Key Features</h3>
            <ul>
              <li><strong>Multi-format Support:</strong> Process PDF, DOCX, HTML, TXT, and Markdown files</li>
              <li><strong>Semantic Search:</strong> Find information using natural language queries</li>
              <li><strong>AI Chat:</strong> Ask questions and get contextual answers from your documents</li>
              <li><strong>Local Processing:</strong> Your data stays on your system with Ollama integration</li>
              <li><strong>Advanced Extraction:</strong> Powered by Docling for accurate content extraction</li>
            </ul>
            
            <h3>Technology Stack</h3>
            <ul>
              <li><strong>Backend:</strong> FastAPI with Python</li>
              <li><strong>Vector Database:</strong> ChromaDB for semantic search</li>
              <li><strong>Document Processing:</strong> Docling for content extraction</li>
              <li><strong>Embeddings:</strong> SentenceTransformers for multilingual support</li>
              <li><strong>AI Models:</strong> Ollama for local language model inference</li>
            </ul>
          </div>
        </div>
      </div>
    `;
  },
  
  /**
   * Get help page content
   */
  getHelpPageContent() {
    return `
      <div class="page-header">
        <h1>Help & Documentation</h1>
        <p>Get help using StudyRAG effectively.</p>
      </div>
      
      <div class="page-content">
        <div class="card">
          <div class="card-header">
            <h2 class="card-title">Getting Started</h2>
          </div>
          <div class="card-body">
            <ol>
              <li><strong>Upload Documents:</strong> Go to the Documents page and upload your research files</li>
              <li><strong>Wait for Processing:</strong> Documents are processed and indexed automatically</li>
              <li><strong>Search:</strong> Use the Search page to find specific information</li>
              <li><strong>Chat:</strong> Ask questions in natural language on the Chat page</li>
            </ol>
          </div>
        </div>
        
        <div class="card" style="margin-top: 1rem;">
          <div class="card-header">
            <h2 class="card-title">Supported File Types</h2>
          </div>
          <div class="card-body">
            <ul>
              <li><strong>PDF:</strong> Academic papers, reports, books</li>
              <li><strong>DOCX:</strong> Microsoft Word documents</li>
              <li><strong>HTML:</strong> Web pages and articles</li>
              <li><strong>TXT:</strong> Plain text files</li>
              <li><strong>MD:</strong> Markdown documents</li>
            </ul>
          </div>
        </div>
        
        <div class="card" style="margin-top: 1rem;">
          <div class="card-header">
            <h2 class="card-title">Tips for Better Results</h2>
          </div>
          <div class="card-body">
            <ul>
              <li>Use descriptive filenames for your documents</li>
              <li>Ask specific questions in the chat interface</li>
              <li>Use natural language for search queries</li>
              <li>Check the Settings page to optimize model performance</li>
            </ul>
          </div>
        </div>
      </div>
    `;
  }
};

// Initialize router when DOM is ready
window.StudyRAG.DOM.ready().then(() => {
  window.StudyRAG.Router.init();
});