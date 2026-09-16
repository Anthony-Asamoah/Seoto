/* Assignment rows: picking a position fills the salary and currency from that position's
   reference figures. Only empty fields are touched, so a typed-in salary survives. */
(function () {
    'use strict';

    function siblingBySuffix(select, suffix) {
        // Inline rows are prefixed (`assignments-0-position`); the standalone form is not.
        const name = select.name === 'position'
            ? suffix.slice(1)
            : select.name.replace(/-position$/, suffix);
        return document.querySelector('[name="' + name + '"]');
    }

    function setCurrency(select, value) {
        select.value = value;
        // jazzmin runs select2 over plain selects and does so with its own jQuery copy, so a
        // django.jQuery trigger never reaches it. A native event reaches every jQuery on the page.
        select.dispatchEvent(new Event('change', {bubbles: true}));
    }

    function applyDefaults(select) {
        const url = select.dataset.defaultsUrl;
        if (!url || !select.value) return;

        const salary = siblingBySuffix(select, '-salary');
        const currency = siblingBySuffix(select, '-currency');
        if (salary && salary.value.trim()) return;

        fetch(url + '?position=' + encodeURIComponent(select.value), {credentials: 'same-origin'})
            .then(response => (response.ok ? response.json() : null))
            .then(data => {
                if (!data) return;
                if (salary && data.salary) salary.value = data.salary;
                if (currency && data.currency) setCurrency(currency, data.currency);
            })
            .catch(() => {});
    }

    function listen() {
        // select2 fires jQuery events, so the handler has to be bound through django.jQuery.
        const $ = window.django && window.django.jQuery;
        if (!$) return;
        $(document).on('change', 'select[data-defaults-url]', function () {
            applyDefaults(this);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', listen);
    } else {
        listen();
    }
})();
