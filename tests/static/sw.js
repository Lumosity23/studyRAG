/**
 * StudyRAG Service Worker
 * Provides offline support and caching for the application
 */

const CACHE_NAME = 'studyrag-v1';
const STATIC_ASSETS = [
  '/static/',
  '/static/index.html',
  '/static/css/main.css',
  '/static/css/components.css',
  '/static/js/utils.js',
  '/static/js/components.js',
  '/static/js/router.js',
  '/static/js/main.js',
  '/static/assets/favicon.svg'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('Service Worker: Installing...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Service Worker: Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log('Service Worker: Installation complete');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('Service Worker: Installation failed', error);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('Service Worker: Activating...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== CACHE_NAME) {
              console.log('Service Worker: Deleting old cache', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('Service Worker: Activation complete');
        return self.clients.claim();
      })
  );
});

// Fetch event - serve from cache with network fallback
self.addEventListener('fetch', (event) => {
  // Only handle GET requests
  if (event.request.method !== 'GET') {
    return;
  }
  
  // Skip API requests - always go to network
  if (event.request.url.includes('/api/')) {
    return;
  }
  
  event.respondWith(
    caches.match(event.request)
      .then((cachedResponse) => {
        // Return cached version if available
        if (cachedResponse) {
          return cachedResponse;
        }
        
        // Otherwise fetch from network
        return fetch(event.request)
          .then((response) => {
            // Don't cache non-successful responses
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }
            
            // Clone the response for caching
            const responseToCache = response.clone();
            
            // Cache static assets
            if (isStaticAsset(event.request.url)) {
              caches.open(CACHE_NAME)
                .then((cache) => {
                  cache.put(event.request, responseToCache);
                });
            }
            
            return response;
          })
          .catch((error) => {
            console.error('Service Worker: Fetch failed', error);
            
            // Return offline page for navigation requests
            if (event.request.mode === 'navigate') {
              return caches.match('/static/index.html');
            }
            
            throw error;
          });
      })
  );
});

// Helper function to check if URL is a static asset
function isStaticAsset(url) {
  return url.includes('/static/') || 
         url.endsWith('.css') || 
         url.endsWith('.js') || 
         url.endsWith('.svg') || 
         url.endsWith('.png') || 
         url.endsWith('.jpg') || 
         url.endsWith('.ico');
}

// Handle messages from the main thread
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// Background sync for offline actions (if supported)
if ('sync' in self.registration) {
  self.addEventListener('sync', (event) => {
    console.log('Service Worker: Background sync triggered', event.tag);
    
    if (event.tag === 'background-upload') {
      event.waitUntil(handleBackgroundUpload());
    }
  });
}

// Handle background upload sync
async function handleBackgroundUpload() {
  try {
    // Get pending uploads from IndexedDB or localStorage
    // This would be implemented based on your offline storage strategy
    console.log('Service Worker: Processing background uploads');
  } catch (error) {
    console.error('Service Worker: Background upload failed', error);
  }
}

// Push notification handling (if needed in the future)
self.addEventListener('push', (event) => {
  if (event.data) {
    const data = event.data.json();
    
    const options = {
      body: data.body,
      icon: '/static/assets/favicon.svg',
      badge: '/static/assets/favicon.svg',
      vibrate: [100, 50, 100],
      data: {
        dateOfArrival: Date.now(),
        primaryKey: data.primaryKey || 1
      },
      actions: [
        {
          action: 'explore',
          title: 'View Details',
          icon: '/static/assets/favicon.svg'
        },
        {
          action: 'close',
          title: 'Close',
          icon: '/static/assets/favicon.svg'
        }
      ]
    };
    
    event.waitUntil(
      self.registration.showNotification(data.title, options)
    );
  }
});

// Notification click handling
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  
  if (event.action === 'explore') {
    // Open the app
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});