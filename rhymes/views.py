from django.shortcuts import render
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

			# the_code.write_to_file(rhyme, words, amount)

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
