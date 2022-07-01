from seoto.settings import BASE_DIR
from os import path
import re
import string

BASE_DIR = path.join(BASE_DIR, 'rhymes')


def rhymeValidator(rhyme):
	for letter in range(len(rhyme)):
		if rhyme[letter] not in string.ascii_letters:
			return False
	if len(rhyme) == 0:
		return False
	if rhyme == '':
		return False
	return True


def find_rhymes(rhyme_string):
	dictionary_path = path.join(BASE_DIR, "Words.txt")  # default Path for english dictionary

	dictionary = open(dictionary_path, "r")
	all_text = dictionary.readlines()
	dictionary.close()

	temp = " ".join(all_text)

	regex = re.compile(f'\\w*{rhyme_string}\\s')
	found = sorted(set(regex.findall(temp)))

	return {
		'list': found,
		'amount': len(found)
	}


def write_to_file(rhyme, words, amount):
	with open('rhymes/Rhymes_Seoto.txt', 'w') as file:
		to_file = f'''
				{'Rhyme Db'.rjust(30)}
				{'Powered by Python & Wine'.rjust(30)}


		'''
		to_file += f'({amount}) Words that rhyme with "{rhyme}"\n' + '\n' + ''.center(70, '-') + '\n\n'

		for word in words:
			to_file += f'{word.capitalize()}\n'
		to_file += (''.center(70, '-'))

		file.write(to_file)
