// Notification Manager
// Manages notification button state and subscription status

(function() {
  'use strict';

  // Update notification button based on permission status
  function updateNotificationButton() {
    const notificationToggle = document.getElementById('notification-toggle');
    if (!notificationToggle) return;

    // Check if notifications are supported
    if (!('Notification' in window) || !('PushManager' in window)) {
      notificationToggle.style.display = 'none';
      return;
    }

    // Update button based on permission status
    const permission = Notification.permission;

    if (permission === 'granted') {
      notificationToggle.innerHTML = '<i class="fas fa-bell"></i>';
      notificationToggle.title = 'Notifications enabled';
      notificationToggle.classList.add('text-success');
      notificationToggle.classList.remove('text-muted');
    } else if (permission === 'denied') {
      notificationToggle.innerHTML = '<i class="fas fa-bell-slash"></i>';
      notificationToggle.title = 'Notifications blocked (check browser settings)';
      notificationToggle.classList.add('text-muted');
      notificationToggle.classList.remove('text-success');
      notificationToggle.disabled = true;
    } else {
      notificationToggle.innerHTML = '<i class="far fa-bell"></i>';
      notificationToggle.title = 'Enable push notifications';
      notificationToggle.classList.remove('text-success', 'text-muted');
    }
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