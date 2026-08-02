// Service Worker for Seoto PWA
// Version: 1.3.0

const CACHE_VERSION = 'seoto-v1.3.2';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const DYNAMIC_CACHE = `${CACHE_VERSION}-dynamic`;
const IMAGE_CACHE = `${CACHE_VERSION}-images`;

// Fallback TTL if not served through pwa.views.service_worker (which stamps in
// the real value from settings.CLIENT_CACHE_TTL_SECONDS, env-configurable, default 5 min).
const CACHE_TTL_MS = 300000;

// Exact page paths served straight from cache (no network round-trip) until
// CACHE_TTL_MS has elapsed since they were last fetched.
const CACHEABLE_ROUTES = [
  '/', // Apps screen
];

// accounts.urls registers `<str:username>` last, after these literal paths —
// anything else single-segment under /accounts/ is someone's profile page.
const ACCOUNTS_RESERVED_PATHS = new Set(['register']);

function isCacheableRoute(pathname) {
  if (CACHEABLE_ROUTES.includes(pathname)) {
    return true;
  }
  const accountsMatch = pathname.match(/^\/accounts\/([^/]+)$/);
  return !!accountsMatch && !ACCOUNTS_RESERVED_PATHS.has(accountsMatch[1]);
}

// Static assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/offline/',
  '/manifest.json',
  '/static/img/logo.png',
  '/static/img/pwa/android-chrome-192x192.png',
  '/static/img/pwa/android-chrome-512x512.png',
  // CDN resources
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
  'https://unpkg.com/@popperjs/core@2'
];

// Install Event - Cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...', event);
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .catch((error) => {
        console.error('[SW] Failed to cache static assets:', error);
      })
      .then(() => self.skipWaiting()) // Activate immediately regardless of cache result
  );
});

// Activate Event - Clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...', event);
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName.startsWith('seoto-') &&
                cacheName !== STATIC_CACHE &&
                cacheName !== DYNAMIC_CACHE &&
                cacheName !== IMAGE_CACHE) {
              console.log('[SW] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => self.clients.claim()) // Take control immediately
  );
});

// Fetch Event - Hybrid caching strategy
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip Chrome extension requests
  if (url.protocol === 'chrome-extension:') {
    return;
  }

  // Strategy 1: Cache-first for static assets (CSS, JS, fonts, images)
  if (isStaticAsset(request)) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  // Strategy 2: Cache-first for images with separate cache
  if (request.destination === 'image') {
    event.respondWith(cacheFirst(request, IMAGE_CACHE));
    return;
  }

  const isHtmlRequest = request.headers.get('accept') && request.headers.get('accept').includes('text/html');

  // Strategy 3: TTL cache for configured routes — serve from cache with no
  // network call until the cached copy is older than CACHE_TTL_MS.
  if (isHtmlRequest && isCacheableRoute(url.pathname)) {
    event.respondWith(cacheWithTTL(request, DYNAMIC_CACHE));
    return;
  }

  // Strategy 4: Network-first for HTML pages (with cache fallback)
  if (isHtmlRequest) {
    event.respondWith(networkFirst(request, DYNAMIC_CACHE));
    return;
  }

  // Strategy 5: Network-first for API calls and dynamic content
  event.respondWith(networkFirst(request, DYNAMIC_CACHE));
});

// Helper: Check if request is for static asset
function isStaticAsset(request) {
  const url = new URL(request.url);
  return url.pathname.match(/\.(css|js|woff|woff2|ttf|eot)$/) ||
         url.pathname.startsWith('/static/');
}

// Cache-first strategy: Check cache first, fallback to network
async function cacheFirst(request, cacheName) {
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    console.log('[SW] Cache hit:', request.url);
    return cachedResponse;
  }

  console.log('[SW] Cache miss, fetching:', request.url);
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.error('[SW] Fetch failed:', request.url, error);
    // Return offline page if available
    return caches.match('/offline/');
  }
}

