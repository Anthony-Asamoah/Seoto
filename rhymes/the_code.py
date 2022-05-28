from seoto.settings import BASE_DIR
from os import path
import re
import string

BASE_DIR = path.join(BASE_DIR, 'rhymes')


def rhymeValidator(rhyme):
	for letter in range(len(rhyme)):
		if rhyme[letter] not in string.ascii_letters or rhyme[letter] == 0:
			return False
	return True


def find_rhymes(rhyme_string):
	dictionary_path = path.join(BASE_DIR, "Words.txt")  # default Path for english dictionary

	dictionary = open(dictionary_path, "r")
	all_text = dictionary.readlines()
	dictionary.close()

	temp = " ".join(all_text)

	regex = re.compile(f'\\w*{rhyme_string}\\s')
	found = regex.findall(temp)

	return sorted(set(found))
