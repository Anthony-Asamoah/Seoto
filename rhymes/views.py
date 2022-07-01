from django.shortcuts import render, HttpResponse
from django.http import FileResponse
from . import the_code


def rhymes(request):
	if request.method == 'POST':
		rhyme = request.POST['rhyme']
		isValid = the_code.rhymeValidator(rhyme)

		if isValid:
			info = the_code.find_rhymes(rhyme)
			words = info['list']
			amount = info['amount']

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

		else:
			words = False
			amount = False

		context = {
			'input': rhyme,
			'words': words,
			'amount': amount
		}

		return render(request, 'rhymes/rhymes.html', context)

	else:
		return render(request, 'rhymes/rhymes.html')


def download_rhyme(request):
	return FileResponse(open('rhymes/Rhymes_Seoto.txt', 'rb'), as_attachment=True)
