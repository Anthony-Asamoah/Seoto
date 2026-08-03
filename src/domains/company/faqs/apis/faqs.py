from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status as http_status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from infrastructure.core.pagination import DefaultAPIPagination

from ..serializers import FAQSerializer, PaginatedFAQListSerializer
from ..services.faqs import (
    ORDERING_FIELDS,
    FAQFilterError,
    get_published_faq,
    list_published_faqs,
)


class FAQListApi(APIView):
    """GET /api/company/faqs/ — the FAQ page."""

    permission_classes = (AllowAny,)

    # Filters are read off query_params, so the schema can't introspect them.
    @extend_schema(
        operation_id='company_faqs_list',
        summary='List published FAQs',
        responses={200: PaginatedFAQListSerializer},
        parameters=[
            OpenApiParameter(
                'category', OpenApiTypes.STR, many=True,
                description='Repeatable category slug. Matches any of the ones given.',
            ),
            OpenApiParameter('q', OpenApiTypes.STR, description='Search question and answer.'),
            OpenApiParameter('is_featured', OpenApiTypes.BOOL),
            OpenApiParameter(
                'ordering', OpenApiTypes.STR,
                enum=sorted(ORDERING_FIELDS) + [f'-{f}' for f in sorted(ORDERING_FIELDS)],
                description="Prefix with '-' to sort descending.",
            ),
            OpenApiParameter('page', OpenApiTypes.INT, description='Page number.'),
            OpenApiParameter(
                'page_size', OpenApiTypes.INT,
                description=f'Results per page (default {DefaultAPIPagination.page_size}, '
                            f'max {DefaultAPIPagination.max_page_size}).',
            ),
        ],
    )
    def get(self, request):
        params = request.query_params

        try:
            queryset = list_published_faqs(
                categories=params.getlist('category'),
                search=params.get('q'),
                is_featured=params.get('is_featured'),
                ordering=params.get('ordering'),
            )
        except FAQFilterError as error:
            return Response(
                {'detail': str(error)}, status=http_status.HTTP_400_BAD_REQUEST
            )

        paginator = DefaultAPIPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = FAQSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


class FAQDetailApi(APIView):
    """GET /api/company/faqs/<slug>/ — one question, for a deep link."""

    permission_classes = (AllowAny,)

    @extend_schema(
        operation_id='company_faqs_retrieve',
        summary='Retrieve one FAQ by slug',
        responses={200: FAQSerializer, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request, slug):
        faq = get_published_faq(slug)
        if faq is None:
            return Response(
                {'detail': 'Not found.'}, status=http_status.HTTP_404_NOT_FOUND
            )

        serializer = FAQSerializer(faq, context={'request': request})
        return Response(serializer.data)
