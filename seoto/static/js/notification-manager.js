// Notification Manager
// Owns the "push" control in the notification dropdown header (shared by the
// mobile bottom nav and desktop top nav) and the initial state of the profile
// settings button. The bell icons themselves are pure open/close toggles for
// the in-app notification tray — they are NOT managed here.

(function() {
  'use strict';

  var supported = ('Notification' in window) && ('PushManager' in window);

  function hasPWA(method) {
    return window.SeotoPWA && typeof window.SeotoPWA[method] === 'function';
  }

  // Is there an active push subscription? (Resolves false if SW unavailable.)
  async function isSubscribed() {
    if (!('serviceWorker' in navigator)) return false;
    try {
      var registration = await navigator.serviceWorker.ready;
      return !!(await registration.pushManager.getSubscription());
    } catch (error) {
      return false;
    }
  }

  // ── Profile settings button ────────────────────────────────────────────
  // The click behaviour lives in profile.html; here we only reflect the
  // current permission in the icon on page load.
  function updateProfileButton() {
    var btn = document.getElementById('notification-toggle-profile');
    if (!btn) return;
    if (!supported) { btn.style.display = 'none'; return; }

    var icon = btn.querySelector('i');
    var permission = Notification.permission;

    if (permission === 'granted') {
      if (icon) icon.className = 'fas fa-bell';
      btn.title = 'Notifications enabled';
    } else if (permission === 'denied') {
      if (icon) icon.className = 'fas fa-bell-slash';
      btn.title = 'Notifications blocked (check browser settings)';
    } else {
      if (icon) icon.className = 'far fa-bell';
      btn.title = 'Enable push notifications';
    }
  }

  // ── Dropdown header push control (mobile + desktop share one panel) ─────
  async function updatePushToggle() {
    var btn = document.getElementById('notif-push-toggle');
    if (!btn) return;
    if (!supported) { btn.hidden = true; return; }

    var icon = btn.querySelector('i');
    var label = btn.querySelector('.notif-push-label');
    var permission = Notification.permission;

    btn.hidden = false;
    btn.disabled = false;
    btn.classList.remove('is-on', 'is-blocked');

    if (permission === 'denied') {
      if (icon) icon.className = 'fas fa-bell-slash';
      if (label) label.textContent = 'Blocked';
      btn.classList.add('is-blocked');
      btn.disabled = true;
      btn.title = 'Push is blocked — enable it in your browser settings';
      return;
    }

    var subscribed = await isSubscribed();

    if (permission === 'granted' && subscribed) {
      if (icon) icon.className = 'fas fa-bell';
      if (label) label.textContent = 'Push on';
      btn.classList.add('is-on');
      btn.title = 'Push notifications are on — tap to turn off';
    } else {
      // 'default', or 'granted' but not yet subscribed
      if (icon) icon.className = 'far fa-bell';
      if (label) label.textContent = 'Enable push';
      btn.title = 'Enable push notifications';
    }
  }

  async function onPushToggleClick() {
    var btn = document.getElementById('notif-push-toggle');
    if (!btn || !supported) return;
    if (Notification.permission === 'denied') return; // disabled anyway

    var label = btn.querySelector('.notif-push-label');
    btn.disabled = true;

    try {
      var subscribed = await isSubscribed();

      if (Notification.permission === 'granted' && subscribed) {
        if (label) label.textContent = 'Turning off…';
        if (hasPWA('unsubscribeFromPushNotifications')) {
          await window.SeotoPWA.unsubscribeFromPushNotifications();
        }
      } else if (Notification.permission === 'granted') {
        // Already granted — just (re)create the subscription, no prompt.
        if (label) label.textContent = 'Enabling…';
        if (hasPWA('subscribeToPushNotifications')) {
          await window.SeotoPWA.subscribeToPushNotifications();
        }
      } else {
        // 'default' — this is the deliberate opt-in: prompt, then subscribe.
        if (label) label.textContent = 'Enabling…';
        if (hasPWA('requestNotificationPermission')) {
          await window.SeotoPWA.requestNotificationPermission();
        }
      }
    } catch (error) {
      console.error('Push toggle failed:', error);
    } finally {
      btn.disabled = false;
      updatePushToggle();
    }
  }

  function refreshAll() {
    updateProfileButton();
    updatePushToggle();
  }

  // Check subscription status and re-sync backend if permission outlived it
  async function checkSubscriptionStatus() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;

    try {
      var registration = await navigator.serviceWorker.ready;
      var subscription = await registration.pushManager.getSubscription();

      if (subscription && Notification.permission === 'granted') {
        console.log('Push subscription active:', subscription.endpoint);
      } else if (Notification.permission === 'granted' && !subscription) {
        // Permission granted but no subscription — re-subscribe
        console.log('Re-subscribing to push notifications...');
        if (hasPWA('subscribeToPushNotifications')) {
          await window.SeotoPWA.subscribeToPushNotifications();
        }
      }
    } catch (error) {
      console.error('Failed to check subscription status:', error);
    }
  }

  // Initialize on page load
  document.addEventListener('DOMContentLoaded', function () {
    refreshAll();
    checkSubscriptionStatus();

    var pushToggle = document.getElementById('notif-push-toggle');
    if (pushToggle) pushToggle.addEventListener('click', onPushToggleClick);

    // React to permission changes made elsewhere (e.g. browser UI)
    if (navigator.permissions && navigator.permissions.query) {
      navigator.permissions.query({ name: 'notifications' }).then(function (status) {
        status.onchange = function () {
          refreshAll();
          checkSubscriptionStatus();
        };
      }).catch(function (error) {
        console.log('Permission query not supported:', error);
      });
    }
  });

  // Keep the controls in sync after the profile page triggers a permission request
  if (hasPWA('requestNotificationPermission')) {
    var originalRequestPermission = window.SeotoPWA.requestNotificationPermission;
    window.SeotoPWA.requestNotificationPermission = async function () {
      await originalRequestPermission.apply(this, arguments);
      setTimeout(function () {
        refreshAll();
        checkSubscriptionStatus();
      }, 500);
    };
  }

})();
