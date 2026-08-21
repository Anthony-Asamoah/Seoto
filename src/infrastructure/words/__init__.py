from functools import lru_cache
from pathlib import Path

WORDS_DIR = Path(__file__).resolve().parent

ENGLISH_DICTIONARY = WORDS_DIR / 'english_dictionary.txt'


@lru_cache(maxsize=None)
def load_words(source: Path, min_length: int = 1) -> tuple:
    """Words from one list file, cached per process — the file is large."""
    with open(source, encoding='utf-8') as handle:
        return tuple(
            word for word in (line.strip() for line in handle) if len(word) >= min_length
        )
