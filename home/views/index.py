from datetime import datetime

from django.views.generic import TemplateView


class Home(TemplateView):
    template_name = 'Home/home.html'


class Apps(TemplateView):
    extra_context = {'year': datetime.now().year}
    template_name = 'Home/apps.html'
