from django.urls import include, path

urlpatterns = [
    path('products/', include('domains.website.products.urls')),
    path('faqs/', include('domains.website.faqs.urls')),
]
