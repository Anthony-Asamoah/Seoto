from django.shortcuts import render


def generate_invoice(request):
    return render(request, 'generate_invoice/index.html')
