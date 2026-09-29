from django.shortcuts import render


def generate_invoice(request):
    return render(request, 'apps/generate_invoice/index.html')
