// Retire earlier ANT PWA caches without touching saved notes or browser storage.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter(name => name.startsWith('ant-cache-')).map(name => caches.delete(name)));
    await self.clients.claim();
    await self.registration.unregister();
  })());
});