// TTL strategy: Serve from cache with no network call while the cached copy
// is younger than CACHE_TTL_MS; otherwise refetch and re-stamp the cache.
async function cacheWithTTL(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);

  if (cachedResponse) {
    const cachedAt = parseInt(cachedResponse.headers.get('sw-cached-at') || '0', 10);
    if (Date.now() - cachedAt < CACHE_TTL_MS) {
      console.log('[SW] TTL cache hit (fresh):', request.url);
      return cachedResponse;
    }
  }

  console.log('[SW] TTL cache stale/miss, fetching:', request.url);
  try {
    const networkResponse = await fetch(request);
    // Skip redirected responses (e.g. a login-required page bounced to the
    // login form) — caching that under this URL's key would poison it.
    if (networkResponse.ok && !networkResponse.redirected) {
      cache.put(request, await stampWithCacheTime(networkResponse.clone()));
    }
    return networkResponse;
  } catch (error) {
    console.log('[SW] Network failed, falling back to stale TTL cache:', request.url);
    if (cachedResponse) {
      return cachedResponse;
    }
    return caches.match('/offline/');
  }
}

// Clone a response with an added header recording when it was cached, since
// the Cache API itself doesn't track insertion time.
async function stampWithCacheTime(response) {
  const body = await response.blob();
  const headers = new Headers(response.headers);
  headers.set('sw-cached-at', Date.now().toString());
  return new Response(body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

// Network-first strategy: Try network first, fallback to cache
async function networkFirst(request, cacheName) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.log('[SW] Network failed, checking cache:', request.url);
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    // Return offline page for HTML requests
    if (request.headers.get('accept') && request.headers.get('accept').includes('text/html')) {
      return caches.match('/offline/');
    }
    throw error;
  }
}

// Push Notification Event
self.addEventListener('push', (event) => {
  console.log('[SW] Push event fired. Has data:', !!event.data);

  let notificationData = {
    title: 'Seoto',
    body: 'You have a new notification',
    icon: '/static/img/pwa/android-chrome-192x192.png',
    badge: '/static/img/pwa/favicon-32x32.png',
    data: {}
  };

  if (event.data) {
    console.log('[SW] Raw push data text:', event.data.text());
    try {
      const payload = event.data.json();
      console.log('[SW] Parsed payload:', JSON.stringify(payload));
      notificationData = {
        title: payload.title || notificationData.title,
        body: payload.body || notificationData.body,
        icon: payload.icon || notificationData.icon,
        badge: payload.badge || notificationData.badge,
        data: payload.data || {}
      };
    } catch (error) {
      console.error('[SW] Failed to parse push payload as JSON:', error);
    }
  } else {
    console.warn('[SW] Push event had no data — showing default notification');
  }

  console.log('[SW] Showing notification:', JSON.stringify(notificationData));

  event.waitUntil(
    self.registration.showNotification(notificationData.title, {
      body: notificationData.body,
      icon: notificationData.icon,
      badge: notificationData.badge,
      data: notificationData.data,
      vibrate: [200, 100, 200],
      tag: 'seoto-notification',
      requireInteraction: false
    })
    .then(() => {
      console.log('[SW] Notification displayed successfully');
    })
    .catch(error => {
      console.error('[SW] showNotification failed:', error);
    })
  );
});

// Notification Click Event
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event.notification);
  event.notification.close();

  // Navigate to URL if provided in notification data
  const urlToOpen = event.notification.data?.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Check if a window is already open
        for (let client of clientList) {
          if (client.url === urlToOpen && 'focus' in client) {
            return client.focus();
          }
        }
        // Open new window if none exists
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen);
        }
      })
  );
});

// Background Sync Event
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync triggered:', event.tag);

  if (event.tag === 'sync-posts') {
    event.waitUntil(syncPosts());
  } else if (event.tag === 'sync-todos') {
    event.waitUntil(syncTodos());
  } else if (event.tag === 'sync-todo-edits') {
    event.waitUntil(syncTodoEdits());
  } else if (event.tag === 'sync-transactions') {
    event.waitUntil(syncTransactions());
  }
});

