// PWA Install Prompt Handler
// Manages the beforeinstallprompt event and custom install UI

(function() {
  'use strict';

  // Store the deferred prompt for later use
  let deferredPrompt = null;

  // Check if user has previously dismissed the install prompt
  const DISMISS_KEY = 'pwa-install-dismissed';
  const DISMISS_DURATION = 7 * 24 * 60 * 60 * 1000; // 7 days in milliseconds

  // Check if install prompt should be shown
  function shouldShowPrompt() {
    const dismissedTime = localStorage.getItem(DISMISS_KEY);
    if (!dismissedTime) return true;

    const timeSinceDismissal = Date.now() - parseInt(dismissedTime, 10);
    return timeSinceDismissal > DISMISS_DURATION;
  }

  // Save dismissal timestamp
  function markAsDismissed() {
    localStorage.setItem(DISMISS_KEY, Date.now().toString());
  }

  // Show the install button
  function showInstallButton() {
    if (!shouldShowPrompt()) return;

    ['install-button', 'install-button-profile'].forEach(function(id) {
      const btn = document.getElementById(id);
      if (btn) btn.style.display = 'flex';
    });
  }

  // Hide the install button
  function hideInstallButton() {
    ['install-button', 'install-button-profile'].forEach(function(id) {
      const btn = document.getElementById(id);
      if (btn) btn.style.display = 'none';
    });
  }

  // Handle install button click
  async function handleInstallClick() {
    if (!deferredPrompt) {
      console.warn('Install prompt not available');
      return;
    }

    // Show the install prompt
    deferredPrompt.prompt();

    // Wait for the user to respond to the prompt
    const { outcome } = await deferredPrompt.userChoice;

    console.log(`User response to install prompt: ${outcome}`);

    if (outcome === 'dismissed') {
      markAsDismissed();
    }

    // Clear the deferred prompt since it can only be used once
    deferredPrompt = null;
    hideInstallButton();
  }

  // Listen for beforeinstallprompt event
  window.addEventListener('beforeinstallprompt', (e) => {
    // Prevent the default browser install prompt
    e.preventDefault();

    // Store the event for later use
    deferredPrompt = e;

    console.log('beforeinstallprompt event captured - PWA is installable');

    // Show the custom install button
    showInstallButton();
  });

  // Listen for successful app installation
  window.addEventListener('appinstalled', (e) => {
    console.log('PWA was installed successfully');

    // Clear the deferred prompt
    deferredPrompt = null;

    // Hide the install button
    hideInstallButton();

    // Clear dismissal flag since app is now installed
    localStorage.removeItem(DISMISS_KEY);

    // Prompt for notification permission after installation
    setTimeout(() => {
      if (window.SeotoPWA && typeof window.SeotoPWA.requestNotificationPermission === 'function') {
        console.log('Requesting notification permission after PWA installation...');
        window.SeotoPWA.requestNotificationPermission();
      }
    }, 2000); // Wait 2 seconds after installation

    // Optional: Track installation event
    // You can add analytics tracking here if needed
  });

  // Attach click handler when DOM is ready
  window.addEventListener('DOMContentLoaded', () => {
    ['install-button', 'install-button-profile'].forEach(function(id) {
      const btn = document.getElementById(id);
      if (btn) {
        btn.addEventListener('click', handleInstallClick);
      }
    });

    // Also add a close/dismiss button if exists
    const dismissButton = document.getElementById('install-dismiss');
    if (dismissButton) {
      dismissButton.addEventListener('click', () => {
        markAsDismissed();
        hideInstallButton();
      });
    }
  });

  // Check if app is already installed
  if (window.matchMedia('(display-mode: standalone)').matches ||
      window.navigator.standalone === true) {
    console.log('PWA is running in installed mode');
    // App is already installed, no need to show install prompt
    hideInstallButton();
  }

})();
