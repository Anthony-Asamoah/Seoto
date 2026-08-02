from django.urls import path

from .apis import ProductDetailApi, ProductListApi, ProductTagListApi

urlpatterns = [
    path('', ProductListApi.as_view(), name='product_list'),
    path('tags/', ProductTagListApi.as_view(), name='product_tag_list'),
    path('<slug:slug>/', ProductDetailApi.as_view(), name='product_detail'),
]