// Background sync helper for blog posts
async function syncPosts() {
  try {
    const db = await openIndexedDB();
    const pendingPosts = await getPendingItems(db, 'posts');

    for (let post of pendingPosts) {
      try {
        const response = await fetch('/blog/api/create/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': post.csrfToken
          },
          body: JSON.stringify(post.data)
        });

        if (response.ok) {
          await removePendingItem(db, 'posts', post.id);
          console.log('[SW] Post synced successfully:', post.id);
        }
      } catch (error) {
        console.error('[SW] Failed to sync post:', post.id, error);
      }
    }
  } catch (error) {
    console.error('[SW] Background sync failed:', error);
  }
}

// Background sync helper for todos
async function syncTodos() {
  try {
    const db = await openIndexedDB();
    const pendingTodos = await getPendingItems(db, 'todos');

    for (let todo of pendingTodos) {
      try {
        const response = await fetch('/jotter/api/todo/create/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': todo.csrfToken
          },
          body: JSON.stringify(todo.data)
        });

        if (response.ok) {
          await removePendingItem(db, 'todos', todo.id);
          console.log('[SW] Todo synced successfully:', todo.id);
        }
      } catch (error) {
        console.error('[SW] Failed to sync todo:', todo.id, error);
      }
    }
  } catch (error) {
    console.error('[SW] Background sync failed:', error);
  }
}

// Background sync helper for thetodoapp edits (offline-first with timestamp conflict resolution)
async function syncTodoEdits() {
  try {
    const db = await openIndexedDB();
    const pendingEdits = await getPendingItems(db, 'todo_edits');

    for (let edit of pendingEdits) {
      try {
        const response = await fetch('/jotter/api/todo/update/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': edit.csrfToken
          },
          body: JSON.stringify(edit.data)
        });

        if (response.ok) {
          const result = await response.json();
          if (result.success) {
            // Remove from queue whether saved or rejected (conflict) — no retry benefit
            await removePendingItem(db, 'todo_edits', edit.id);
            if (!result.saved) {
              console.log('[SW] Todo edit rejected (conflict, server version is newer):', edit.id);
            } else {
              console.log('[SW] Todo edit synced successfully:', edit.id);
            }
          }
        }
      } catch (error) {
        console.error('[SW] Failed to sync todo edit:', edit.id, error);
      }
    }
  } catch (error) {
    console.error('[SW] Todo edit background sync failed:', error);
  }
}

// Background sync helper for spending tracker transactions
async function syncTransactions() {
  try {
    const db = await openIndexedDB();
    const pendingTransactions = await getPendingItems(db, 'transactions');

    for (let transaction of pendingTransactions) {
      try {
        const response = await fetch('/spending_tracker/api/transaction/create/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': transaction.csrfToken
          },
          body: JSON.stringify(transaction.data)
        });

        if (response.ok) {
          await removePendingItem(db, 'transactions', transaction.id);
          console.log('[SW] Transaction synced successfully:', transaction.id);
        }
      } catch (error) {
        console.error('[SW] Failed to sync transaction:', transaction.id, error);
      }
    }
  } catch (error) {
    console.error('[SW] Background sync failed:', error);
  }
}

// IndexedDB helpers
function openIndexedDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('SeotoSyncDB', 2);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains('posts')) {
        db.createObjectStore('posts', { keyPath: 'id', autoIncrement: true });
      }
      if (!db.objectStoreNames.contains('todos')) {
        db.createObjectStore('todos', { keyPath: 'id', autoIncrement: true });
      }
      if (!db.objectStoreNames.contains('transactions')) {
        db.createObjectStore('transactions', { keyPath: 'id', autoIncrement: true });
      }
      if (!db.objectStoreNames.contains('todo_edits')) {
        db.createObjectStore('todo_edits', { keyPath: 'id', autoIncrement: true });
      }
    };
  });
}

function getPendingItems(db, storeName) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([storeName], 'readonly');
    const store = transaction.objectStore(storeName);
    const request = store.getAll();

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
  });
}

function removePendingItem(db, storeName, id) {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([storeName], 'readwrite');
    const store = transaction.objectStore(storeName);
    const request = store.delete(id);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
}
