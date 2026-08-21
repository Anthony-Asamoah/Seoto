import string
from collections import Counter
from functools import lru_cache

from infrastructure.core.exceptions import InvalidInput
from infrastructure.words import ENGLISH_DICTIONARY, load_words

MAX_LETTERS = 15
MIN_WORD_LENGTH = 3


@lru_cache(maxsize=1)
def _load_index() -> dict:
    """Map sorted-letters -> words sharing them, built once per process."""
    index = {}
    for word in load_words(ENGLISH_DICTIONARY, MIN_WORD_LENGTH):
        index.setdefault(''.join(sorted(word)), []).append(word)
    return index


class AnagramSolver:

    def __init__(self, letters: str):
        self._letters = letters
        self._exact = []
        self._partials = {}

        self.validate()
        self.solve()

    def validate(self) -> None:
        self._letters = ''.join(self._letters.lower().split())
        if not self._letters:
            raise InvalidInput('At least one english letter is required')
        for letter in self._letters:
            if letter not in string.ascii_lowercase:
                raise InvalidInput('Only english letters are allowed')
        if len(self._letters) < MIN_WORD_LENGTH:
            raise InvalidInput(f'Enter at least {MIN_WORD_LENGTH} letters')
        if len(self._letters) > MAX_LETTERS:
            raise InvalidInput(f'{MAX_LETTERS} letters is the limit')

    def solve(self) -> None:
        available = Counter(self._letters)
        total = len(self._letters)
        for key, words in _load_index().items():
            if len(key) > total: continue
            if not Counter(key) <= available: continue
            if len(key) == total:
                self._exact.extend(words)
            else:
                self._partials.setdefault(len(key), []).extend(words)
        self._exact.sort()
        for words in self._partials.values():
            words.sort()

    @property
    def letters(self) -> str:
        return self._letters

    def get_exact(self) -> list:
        return self._exact

    def get_groups(self) -> list:
        """Partial matches, longest words first."""
        return [
            {'length': length, 'words': self._partials[length]}
            for length in sorted(self._partials, reverse=True)
        ]

    def word_count(self) -> int:
        return len(self._exact) + sum(len(w) for w in self._partials.values())

    def is_empty(self) -> bool:
        return self.word_count() == 0
