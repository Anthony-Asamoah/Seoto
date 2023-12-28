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
        self.rhyme_string = rhyme_string
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

    def findall(self) -> None:
        dictionary_path = path.join(BASE_DIR, "Words.txt")  # default Path for english dictionary
        dictionary = open(dictionary_path, "r")
        all_text = dictionary.readlines()
        dictionary.close()
        temp = " ".join(all_text)

        if ',' not in self.rhyme_string:
            regex = re.compile(f'\\w*{self.rhyme_string.strip()}\\s')
            data = sorted({i.title() for i in regex.findall(temp)})
            if data: self._result[self.rhyme_string] = data
        else:
            rhyme_list = self.rhyme_string.split(',')
            for item in rhyme_list:
                item = item.strip()
                regex = re.compile(f'\\w*{item}\\s')
                data = (sorted({i.title() for i in regex.findall(temp)}))
                if data: self._result[item] = data

    def get_all_words(self) -> list:
        if not self._all_words:
            for rhyme in self._result.values(): self._all_words.extend(rhyme)
        return self._all_words

    def word_count(self) -> int:
        if not self.get_all_words:
            self.get_all_words()
        return len(self._all_words)

    def get_text(self) -> str:
        if not self._result: return ''
        if len(self._result.keys()) == 1:
            return '\n'.join(self._result[self.rhyme_string])
        txt = ''
        for rhyme, words in self._result.items():
            txt += '...' + rhyme + '\n'
            txt += '\n'.join(words)
            txt += '\n\n'
        return txt

    def is_empty(self) -> bool:
        if self.word_count(): return False
        return True

    def get_result(self) -> dict:
        return self._result
