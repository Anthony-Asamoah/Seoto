/*
 * Click a word, get its dictionary entry in a panel below it.
 *
 * Definitions come from dictionaryapi.dev, straight from the browser — no key,
 * no server round-trip. Responses are cached per page for the session, and the
 * service worker's network-first rule caches them across visits too, so a word
 * looked up once still opens when offline.
 *
 * Usage: WordDefinitions.attach(container, itemSelector) — delegated, so it
 * keeps working when the results are re-rendered.
 */
(function (window, document) {
    'use strict';

    const ENDPOINT = 'https://api.dictionaryapi.dev/api/v2/entries/en/';
    // Fallback for the words the first dictionary has never heard of. It is
    // WordNet/Wiktionary-derived, so it covers the dialect and archaic entries
    // a word-game list is full of ("glime", "kation").
    const FALLBACK = 'https://api.datamuse.com/words?md=dp&max=1&sp=';
    const WIKTIONARY = 'https://en.wiktionary.org/wiki/';
    const PARTS_OF_SPEECH = {n: 'noun', v: 'verb', adj: 'adjective', adv: 'adverb'};
    const MAX_SENSES = 4;
    const cache = new Map();

    // The richer source, but it 502s often enough (~10% in testing) that a
    // failure is not worth retrying — the fallback is quicker and steadier.
    function request(key) {
        return fetch(ENDPOINT + encodeURIComponent(key)).then(function (response) {
            if (response.status === 404) throw new Error('not-found');
            if (!response.ok) throw new Error('failed');
            return response.json();
        });
    }

    function fallbackLookup(key) {
        return fetch(FALLBACK + encodeURIComponent(key))
            .then(function (response) {
                if (!response.ok) throw new Error('failed');
                return response.json();
            })
            .then(function (results) {
                const match = (results || [])[0];
                if (!match || match.word.toLowerCase() !== key || !match.defs) {
                    throw new Error('not-found');
                }
                return [{
                    word: match.word,
                    source: 'Datamuse',
                    meanings: match.defs.map(function (entry) {
                        const split = entry.split('\t');
                        return {
                            partOfSpeech: PARTS_OF_SPEECH[split[0]] || '',
                            definitions: [{definition: (split[1] || split[0]).trim()}]
                        };
                    })
                }];
            });
    }

    function lookup(word) {
        const key = word.toLowerCase();
        if (cache.has(key)) return cache.get(key);

        const pending = request(key)
            .catch(function () {
                return fallbackLookup(key); // unknown word, or the first dictionary is down
            })
            .catch(function (error) {
                if (error.message !== 'not-found') cache.delete(key); // let a retry try again
                throw error;
            });

        cache.set(key, pending);
        return pending;
    }

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text) node.textContent = text; // never innerHTML: this is third-party text
        return node;
    }

    function buildSenses(entries) {
        const body = el('div', 'definition-body');
        let shown = 0;

        entries.forEach(function (entry) {
            (entry.meanings || []).forEach(function (meaning) {
                (meaning.definitions || []).forEach(function (sense) {
                    if (shown >= MAX_SENSES || !sense.definition) return;
                    shown += 1;

                    const item = el('div', 'definition-sense');
                    item.appendChild(el('span', 'definition-pos', meaning.partOfSpeech || ''));
                    item.appendChild(el('p', 'definition-text', sense.definition));

                    if (sense.example) {
                        item.appendChild(el('p', 'definition-example', '“' + sense.example + '”'));
                    }

                    const synonyms = (sense.synonyms || []).concat(meaning.synonyms || []);
                    if (synonyms.length) {
                        item.appendChild(el(
                            'p', 'definition-synonyms',
                            'similar: ' + synonyms.slice(0, 6).join(', ')
                        ));
                    }
                    body.appendChild(item);
                });
            });
        });

        if (!shown) body.appendChild(el('p', 'definition-text', 'No definition found.'));
        return body;
    }

    function buildPanel(word) {
        const panel = el('li', 'definition-panel');
        panel.setAttribute('role', 'presentation');

        const card = el('div', 'definition-card');
        const head = el('div', 'definition-head');
        head.appendChild(el('span', 'definition-word', word));
        head.appendChild(el('span', 'definition-phonetic', ''));

        const close = el('button', 'definition-close', '×');
        close.type = 'button';
        close.setAttribute('aria-label', 'Close definition');
        head.appendChild(close);

        card.appendChild(head);
        card.appendChild(el('div', 'definition-body definition-loading', 'Looking it up…'));
        panel.appendChild(card);
        return panel;
    }

    function wiktionaryLink(word, label) {
        const link = el('a', 'definition-link', label);
        link.href = WIKTIONARY + encodeURIComponent(word.toLowerCase());
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        return link;
    }

    function fill(panel, word, entries) {
        const card = panel.querySelector('.definition-card');
        const phonetic = (entries.find(function (entry) { return entry.phonetic; }) || {}).phonetic;
        if (phonetic) card.querySelector('.definition-phonetic').textContent = phonetic;

        const body = buildSenses(entries);
        const credit = el('p', 'definition-credit', '');
        credit.appendChild(wiktionaryLink(word, 'More on Wiktionary ↗'));
        body.appendChild(credit);

        card.replaceChild(body, card.querySelector('.definition-body'));
    }

    function fail(panel, word, error) {
        const card = panel.querySelector('.definition-card');
        const missing = error && error.message === 'not-found';
        const body = el('div', 'definition-body');
        body.appendChild(el('p', 'definition-text', missing
            ? 'Neither dictionary has an entry for this one.'
            : 'The dictionaries did not answer. Tap the word again to retry.'));

        // Never a dead end — Wiktionary itself is the last resort.
        const credit = el('p', 'definition-credit', '');
        credit.appendChild(wiktionaryLink(word, 'Look it up on Wiktionary ↗'));
        body.appendChild(credit);

        card.replaceChild(body, card.querySelector('.definition-body'));
    }

    function attach(container, itemSelector) {
        if (!container) return;

        function closeOpen() {
            const open = container.querySelector('.definition-panel');
            if (open) open.remove();
            container.querySelectorAll('[aria-expanded="true"]').forEach(function (item) {
                item.setAttribute('aria-expanded', 'false');
            });
        }

        function toggle(item) {
            const wasOpen = item.getAttribute('aria-expanded') === 'true';
            closeOpen();
            if (wasOpen) return;

            const word = item.textContent.trim();
            const panel = buildPanel(word);
            item.setAttribute('aria-expanded', 'true');
            item.insertAdjacentElement('afterend', panel);

            lookup(word).then(
                function (entries) { fill(panel, word, entries); },
                function (error) { fail(panel, word, error); }
            );
        }

        container.addEventListener('click', function (event) {
            if (event.target.closest('.definition-close')) {
                closeOpen();
                return;
            }
            const item = event.target.closest(itemSelector);
            if (item && container.contains(item)) toggle(item);
        });

        container.addEventListener('keydown', function (event) {
            const item = event.target.closest(itemSelector);
            if (!item || (event.key !== 'Enter' && event.key !== ' ')) return;
            event.preventDefault();
            toggle(item);
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') closeOpen();
        });
    }

    function prepare(item) {
        item.setAttribute('role', 'button');
        item.setAttribute('tabindex', '0');
        item.setAttribute('aria-expanded', 'false');
    }

    window.WordDefinitions = {attach: attach, prepare: prepare};
})(window, document);
