// CSRF token freshness
//
// `{% csrf_token %}` bakes the token into the HTML when the page is rendered, but
// the cookie is what the server checks against, and its secret is rotated on every
// login/logout. Any HTML the browser still holds from before a rotation — a page the
// service worker served from cache, a tab left open for hours, a bfcache restore —
// therefore carries a dead token and its next POST is rejected with a 403.
//
// The cookie, unlike the HTML, is always current. So sync every rendered token from
// the cookie at submit time, the same way pwa.js already does for its fetch() calls.

(function () {
  'use strict';

  function getCsrfToken() {
    var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  // Django only renders csrfmiddlewaretoken into same-origin forms, but a form's
  // action can still be rewritten to point elsewhere — never hand the token over.
  function isSameOrigin(url) {
    if (!url) return true; // empty action posts back to the current URL
    try {
      return new URL(url, window.location.href).origin === window.location.origin;
    } catch (error) {
      return false;
    }
  }

  function refreshFormToken(form) {
    if (!form || !isSameOrigin(form.getAttribute('action'))) return;

    var token = getCsrfToken();
    if (!token) return; // no cookie to trust; leave the rendered value alone

    var inputs = form.querySelectorAll('input[name="csrfmiddlewaretoken"]');
    for (var i = 0; i < inputs.length; i++) {
      if (inputs[i].value !== token) {
        inputs[i].value = token;
      }
    }
  }

  // Capture phase, so the token is current even if another submit handler stops
  // propagation or submits the form itself.
  document.addEventListener('submit', function (event) {
    refreshFormToken(event.target);
  }, true);

  // fetch() wrapper that reads the token at call time instead of page-render time,
  // and retries once against a fresh cookie if the server still says it is stale
  // (see home.views.error_handlers.csrf_failure, which re-issues the cookie).
  async function csrfFetch(url, options) {
    var config = Object.assign({}, options);
    config.headers = new Headers(config.headers || {});
    config.credentials = config.credentials || 'same-origin';
    config.headers.set('X-CSRFToken', getCsrfToken());

    var response = await fetch(url, config);
    if (response.status !== 403) return response;

    var body = await response.clone().json().catch(function () { return {}; });
    if (body.error !== 'csrf_failure') return response;

    var refreshed = getCsrfToken();
    if (!refreshed || refreshed === config.headers.get('X-CSRFToken')) return response;

    config.headers.set('X-CSRFToken', refreshed);
    return fetch(url, config);
  }

  window.getCsrfToken = getCsrfToken;
  window.csrfFetch = csrfFetch;
})();
