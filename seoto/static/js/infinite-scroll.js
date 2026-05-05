(function () {
    'use strict';

    const SENTINEL_SELECTOR = '[data-infinite-scroll-sentinel]';
    const DEBUG = true;

    function log(...args) {
        if (DEBUG) console.log('[infinite-scroll]', ...args);
    }

    function spinnerHTML(label) {
        return (
            '<div class="d-flex align-items-center justify-content-center gap-2 py-2">' +
            '  <div class="spinner-border spinner-border-sm text-secondary" role="status" aria-hidden="true"></div>' +
            '  <span class="text-muted small">' + (label || 'Loading more…') + '</span>' +
            '</div>'
        );
    }

    function setSpinner(sentinel) {
        sentinel.innerHTML = spinnerHTML();
    }

    function buildUrl(sentinel, page) {
        const base = sentinel.dataset.url || window.location.pathname;
        const params = new URLSearchParams();
        params.set('partial', '1');
        params.set('page', page);

        const extra = sentinel.dataset.extraQuery || '';
        if (extra) {
            const cleaned = extra.replace(/^[?&]+/, '');
            if (cleaned) {
                const extraParams = new URLSearchParams(cleaned);
                extraParams.forEach((value, key) => {
                    if (key !== 'partial' && key !== 'page') {
                        params.set(key, value);
                    }
                });
            }
        }

        return base + (base.indexOf('?') === -1 ? '?' : '&') + params.toString();
    }

    function showError(sentinel, message) {
        sentinel.innerHTML = '';
        const wrap = document.createElement('div');
        wrap.className = 'text-center text-muted small py-2';
        wrap.textContent = message + ' ';
        const retry = document.createElement('button');
        retry.type = 'button';
        retry.className = 'btn btn-sm btn-link p-0';
        retry.textContent = 'Retry';
        retry.addEventListener('click', () => loadNext(sentinel));
        wrap.appendChild(retry);
        sentinel.appendChild(wrap);
    }

    let observer = null;
    const observed = new WeakSet();

    function disconnectSentinel(sentinel) {
        if (observer) observer.unobserve(sentinel);
    }

    function ensureObserver() {
        if (observer) return observer;
        observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                log('intersection', { isIntersecting: entry.isIntersecting, target: entry.target });
                if (entry.isIntersecting) {
                    loadNext(entry.target);
                }
            });
        }, { rootMargin: '200px 0px' });
        return observer;
    }

    function loadNext(sentinel) {
        if (sentinel.dataset.loading === '1') {
            log('skip — already loading', sentinel);
            return;
        }
        const nextPage = sentinel.dataset.nextPage;
        if (!nextPage || nextPage === '0') {
            log('no next page, removing sentinel');
            disconnectSentinel(sentinel);
            sentinel.remove();
            return;
        }

        const targetSelector = sentinel.dataset.target;
        const target = targetSelector ? document.querySelector(targetSelector) : null;
        if (!target) {
            log('target not found', targetSelector);
            sentinel.dataset.loading = '0';
            return;
        }

        sentinel.dataset.loading = '1';
        setSpinner(sentinel);

        const url = buildUrl(sentinel, nextPage);
        log('fetching', url);

        fetch(url, {
            credentials: 'same-origin',
            headers: { 'Accept': 'text/html', 'X-Requested-With': 'XMLHttpRequest' }
        })
            .then((res) => {
                log('response', res.status, 'X-Has-Next:', res.headers.get('X-Has-Next'));
                if (!res.ok) throw new Error('HTTP ' + res.status);
                const hasNext = res.headers.get('X-Has-Next') === '1';
                return res.text().then((html) => ({ html, hasNext }));
            })
            .then(({ html, hasNext }) => {
                log('appending', html.length, 'chars; hasNext:', hasNext);
                target.insertAdjacentHTML('beforeend', html);
                sentinel.dataset.loading = '0';

                if (hasNext) {
                    sentinel.dataset.nextPage = String(parseInt(nextPage, 10) + 1);
                    sentinel.innerHTML = spinnerHTML('Scroll for more');
                    // Re-observe so that if the sentinel is *still* intersecting after
                    // the append (e.g. content shorter than viewport), we get another tick.
                    disconnectSentinel(sentinel);
                    observed.delete(sentinel);
                    requestAnimationFrame(() => {
                        observed.add(sentinel);
                        ensureObserver().observe(sentinel);
                    });
                } else {
                    disconnectSentinel(sentinel);
                    sentinel.remove();
                }
                scan();
            })
            .catch((err) => {
                log('fetch error', err);
                sentinel.dataset.loading = '0';
                showError(sentinel, 'Could not load more.');
            });
    }

    function scan() {
        const obs = ensureObserver();
        const sentinels = document.querySelectorAll(SENTINEL_SELECTOR);
        log('scan found', sentinels.length, 'sentinels');
        sentinels.forEach((s) => {
            const next = s.dataset.nextPage;
            if (!next || next === '0') {
                s.remove();
                return;
            }
            if (!observed.has(s)) {
                observed.add(s);
                obs.observe(s);
                log('observing sentinel', { nextPage: next, target: s.dataset.target, url: s.dataset.url });
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', scan);
    } else {
        scan();
    }

    window.InfiniteScroll = { scan, _loadNext: loadNext };
})();
