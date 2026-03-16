// PWA Registration and Management
// Handles service worker registration, push notifications, and background sync

(function() {
  'use strict';

  // Check if service workers are supported
  if (!('serviceWorker' in navigator)) {
    console.warn('Service Workers not supported in this browser');
    return;
  }

  // Register service worker on page load
  window.addEventListener('load', () => {
    registerServiceWorker();
  });

  // Register the service worker
  async function registerServiceWorker() {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js', {
        scope: '/'
      });

      console.log('Service Worker registered successfully:', registration.scope);

      // Check for updates every hour
      setInterval(() => {
        registration.update();
      }, 60 * 60 * 1000);

      // Listen for service worker updates
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        console.log('New Service Worker found, installing...');

        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            // New service worker installed, show update notification
            showUpdateNotification();
          }
        });
      });

      // Initialize push notifications if user previously subscribed
      initializePushNotifications(registration);

    } catch (error) {
      console.error('Service Worker registration failed:', error);
    }
  }

  // Show update notification to user
  function showUpdateNotification() {
    if (confirm('A new version of Seoto is available. Reload to update?')) {
      window.location.reload();
    }
  }

  // Initialize push notifications
  async function initializePushNotifications(registration) {
    // Check if notifications are supported
    if (!('Notification' in window)) {
      console.warn('Notifications not supported in this browser');
      return;
    }

    // Check if push is supported
    if (!('PushManager' in window)) {
      console.warn('Push notifications not supported in this browser');
      return;
    }

    // Check current permission status
    if (Notification.permission === 'granted') {
      // User has already granted permission, ensure subscription exists
      const subscription = await registration.pushManager.getSubscription();
      if (subscription) {
        console.log('Push subscription active:', subscription.endpoint);
      }
    }
  }

  // Request push notification permission
  async function requestNotificationPermission() {
    const permission = await Notification.requestPermission();
    if (permission === 'granted') {
      console.log('Notification permission granted');
      await subscribeToPushNotifications();
    } else {
      console.log('Notification permission denied');
    }
  }

  // Subscribe to push notifications
  async function subscribeToPushNotifications() {
    try {
      const registration = await navigator.serviceWorker.ready;

      // Fetch VAPID public key from server
      const response = await fetch('/api/push/vapid-public-key/');
      const { publicKey } = await response.json();

      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey)
      });

      console.log('Push subscription created:', subscription);

      // Send subscription to server
      const saveResponse = await fetch('/api/push/subscribe/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(subscription)
      });

      if (!saveResponse.ok) {
        console.error('Failed to save push subscription to server:', saveResponse.status);
        // Unsubscribe from push manager since server didn't save it
        await subscription.unsubscribe();
        return;
      }

      console.log('Push subscription saved to server');
    } catch (error) {
      console.error('Failed to subscribe to push notifications:', error);
    }
  }

  // Unsubscribe from push notifications
  async function unsubscribeFromPushNotifications() {
    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();

      if (subscription) {
        await subscription.unsubscribe();

        // Remove subscription from server
        await fetch('/api/push/unsubscribe/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
          },
          body: JSON.stringify({ endpoint: subscription.endpoint })
        });

        console.log('Unsubscribed from push notifications');
      }
    } catch (error) {
      console.error('Failed to unsubscribe from push notifications:', error);
    }
  }

  // Queue data for background sync
  async function queueForSync(storeName, data, csrfToken) {
    try {
      const db = await openIndexedDB();
      await addPendingItem(db, storeName, { data, csrfToken });

      // Request background sync
      const registration = await navigator.serviceWorker.ready;
      const tag = `sync-${storeName}`;
      await registration.sync.register(tag);

      console.log(`Queued for background sync: ${storeName}`);
      return true;
    } catch (error) {
      console.error('Failed to queue for sync:', error);
      return false;
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

  function addPendingItem(db, storeName, item) {
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      const request = store.add(item);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
    });
  }

  // Utility: Convert VAPID key
  function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/\-/g, '+')
      .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  // Utility: Get CSRF token from cookies
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  // Expose public API
  window.SeotoPWA = {
    requestNotificationPermission,
    subscribeToPushNotifications,
    unsubscribeFromPushNotifications,
    queueForSync
  };

})();
