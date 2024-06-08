from datetime import datetime

from django.views.generic import TemplateView


class Home(TemplateView):
    extra_context = {'year': datetime.now().year}
    template_name = 'Home/index.html'
