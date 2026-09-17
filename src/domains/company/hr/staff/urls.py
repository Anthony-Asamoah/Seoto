from django.urls import path

from .apis import MemberDetailApi, MemberFacetListApi, MemberListApi

urlpatterns = [
    path('', MemberListApi.as_view(), name='member_list'),
    path('facets/', MemberFacetListApi.as_view(), name='member_facet_list'),
    path('<slug:staff_id>/', MemberDetailApi.as_view(), name='member_detail'),
]
