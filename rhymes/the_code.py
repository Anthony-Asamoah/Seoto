import re
import string
from os import path

from seoto.exceptions import InvalidInput
from seoto.settings import BASE_DIR

BASE_DIR = path.join(BASE_DIR, 'rhymes')


class RhymeDB:

    def __init__(self, rhyme_string: str):
        self._all_words = []
        self._result = {}

        self._rhyme_string = rhyme_string
        self.validate()
        self.findall()

    def validate(self) -> None:
        self._rhyme_string = self._rhyme_string.lower().strip()
        if not isinstance(self._rhyme_string, str):
            raise InvalidInput("At least one english letter is required")
        if not self._rhyme_string:
            raise InvalidInput("At least one english letter is required")
        allowed_chars = string.ascii_letters + ' ,'
        for letter in self._rhyme_string:
            if letter not in allowed_chars: raise InvalidInput('Only english letters are allowed')

    @staticmethod
    def _ideal_suffix_length(word: str) -> int:
        """How many trailing letters to rhyme on, scaled by word length.

        Longer words need a longer ending to rhyme well — matching only the
        last 3 letters of "action" pulls in non-rhymes like "lion"/"onion",
        whereas "tion" keeps it to nation/station. Short words rhyme on 2.
        """
        length = len(word)
        if length < 4:
            return 2
        if length < 6:
            return 3
        return 4

    def _find_rhymes_for_word(self, word: str, temp: str) -> None:
        # Try the ideal suffix for this word's length, shortening only if the
        # longer (more specific) ending matches nothing in the dictionary.
        for n in range(self._ideal_suffix_length(word), 0, -1):
            if len(word) >= n:
                suffix = word[-n:]
                regex = re.compile(f'\\w*{suffix}\\s')
                data = sorted({i.title() for i in regex.findall(temp)})
                if data:
                    self._result[suffix] = data
                    return

    def findall(self) -> None:
        dictionary_path = path.join(BASE_DIR, "Words.txt")  # default Path for english dictionary
        dictionary = open(dictionary_path, "r")
        all_text = dictionary.readlines()
        dictionary.close()
        temp = " ".join(all_text)

        if ',' not in self._rhyme_string:
            self._find_rhymes_for_word(self._rhyme_string.strip(), temp)
        else:
            for item in self._rhyme_string.split(','):
                self._find_rhymes_for_word(item.strip(), temp)

    def get_all_words(self) -> list:
        if not self._all_words:
            for rhyme in self._result.values(): self._all_words.extend(rhyme)
        return self._all_words

    def word_count(self) -> int:
        if not self.get_all_words:
            self.get_all_words()
        return len(self._all_words)

    def get_text(self) -> str:
        if not self._result:
            return ''
        if len(self._result.keys()) == 1:
            return '\n'.join(list(self._result.values())[0])
        txt = ''
        for rhyme, words in self._result.items():
            txt += '...' + rhyme + '\n'
            txt += '\n'.join(words or [])
            txt += '\n\n'
        return txt

    def is_empty(self) -> bool:
        if self.word_count(): return False
        return True

    def get_result(self) -> dict:
        return self._result
