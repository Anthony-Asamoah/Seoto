// Notification Manager
// Owns the "Enable push" control in the notification dropdown header (shared by
// the mobile bottom nav and desktop top nav) and the first-visit opt-in prompt.
//
// Nav control policy: enable-only. It is shown only while push can still be
// turned on; once enabled (or blocked) it hides itself. Turning push OFF lives
// on the profile settings page, which owns its own button entirely.
// The bell icons are pure open/close toggles for the tray — not managed here.

(function() {
  'use strict';

  var supported = ('Notification' in window) && ('PushManager' in window);
  var PROMPTED_KEY = 'seoto_push_prompted';

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

  function storageGet(key) {
    try { return window.localStorage.getItem(key); } catch (e) { return null; }
  }
  function storageSet(key, value) {
    try { window.localStorage.setItem(key, value); } catch (e) { /* private mode */ }
  }

  // ── Dropdown header "Enable push" control (mobile + desktop share one panel) ──
  // Shown only when push is still enable-able; hidden once on, blocked, or
  // unsupported.
  async function updatePushToggle() {
    var btn = document.getElementById('notif-push-toggle');
    if (!btn) return;

    if (!supported || Notification.permission === 'denied') {
      btn.hidden = true;
      return;
    }

    var subscribed = await isSubscribed();
    if (Notification.permission === 'granted' && subscribed) {
      btn.hidden = true; // already on — turn off lives in Settings
      return;
    }

    // 'default', or 'granted' but not yet subscribed → offer to enable
    var label = btn.querySelector('.notif-push-label');
    if (label) label.textContent = 'Enable push';
    btn.disabled = false;
    btn.title = 'Enable push notifications';
    btn.hidden = false;
  }

  async function onPushToggleClick() {
    var btn = document.getElementById('notif-push-toggle');
    if (!btn || !supported) return;
    if (Notification.permission === 'denied') return;

    var label = btn.querySelector('.notif-push-label');
    btn.disabled = true;
    if (label) label.textContent = 'Enabling…';

    try {
      if (Notification.permission === 'granted') {
        // Already granted — just (re)create the subscription, no prompt.
        if (hasPWA('subscribeToPushNotifications')) {
          await window.SeotoPWA.subscribeToPushNotifications();
        }
      } else {
        // 'default' — deliberate opt-in: prompt, then subscribe.
        if (hasPWA('requestNotificationPermission')) {
          await window.SeotoPWA.requestNotificationPermission();
        }
      }
    } catch (error) {
      console.error('Push enable failed:', error);
    } finally {
      btn.disabled = false;
      updatePushToggle(); // hides itself if it succeeded
    }
  }

  // ── First-visit opt-in ──────────────────────────────────────────────────
  // Browsers (Safari, Firefox) require a user gesture for requestPermission, so
  // we ask on the visitor's first interaction rather than on raw page load. Runs
  // once per browser for authenticated users who haven't decided yet.
  function maybeAutoPrompt() {
    if (!supported) return;
    if (!document.getElementById('notif-push-toggle')) return; // authed only
    if (Notification.permission !== 'default') return;
    if (storageGet(PROMPTED_KEY)) return;

    function trigger() {
      document.removeEventListener('pointerdown', trigger, true);
      document.removeEventListener('keydown', trigger, true);
      if (Notification.permission !== 'default') return;
      storageSet(PROMPTED_KEY, '1'); // ask at most once, regardless of choice
      if (hasPWA('requestNotificationPermission')) {
        window.SeotoPWA.requestNotificationPermission();
      }
    }

    document.addEventListener('pointerdown', trigger, true);
    document.addEventListener('keydown', trigger, true);
  }

  // Re-sync backend if a granted permission outlived its subscription
  async function checkSubscriptionStatus() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;

    try {
      var registration = await navigator.serviceWorker.ready;
      var subscription = await registration.pushManager.getSubscription();

      if (subscription && Notification.permission === 'granted') {
        console.log('Push subscription active:', subscription.endpoint);
      } else if (Notification.permission === 'granted' && !subscription) {
        console.log('Re-subscribing to push notifications...');
        if (hasPWA('subscribeToPushNotifications')) {
          await window.SeotoPWA.subscribeToPushNotifications();
        }
      }
    } catch (error) {
      console.error('Failed to check subscription status:', error);
    } finally {
      updatePushToggle();
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    updatePushToggle();
    checkSubscriptionStatus();
    maybeAutoPrompt();

    var pushToggle = document.getElementById('notif-push-toggle');
    if (pushToggle) pushToggle.addEventListener('click', onPushToggleClick);

    // React to permission changes made elsewhere (browser UI, profile page)
    if (navigator.permissions && navigator.permissions.query) {
      navigator.permissions.query({ name: 'notifications' }).then(function (status) {
        status.onchange = function () {
          updatePushToggle();
          checkSubscriptionStatus();
        };
      }).catch(function (error) {
        console.log('Permission query not supported:', error);
      });
    }
  });

  // Keep the nav control in sync after a permission request elsewhere
  if (hasPWA('requestNotificationPermission')) {
    var originalRequestPermission = window.SeotoPWA.requestNotificationPermission;
    window.SeotoPWA.requestNotificationPermission = async function () {
      await originalRequestPermission.apply(this, arguments);
      setTimeout(function () {
        updatePushToggle();
        checkSubscriptionStatus();
      }, 500);
    };
  }

})();
