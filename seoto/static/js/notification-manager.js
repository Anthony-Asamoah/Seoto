// Notification Manager
// Manages notification button state and subscription status

(function() {
  'use strict';

  // Update a single notification button based on permission status
  function updateSingleButton(btn) {
    if (!btn) return;

    // Check if notifications are supported
    if (!('Notification' in window) || !('PushManager' in window)) {
      btn.style.display = 'none';
      return;
    }

    // Reuse or create the icon element (preserve the badge span)
    let icon = btn.querySelector('i');
    if (!icon) {
      icon = document.createElement('i');
      btn.insertBefore(icon, btn.firstChild);
    }

    // Update button based on permission status
    const permission = Notification.permission;

    if (permission === 'granted') {
      icon.className = 'fas fa-bell';
      btn.title = 'Notifications enabled';
      btn.classList.add('text-success');
      btn.classList.remove('text-muted');
      btn.disabled = false;
    } else if (permission === 'denied') {
      icon.className = 'fas fa-bell-slash';
      btn.title = 'Notifications blocked (check browser settings)';
      btn.classList.add('text-muted');
      btn.classList.remove('text-success');
      btn.disabled = true;
    } else {
      icon.className = 'far fa-bell';
      btn.title = 'Enable push notifications';
      btn.classList.remove('text-success', 'text-muted');
      btn.disabled = false;
    }
  }

  // Update all notification buttons (top nav, bottom nav, profile settings)
  function updateNotificationButton() {
    updateSingleButton(document.getElementById('notification-toggle'));
    updateSingleButton(document.getElementById('notification-toggle-bottom'));
    updateSingleButton(document.getElementById('notification-toggle-profile'));
  }

  // Check subscription status and ensure backend is synced
  async function checkSubscriptionStatus() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      return;
    }

    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();

      if (subscription && Notification.permission === 'granted') {
        console.log('Push subscription active:', subscription.endpoint);

        // Optionally verify subscription with backend
        // You could add a GET endpoint to check if subscription exists
      } else if (Notification.permission === 'granted' && !subscription) {
        // Permission granted but no subscription - re-subscribe
        console.log('Re-subscribing to push notifications...');
        if (window.SeotoPWA && typeof window.SeotoPWA.subscribeToPushNotifications === 'function') {
          await window.SeotoPWA.subscribeToPushNotifications();
        }
      }
    } catch (error) {
      console.error('Failed to check subscription status:', error);
    }
  }

  // Initialize on page load
  document.addEventListener('DOMContentLoaded', () => {
    updateNotificationButton();
    checkSubscriptionStatus();

    // Listen for permission changes (if browser supports it)
    if (navigator.permissions && navigator.permissions.query) {
      navigator.permissions.query({ name: 'notifications' }).then((permissionStatus) => {
        permissionStatus.onchange = () => {
          updateNotificationButton();
          checkSubscriptionStatus();
        };
      }).catch((error) => {
        console.log('Permission query not supported:', error);
      });
    }
  });

  // Override the requestNotificationPermission to update button after permission
  if (window.SeotoPWA && typeof window.SeotoPWA.requestNotificationPermission === 'function') {
    const originalRequestPermission = window.SeotoPWA.requestNotificationPermission;

    window.SeotoPWA.requestNotificationPermission = async function() {
      await originalRequestPermission();
      setTimeout(() => {
        updateNotificationButton();
        checkSubscriptionStatus();
      }, 500);
    };
  }

})();