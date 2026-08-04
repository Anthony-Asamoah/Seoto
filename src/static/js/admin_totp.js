/* Drives the "Set up 2FA" button on the User change page.

   The server owns every step: it renders the modal body (QR, secret, backup codes) and
   answers verify/email as JSON, so this file only moves HTML around. Reset confirmation is
   done inside the modal rather than with window.confirm(), which would block the page.

   Depends on window.csrfFetch from csrf.js — both are pulled in by CustomUserAdmin.Media. */
(function () {
    var modal = null;

    function body() {
        return document.getElementById('totpSetupBody');
    }

    function button() {
        return document.getElementById('totp-setup-btn');
    }

    function show() {
        var element = document.getElementById('totpSetupModal');
        if (!modal) {
            modal = new bootstrap.Modal(element);
        }
        modal.show();
    }

    function say(text, ok) {
        var target = document.getElementById('totp-message');
        if (!target) {
            return;
        }
        target.className = 'mt-3 alert ' + (ok ? 'alert-success' : 'alert-danger');
        target.textContent = text;
    }

    /* Name the failure rather than blaming the network for all of them — a 404 means the
       server is running old code, a 403 means CSRF, and a redirect means the session died. */
    function explain(response) {
        if (response.redirected || response.url.indexOf('/login/') !== -1) {
            return 'Your admin session expired. Reload the page and sign in again.';
        }
        if (response.status === 404) {
            return 'Endpoint not found (404) — the server may be running older code. Restart it.';
        }
        if (response.status === 403) {
            return 'Refused (403). Either the CSRF token is stale — reload the page — or you lack permission to change users.';
        }
        return 'The server returned ' + response.status + ' ' + response.statusText + '.';
    }

    function alertHtml(message) {
        var node = document.createElement('div');
        node.className = 'alert alert-danger mb-0';
        node.textContent = message;
        return node.outerHTML;
    }

    function send(url, extra) {
        var payload = new FormData();
        Object.keys(extra || {}).forEach(function (key) {
            payload.append(key, extra[key]);
        });
        if (typeof window.csrfFetch !== 'function') {
            return Promise.reject(new Error('csrf.js did not load, so the request cannot be signed.'));
        }
        return window.csrfFetch(url, {method: 'POST', body: payload});
    }

    function open(extra) {
        body().innerHTML = '<p class="text-muted mb-0">Working…</p>';
        show();

        send(button().dataset.url, extra)
            .then(function (response) {
                if (!response.ok || response.redirected) {
                    throw new Error(explain(response));
                }
                return response.text();
            })
            .then(function (html) {
                body().innerHTML = html;
            })
            .catch(function (error) {
                body().innerHTML = alertHtml(error.message || 'Could not reach the server.');
            });
    }

    function post(url, extra, onDone) {
        send(url, extra)
            .then(function (response) {
                if (!response.ok || response.redirected) {
                    throw new Error(explain(response));
                }
                return response.json();
            })
            .then(function (data) {
                say(data.message, data.ok);
                if (data.ok && onDone) {
                    onDone();
                }
            })
            .catch(function (error) {
                say(error.message || 'Could not reach the server.', false);
            });
    }

    document.addEventListener('click', function (event) {
        var trigger = button();
        if (!trigger) {
            return;
        }

        if (event.target.closest('#totp-setup-btn')) {
            event.preventDefault();
            open();
            return;
        }

        if (event.target.closest('#totp-confirm-reset')) {
            open({confirm: '1'});
            return;
        }

        if (event.target.closest('#totp-verify')) {
            var code = document.getElementById('totp-code');
            post(trigger.dataset.verifyUrl, {code: code.value.trim()}, function () {
                code.value = '';
                document.getElementById('totp-verify').disabled = true;
            });
            return;
        }

        if (event.target.closest('#totp-email')) {
            post(trigger.dataset.emailUrl, {});
        }
    });
})();
