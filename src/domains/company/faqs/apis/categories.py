from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..serializers import FAQCategorySerializer
from ..services.categories import list_published_categories


class FAQCategoryListApi(APIView):
    """GET /api/company/faqs/categories/ — the sections for filter controls."""

    permission_classes = (AllowAny,)

    @extend_schema(
        operation_id='company_faq_categories_list',
        summary='List every category holding a published FAQ',
        responses={200: FAQCategorySerializer(many=True)},
    )
    def get(self, request):
        serializer = FAQCategorySerializer(list_published_categories(), many=True)
        return Response(serializer.data)
