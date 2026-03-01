import logging

from django.contrib import messages
from django.shortcuts import render, redirect
from django.views import View

from .forms import ContactForm
from .models import (
    Stack, Intro, Education, JobExperience
)


def get_context(request):
    return {
        'intro': Intro.objects.filter().first() or None,
        'education': Education.objects.filter(hidden=False) or None,
        'job_history': JobExperience.objects.filter(hidden=False) or None,
        'stack': Stack.objects.filter(is_active=True).first() or None,
    }


class ReachOut(View):
    def get(self, request):
        user = request.user
        form = ContactForm(request=request)
        if user.is_authenticated:
            form = ContactForm(
                request=request,
                initial={
                    'name': f'{user.first_name.title()} {user.last_name.title()}',
                    'email': user.email
                },
            )
        return render(request, 'author/reach_out.html', {'form': form})

    def post(self, request):
        form = ContactForm(request.POST, request=request)
        if form.is_valid():
            details = form.save()
            msg = 'Message Sent.'
            try:
                details.forward_to_email()
            except Exception as e:
                logging.warning(e)
                msg = 'Message Saved.'
            messages.success(request, msg)
            return redirect('reach_out')
        else:
            messages.error(request, 'Failed to send. Kindly try again.')
            return render(request, 'author/reach_out.html', {'form': form})


class About(View):
    def get(self, request):
        user = request.user
        form = ContactForm(request=request)
        if user.is_authenticated: form = ContactForm(
            request=request,
            initial={
                'name': f'{user.first_name.title()} {user.last_name.title()}',
                'email': user.email
            },
        )

        context = get_context(request)
        context["form"] = form

        return render(request, 'author/about.html', context)

    def post(self, request):
        form = ContactForm(request.POST, request=request)
        if form.is_valid():
            details = form.save()
            msg = 'Message Sent.'
            try:
                details.forward_to_email()
            except Exception as e:
                logging.warning(e)
                msg = 'Message Saved.'
            messages.success(request, msg)
            return redirect('about')
        else:
            messages.error(request, 'Could not send the message. Lets try again.')

            context = get_context(request)
            context["form"] = form
            return render(request, 'author/about.html', context)
