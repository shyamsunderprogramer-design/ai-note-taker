/**
 * Service Worker for ANT (AI Note Taker) PWA
 * Provides offline capability and caching
 */

const CACHE_VERSION = 'v4';
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
  '/js/core/auth-helper.js',
  '/js/inline/platform-class.js',
  '/js/inline/sw-register.js'
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
          .filter((name) => name.startsWith('ant-cache-') && name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// Cache only known public assets. API responses must never enter Cache Storage.
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  const isStatic = STATIC_ASSETS.includes(url.pathname) ||
    /^\/(?:assets|js|css)\/.*\.(?:js|css|png|jpe?g|svg|webp|woff2?|ttf)$/.test(url.pathname);
  if (request.method !== 'GET' || url.origin !== self.location.origin ||
      request.headers.has('Authorization') || !isStatic) return;

  // Network first ensures deployments refresh unversioned scripts and HTML.
  // Match the complete URL so one script version cannot satisfy another.
  event.respondWith((async () => {
    try {
      const response = await fetch(request);
      if (response.status === 200 && response.type === 'basic' &&
          !/no-store|private/i.test(response.headers.get('Cache-Control') || '')) {
        const copy = response.clone();
        event.waitUntil(caches.open(CACHE_NAME)
          .then(cache => cache.put(request, copy))
          .catch(err => console.warn('[SW] Cache write failed:', err)));
      }
      return response;
    } catch (err) {
      const cache = await caches.open(CACHE_NAME);
      const cached = await cache.match(request);
      // Never return HTML for a missing script, stylesheet, or API request.
      return cached || Response.error();
    }
  })());
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
