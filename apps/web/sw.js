/**
 * Service Worker for ANT (AI Note Taker) PWA
 * Provides offline capability and caching
 */

const CACHE_VERSION = 'v3';
const CACHE_NAME = 'ant-cache-' + CACHE_VERSION;
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/style.css',
  '/app.js',
  '/manifest.json',
  '/hljs.min.js',
  '/hljs-github-dark.min.css',
  '/js/core/config.js',
  '/js/core/api.js',
  '/js/core/auth-helper.js'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .catch((err) => {
        console.error('[SW] Cache failed:', err);
      })
  );
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Skip API calls - don't cache these
  // Also skip requests to the cloud backend (Render)
  var CLOUD_BACKEND = 'ai-note-taker-7xvn.onrender.com';
  if (url.pathname.startsWith('/api/') ||
      url.hostname === '127.0.0.1' ||
      url.port === '8000' ||
      url.hostname === CLOUD_BACKEND) {
    return;
  }

  event.respondWith(
    caches.match(request)
      .then((cached) => {
        if (cached) {
          // Return cached version
          return cached;
        }

        // Fetch from network
        return fetch(request)
          .then((response) => {
            // Cache successful responses
            if (response.status === 200 &&
                response.type === 'basic') {
              const responseClone = response.clone();
              caches.open(CACHE_NAME)
                .then((cache) => cache.put(request, responseClone));
            }
            return response;
          })
          .catch((err) => {
            console.error('[SW] Fetch failed:', err);
            // Return offline page if available
            return caches.match('/index.html');
          });
      })
  );
});

// Background sync for offline form submissions
self.addEventListener('sync', (event) => {
  if (event.tag === 'background-sync') {
    console.log('[SW] Background sync triggered');
  }
});

// Push notification support
self.addEventListener('push', (event) => {
  const options = {
    body: event.data?.text() || 'New notification',
    icon: '/icon-192x192.png',
    badge: '/icon-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      url: '/'
    }
  };

  event.waitUntil(
    self.registration.showNotification('AI Note Taker', options)
  );
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow(event.notification.data?.url || '/')
  );
});
