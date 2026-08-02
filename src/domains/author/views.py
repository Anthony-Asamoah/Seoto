import logging

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views import View

from .forms import ContactForm, DiscoveryCallForm
from .models import (
    Stack, Intro, Education, JobExperience, Hobby
)


def get_context(request):
    return {
        'intro': Intro.objects.filter().first() or None,
        'education': Education.objects.filter(hidden=False) or None,
        'job_history': JobExperience.objects.filter(hidden=False) or None,
        'stack': Stack.objects.filter(is_active=True).first() or None,
        'hobbies': Hobby.objects.filter(hidden=False),
    }


class ReachOut(View):
    def get(self, request):
        # After a valid submission we land here via PRG with the lead's details
        # stashed in the session — render the calendar step (prefilled) instead
        # of the form so they can lock an actual consultation slot.
        booking = request.session.pop('discovery_booking', None)
        if booking:
            return render(request, 'author/reach_out.html', {
                'booking': booking,
                'calendly_url': settings.CALENDLY_URL,
            })

        # No-email "quick message" path lands here via PRG — show the call-back
        # confirmation instead of the form/calendar.
        confirmation = request.session.pop('discovery_confirmation', None)
        if confirmation:
            return render(request, 'author/reach_out.html', {'confirmation': confirmation})

        user = request.user
        initial = None
        if user.is_authenticated:
            initial = {
                'name': f'{user.first_name.title()} {user.last_name.title()}',
                'email': user.email,
            }
        form = DiscoveryCallForm(request=request, initial=initial)
        return render(request, 'author/reach_out.html', {'form': form})

    def post(self, request):
        form = DiscoveryCallForm(request.POST, request=request)
        is_htmx = request.headers.get('HX-Request') == 'true'
        if form.is_valid():
            details = form.save()
            try:
                details.forward_to_email()
            except Exception as e:
                logging.warning(e)

            if form.cleaned_data.get('quick_message'):
                # No email to self-book with — end on a "we'll call you" note.
                confirmation = {
                    'name': form.cleaned_data.get('name', ''),
                    'phone': form.cleaned_data.get('phone', ''),
                }
                if is_htmx:
                    return render(request, 'author/partials/_reach_confirmation.html', {
                        'confirmation': confirmation,
                    })
                request.session['discovery_confirmation'] = confirmation
                return redirect('reach_out')

            booking = {
                'name': form.cleaned_data.get('name', ''),
                'email': form.cleaned_data.get('email', ''),
            }
            if is_htmx:
                # Swap just the calendar fragment into #reach-panel — no full reload.
                return render(request, 'author/partials/_reach_booking.html', {
                    'booking': booking,
                    'calendly_url': settings.CALENDLY_URL,
                })
            # No-JS fallback: carry name/email across the PRG redirect to prefill Calendly.
            request.session['discovery_booking'] = booking
            return redirect('reach_out')

        if is_htmx:
            # Re-render the form fragment with errors in place.
            return render(request, 'author/partials/_reach_form.html', {'form': form})
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
