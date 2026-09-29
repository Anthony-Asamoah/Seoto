(function () {
    var reveal = document.getElementById('otpReveal');
    if (!reveal) return;
    var form = reveal.closest('form');
    var username = form.elements.username;
    var token = form.elements.otp_token;
    var note = document.getElementById('passkeyOnlyNote');
    var lastChecked = null;

    function apply(result) {
        reveal.classList.toggle('is-open', result.code);
        if (note) note.hidden = !result.passkey_only;
        if (!result.code) token.value = '';
        token.tabIndex = result.code ? 0 : -1;
    }

    function lookup() {
        var name = username.value.trim();
        if (!name || name === lastChecked) return;
        lastChecked = name;
        var body = new FormData();
        body.append('username', name);
        fetch(reveal.dataset.url, {
            method: 'POST',
            body: body,
            credentials: 'same-origin',
            headers: {'X-CSRFToken': form.elements.csrfmiddlewaretoken.value},
        }).then(function (r) { return r.ok ? r.json() : null; })
          .then(function (result) { if (result && name === username.value.trim()) apply(result); })
          .catch(function () { lastChecked = null; });
    }

    if (!reveal.classList.contains('is-open')) token.tabIndex = -1;
    username.addEventListener('blur', lookup);
    username.addEventListener('change', lookup);
    username.addEventListener('input', function () {
        if (username.value.trim() !== lastChecked) apply({code: false, passkey_only: false});
    });
    if (username.value) lookup();
})();
