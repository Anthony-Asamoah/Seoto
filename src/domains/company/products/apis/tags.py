from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..services.tags import list_published_tag_labels


class ProductTagListApi(APIView):
    """GET /api/company/products/tags/ — the tag vocabulary for filter controls."""

    permission_classes = (AllowAny,)

    @extend_schema(
        operation_id='company_product_tags_list',
        summary='List every tag in use by a published product',
        responses={200: OpenApiTypes.STR},
    )
    def get(self, request):
        return Response(list_published_tag_labels())
