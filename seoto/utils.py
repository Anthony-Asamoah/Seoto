from os import environ


def load_variables_into_environment():
	with open(r".env", 'r') as env:
		variables = env.readlines()

	for variable in variables:
		environ[variable.split('=')[0]] = str(variable.split('=')[1].replace('\n', ''))

	del variables
