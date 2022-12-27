from os import environ


def load_variables_into_environment():
	try:
		with open(r".env", 'r') as env:
			variables = env.readlines()
	except FileNotFoundError:
		with open(r"../.env", 'r') as env:
			variables = env.readlines()

	for variable in variables:
		environ[variable.split('=')[0]] = str(variable.split('=')[1].replace('\n', ''))

	del variables
