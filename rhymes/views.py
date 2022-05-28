from django.shortcuts import render, HttpResponse
from . import the_code


def rhymes(request):
	if request.method == 'POST':
		rhyme = request.POST['rhyme']
		isValid = the_code.rhymeValidator(rhyme)

		if isValid:
			words = the_code.find_rhymes(rhyme)
		else:
			words = False

		context = {
			'input': rhyme,
			'words': words,
		}
		return render(request, 'rhymes/rhymes.html', context)
	else:
		return render(request, 'rhymes/rhymes.html')
