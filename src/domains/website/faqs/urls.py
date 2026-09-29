from django.urls import path

from .apis import FAQCategoryListApi, FAQDetailApi, FAQListApi

urlpatterns = [
    path('', FAQListApi.as_view(), name='faq_list'),
    path('categories/', FAQCategoryListApi.as_view(), name='faq_category_list'),
    path('<slug:slug>/', FAQDetailApi.as_view(), name='faq_detail'),
]
