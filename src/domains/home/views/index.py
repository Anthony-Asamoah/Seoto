from datetime import datetime

from django.conf import settings
from django.views.generic import TemplateView


class Home(TemplateView):
    template_name = 'Home/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['seoto_url'] = settings.SEOTO_URL
        return context


class Apps(TemplateView):
    template_name = 'Home/apps.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['year'] = datetime.now().year
        context['seoto_url'] = settings.SEOTO_URL
        return context
