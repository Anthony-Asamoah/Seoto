from datetime import datetime

from django.views.generic import TemplateView


class Dashboard(TemplateView):
    extra_context = {'year': datetime.now().year}
    template_name = 'Home/dash.html'
