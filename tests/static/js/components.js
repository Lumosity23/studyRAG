/**
 * StudyRAG UI Components
 * Reusable UI components for the application
 */

window.StudyRAG = window.StudyRAG || {};
window.StudyRAG.Components = {

  /**
   * Toast Notification Component
   */
  Toast: {
    container: null,
    
    init() {
      this.container = document.getElementById('toast-container');
      if (!this.container) {
        this.container = document.createElement('div');
        this.container.id = 'toast-container';
        this.container.className = 'toast-container';
        this.container.setAttribute('aria-live', 'polite');
        this.container.setAttribute('aria-atomic', 'true');
        document.body.appendChild(this.container);
      }
    },
    
    show(message, type = 'info', options = {}) {
      this.init();
      
      const {
        title = '',
        duration = 5000,
        closable = true,
        icon = true
      } = options;
      
      const toastId = window.StudyRAG.Utils.generateId('toast');
      const toast = window.StudyRAG.DOM.create('div', {
        className: `toast ${type}`,
        id: toastId,
        role: 'alert',
        'aria-live': 'assertive'
      });
      
      // Create toast content
      const content = [];
      
      // Add icon if enabled
      if (icon) {
        const iconSvg = this.getIcon(type);
        content.push(window.StudyRAG.DOM.create('div', {
          className: 'toast-icon',
          innerHTML: iconSvg
        }));
      }
      
      // Add content
      const contentDiv = window.StudyRAG.DOM.create('div', { className: 'toast-content' });
      
      if (title) {
        contentDiv.appendChild(window.StudyRAG.DOM.create('div', {
          className: 'toast-title'
        }, title));
      }
      
      contentDiv.appendChild(window.StudyRAG.DOM.create('div', {
        className: 'toast-message'
      }, message));
      
      content.push(contentDiv);
      
      // Add close button if closable
      if (closable) {
        const closeBtn = window.StudyRAG.DOM.create('button', {
          className: 'toast-close',
          type: 'button',
          'aria-label': 'Close notification',
          innerHTML: '<svg class="toast-close-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>'
        });
        
        window.StudyRAG.DOM.on(closeBtn, 'click', () => this.hide(toastId));
        content.push(closeBtn);
      }
      
      // Add content to toast
      content.forEach(item => toast.appendChild(item));
      
      // Add to container
      this.container.appendChild(toast);
      
      // Trigger animation
      requestAnimationFrame(() => {
        toast.classList.add('active');
      });
      
      // Auto-hide after duration
      if (duration > 0) {
        setTimeout(() => this.hide(toastId), duration);
      }
      
      return toastId;
    },
    
    hide(toastId) {
      const toast = document.getElementById(toastId);
      if (toast) {
        toast.classList.remove('active');
        setTimeout(() => {
          if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
          }
        }, 300);
      }
    },
    
    success(message, options = {}) {
      return this.show(message, 'success', options);
    },
    
    error(message, options = {}) {
      return this.show(message, 'error', options);
    },
    
    warning(message, options = {}) {
      return this.show(message, 'warning', options);
    },
    
    info(message, options = {}) {
      return this.show(message, 'info', options);
    },
    
    getIcon(type) {
      const icons = {
        success: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>',
        error: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>',
        warning: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>',
        info: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>'
      };
      return icons[type] || icons.info;
    }
  },

  /**
   * Modal Component
   */
  Modal: {
    activeModals: new Set(),
    
    create(options = {}) {
      const {
        title = '',
        content = '',
        size = 'md',
        closable = true,
        backdrop = true,
        keyboard = true,
        onShow = null,
        onHide = null
      } = options;
      
      const modalId = window.StudyRAG.Utils.generateId('modal');
      
      // Create backdrop
      const backdrop = window.StudyRAG.DOM.create('div', {
        className: 'modal-backdrop',
        id: `${modalId}-backdrop`
      });
      
      // Create modal
      const modal = window.StudyRAG.DOM.create('div', {
        className: `modal modal-${size}`,
        id: modalId,
        role: 'dialog',
        'aria-modal': 'true',
        'aria-labelledby': title ? `${modalId}-title` : null
      });
      
      // Create modal content
      const modalContent = [];
      
      // Header
      if (title || closable) {
        const header = window.StudyRAG.DOM.create('div', { className: 'modal-header' });
        
        if (title) {
          header.appendChild(window.StudyRAG.DOM.create('h2', {
            className: 'modal-title',
            id: `${modalId}-title`
          }, title));
        }
        
        if (closable) {
          const closeBtn = window.StudyRAG.DOM.create('button', {
            className: 'modal-close',
            type: 'button',
            'aria-label': 'Close modal',
            innerHTML: '<svg class="modal-close-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>'
          });
          
          window.StudyRAG.DOM.on(closeBtn, 'click', () => this.hide(modalId));
          header.appendChild(closeBtn);
        }
        
        modalContent.push(header);
      }
      
      // Body
      const body = window.StudyRAG.DOM.create('div', { className: 'modal-body' });
      if (typeof content === 'string') {
        body.innerHTML = content;
      } else if (content instanceof Element) {
        body.appendChild(content);
      }
      modalContent.push(body);
      
      // Add content to modal
      modalContent.forEach(item => modal.appendChild(item));
      
      // Create container
      const container = window.StudyRAG.DOM.create('div', {
        className: 'modal-container'
      });
      
      container.appendChild(backdrop);
      container.appendChild(modal);
      
      // Event handlers
      if (backdrop) {
        window.StudyRAG.DOM.on(backdrop, 'click', () => this.hide(modalId));
      }
      
      if (keyboard) {
        window.StudyRAG.DOM.on(document, 'keydown', (e) => {
          if (e.key === 'Escape' && this.activeModals.has(modalId)) {
            this.hide(modalId);
          }
        });
      }
      
      return {
        id: modalId,
        element: container,
        modal: modal,
        body: body,
        show: () => this.show(modalId, onShow),
        hide: () => this.hide(modalId, onHide),
        setContent: (newContent) => {
          body.innerHTML = '';
          if (typeof newContent === 'string') {
            body.innerHTML = newContent;
          } else if (newContent instanceof Element) {
            body.appendChild(newContent);
          }
        },
        addFooter: (footerContent) => {
          const existingFooter = modal.querySelector('.modal-footer');
          if (existingFooter) {
            existingFooter.remove();
          }
          
          const footer = window.StudyRAG.DOM.create('div', { className: 'modal-footer' });
          if (typeof footerContent === 'string') {
            footer.innerHTML = footerContent;
          } else if (footerContent instanceof Element) {
            footer.appendChild(footerContent);
          }
          modal.appendChild(footer);
        }
      };
    },
    
    show(modalId, onShow = null) {
      const container = document.getElementById(modalId)?.parentElement;
      if (!container) return;
      
      // Add to DOM
      document.body.appendChild(container);
      container.style.display = 'block';
      
      // Trigger animation
      requestAnimationFrame(() => {
        container.querySelector('.modal-backdrop').classList.add('active');
        container.querySelector('.modal').classList.add('active');
      });
      
      // Track active modal
      this.activeModals.add(modalId);
      
      // Prevent body scroll
      document.body.style.overflow = 'hidden';
      
      // Focus management
      const modal = container.querySelector('.modal');
      const focusableElements = modal.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (focusableElements.length > 0) {
        focusableElements[0].focus();
      }
      
      if (onShow) onShow();
    },
    
    hide(modalId, onHide = null) {
      const container = document.getElementById(modalId)?.parentElement;
      if (!container) return;
      
      // Remove animations
      container.querySelector('.modal-backdrop').classList.remove('active');
      container.querySelector('.modal').classList.remove('active');
      
      // Remove from DOM after animation
      setTimeout(() => {
        if (container.parentNode) {
          container.parentNode.removeChild(container);
        }
      }, 300);
      
      // Remove from active modals
      this.activeModals.delete(modalId);
      
      // Restore body scroll if no active modals
      if (this.activeModals.size === 0) {
        document.body.style.overflow = '';
      }
      
      if (onHide) onHide();
    }
  },

  /**
   * Progress Bar Component
   */
  ProgressBar: {
    create(options = {}) {
      const {
        value = 0,
        max = 100,
        label = '',
        animated = false,
        showPercentage = true
      } = options;
      
      const progressId = window.StudyRAG.Utils.generateId('progress');
      
      const container = window.StudyRAG.DOM.create('div', {
        className: 'progress-labeled'
      });
      
      // Label
      if (label || showPercentage) {
        const labelDiv = window.StudyRAG.DOM.create('div', {
          className: 'progress-label'
        });
        
        if (label) {
          labelDiv.appendChild(window.StudyRAG.DOM.create('span', {}, label));
        }
        
        if (showPercentage) {
          const percentage = window.StudyRAG.DOM.create('span', {
            id: `${progressId}-percentage`
          }, `${Math.round((value / max) * 100)}%`);
          labelDiv.appendChild(percentage);
        }
        
        container.appendChild(labelDiv);
      }
      
      // Progress bar
      const progress = window.StudyRAG.DOM.create('div', {
        className: 'progress',
        role: 'progressbar',
        'aria-valuenow': value,
        'aria-valuemin': 0,
        'aria-valuemax': max
      });
      
      const bar = window.StudyRAG.DOM.create('div', {
        className: `progress-bar ${animated ? 'animated' : ''}`,
        id: progressId,
        style: `width: ${(value / max) * 100}%`
      });
      
      progress.appendChild(bar);
      container.appendChild(progress);
      
      return {
        element: container,
        setValue: (newValue) => {
          const percentage = Math.round((newValue / max) * 100);
          bar.style.width = `${percentage}%`;
          progress.setAttribute('aria-valuenow', newValue);
          
          if (showPercentage) {
            const percentageEl = document.getElementById(`${progressId}-percentage`);
            if (percentageEl) {
              percentageEl.textContent = `${percentage}%`;
            }
          }
        },
        setAnimated: (isAnimated) => {
          window.StudyRAG.DOM.toggleClass(bar, 'animated', isAnimated);
        }
      };
    }
  },

  /**
   * File Upload Component
   */
  FileUpload: {
    create(options = {}) {
      const {
        accept = '.pdf,.docx,.html,.txt,.md',
        multiple = true,
        maxSize = 50 * 1024 * 1024, // 50MB
        onFileSelect = null,
        onError = null
      } = options;
      
      const uploadId = window.StudyRAG.Utils.generateId('upload');
      
      const container = window.StudyRAG.DOM.create('div', {
        className: 'file-upload'
      });
      
      const input = window.StudyRAG.DOM.create('input', {
        type: 'file',
        id: uploadId,
        className: 'file-upload-input',
        accept: accept,
        multiple: multiple
      });
      
      const content = window.StudyRAG.DOM.create('div', {
        className: 'file-upload-content'
      });
      
      content.innerHTML = `
        <svg class="file-upload-icon" viewBox="0 0 24 24" fill="currentColor">
          <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
        </svg>
        <div class="file-upload-text">Drop files here or click to browse</div>
        <div class="file-upload-hint">Supports PDF, DOCX, HTML, TXT, and MD files up to ${window.StudyRAG.Utils.formatFileSize(maxSize)}</div>
      `;
      
      container.appendChild(input);
      container.appendChild(content);
      
      // Event handlers
      const handleFiles = (files) => {
        const fileArray = Array.from(files);
        const validFiles = [];
        const errors = [];
        
        fileArray.forEach(file => {
          // Check file size
          if (file.size > maxSize) {
            errors.push(`${file.name}: File too large (max ${window.StudyRAG.Utils.formatFileSize(maxSize)})`);
            return;
          }
          
          // Check file type
          if (!window.StudyRAG.Utils.isSupportedFileType(file.name)) {
            errors.push(`${file.name}: Unsupported file type`);
            return;
          }
          
          validFiles.push(file);
        });
        
        if (errors.length > 0 && onError) {
          onError(errors);
        }
        
        if (validFiles.length > 0 && onFileSelect) {
          onFileSelect(validFiles);
        }
      };
      
      // File input change
      window.StudyRAG.DOM.on(input, 'change', (e) => {
        handleFiles(e.target.files);
      });
      
      // Drag and drop
      window.StudyRAG.DOM.on(container, 'dragover', (e) => {
        e.preventDefault();
        container.classList.add('dragover');
      });
      
      window.StudyRAG.DOM.on(container, 'dragleave', (e) => {
        e.preventDefault();
        if (!container.contains(e.relatedTarget)) {
          container.classList.remove('dragover');
        }
      });
      
      window.StudyRAG.DOM.on(container, 'drop', (e) => {
        e.preventDefault();
        container.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
      });
      
      // Click to browse
      window.StudyRAG.DOM.on(container, 'click', () => {
        input.click();
      });
      
      return {
        element: container,
        reset: () => {
          input.value = '';
        }
      };
    }
  },

  /**
   * Loading Overlay Component
   */
  LoadingOverlay: {
    show(message = 'Loading...') {
      const overlay = document.getElementById('loading-overlay');
      if (overlay) {
        const messageEl = overlay.querySelector('p');
        if (messageEl) {
          messageEl.textContent = message;
        }
        overlay.classList.add('active');
        overlay.setAttribute('aria-hidden', 'false');
      }
    },
    
    hide() {
      const overlay = document.getElementById('loading-overlay');
      if (overlay) {
        overlay.classList.remove('active');
        overlay.setAttribute('aria-hidden', 'true');
      }
    }
  },

  /**
   * Dropdown Component
   */
  Dropdown: {
    create(trigger, options = {}) {
      const {
        items = [],
        placement = 'bottom-start',
        onSelect = null
      } = options;
      
      const dropdownId = window.StudyRAG.Utils.generateId('dropdown');
      
      // Create dropdown container
      const container = window.StudyRAG.DOM.create('div', {
        className: 'dropdown',
        id: dropdownId
      });
      
      // Move trigger into container
      if (trigger.parentNode) {
        trigger.parentNode.insertBefore(container, trigger);
      }
      container.appendChild(trigger);
      
      // Create menu
      const menu = window.StudyRAG.DOM.create('div', {
        className: 'dropdown-menu',
        role: 'menu'
      });
      
      // Add items
      items.forEach(item => {
        if (item === 'divider') {
          menu.appendChild(window.StudyRAG.DOM.create('div', {
            className: 'dropdown-divider'
          }));
        } else {
          const menuItem = window.StudyRAG.DOM.create('button', {
            className: 'dropdown-item',
            type: 'button',
            role: 'menuitem'
          }, item.label || item);
          
          window.StudyRAG.DOM.on(menuItem, 'click', () => {
            if (onSelect) {
              onSelect(item.value || item, item);
            }
            this.hide(dropdownId);
          });
          
          menu.appendChild(menuItem);
        }
      });
      
      container.appendChild(menu);
      
      // Toggle on trigger click
      window.StudyRAG.DOM.on(trigger, 'click', (e) => {
        e.stopPropagation();
        this.toggle(dropdownId);
      });
      
      // Close on outside click
      window.StudyRAG.DOM.on(document, 'click', () => {
        this.hide(dropdownId);
      });
      
      return {
        element: container,
        show: () => this.show(dropdownId),
        hide: () => this.hide(dropdownId),
        toggle: () => this.toggle(dropdownId)
      };
    },
    
    show(dropdownId) {
      const dropdown = document.getElementById(dropdownId);
      if (dropdown) {
        dropdown.classList.add('active');
      }
    },
    
    hide(dropdownId) {
      const dropdown = document.getElementById(dropdownId);
      if (dropdown) {
        dropdown.classList.remove('active');
      }
    },
    
    toggle(dropdownId) {
      const dropdown = document.getElementById(dropdownId);
      if (dropdown) {
        dropdown.classList.toggle('active');
      }
    }
  }
};

// Initialize components when DOM is ready
window.StudyRAG.DOM.ready().then(() => {
  // Initialize toast container
  window.StudyRAG.Components.Toast.init();
  
  // Initialize mobile menu
  const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
  const mobileMenu = document.querySelector('.navbar-menu');
  
  if (mobileMenuBtn && mobileMenu) {
    window.StudyRAG.DOM.on(mobileMenuBtn, 'click', () => {
      const isExpanded = mobileMenuBtn.getAttribute('aria-expanded') === 'true';
      mobileMenuBtn.setAttribute('aria-expanded', !isExpanded);
      mobileMenu.classList.toggle('active');
    });
  }
});