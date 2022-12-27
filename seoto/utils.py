import logging
from os import environ

logging.basicConfig(
	filename='logs.txt',
	level=logging.DEBUG,
	format='[%(asctime)s] - %(levelname)s - %(message)s'
)


def load_variables_into_environment():
	try:
		with open(r".env", 'r') as env:
			variables = env.readlines()
	except FileNotFoundError:
		with open(r"/home/Tony48/tony48.pythonanywhere.com/.env", 'r') as env:
			variables = env.readlines()

	for variable in variables:
		environ[variable.split('=')[0]] = str(variable.split('=')[1].replace('\n', ''))

	# logging.info(variables)

	del variables
