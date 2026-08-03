"""
Profanity screening built on `better-profanity`.

The library ships an English wordlist; we extend it with common profane /
vulgar words in Ghanaian languages (Twi/Akan, Ga, Ewe) — plus a few anglicised
spellings — so the filter catches local-language abuse too.

The list is intentionally explicit and editable. Note that a few entries (e.g.
anatomical terms, "aboa" = animal) can appear in ordinary speech, so this trades
a little false-positive risk for broader coverage; prune/extend as needed.
"""
from better_profanity import profanity

# ── Twi / Akan ──
_TWI = [
    'kwasea', 'kwasia', 'kwaseani', 'kwasiani', 'gyimii', 'gyimi', 'gyimifo',
    'gyimifoɔ', 'aboa', 'aboayɛ', 'bonsam', 'ɔbonsam', 'tweaa', 'twea',
    'kɔte', 'kote', 'kɔteɛ', 'etwie', 'etwe', 'twɛ', '3tw3', 'tw3', 'twɛboɔ', 'tweaboa',
    'kwasebɔ', 'wo maame', 'womaame', 'wo maame twɛ', 'wo na', 'aboa ba',
]

# ── Ga ──
_GA = [
    'oshwila', 'oshwala', 'gbonyo', 'fɔŋ', 'fong', 'kojo besia', 'tɔɔ',
    'kɛkɛ', 'naa fio', 'yɛ', 'jwɛ',
]

# ── Ewe ──
_EWE = [
    'aɖaba', 'bawu', 'tsɛ', 'gbɔ̃', 'gbɔ', 'aha', 'tɔdzo', 'efi', 'dzata',
    'wò dada', 'wo dada', 'gbeve', 'aɖi',
]

LOCAL_PROFANITY = _TWI + _GA + _EWE

# Load the default English list, then layer on the local words. `add_censor_words`
# keeps the existing list (unlike `load_censor_words(custom_words=...)`, which
# would replace it) and generates the usual character-substitution variants.
profanity.load_censor_words()
profanity.add_censor_words(LOCAL_PROFANITY)


def contains_profanity(text: str) -> bool:
    """Return True if `text` contains a blacklisted word (English or local)."""
    if not text: return False
    return profanity.contains_profanity(text)
