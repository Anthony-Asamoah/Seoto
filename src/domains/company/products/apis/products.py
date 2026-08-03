from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status as http_status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from infrastructure.core.pagination import DefaultAPIPagination

from ..serializers import (
    PaginatedProductListSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
)
from ..services.products import (
    ORDERING_FIELDS,
    PUBLIC_STATUSES,
    ProductFilterError,
    get_published_product,
    list_published_products,
)


class ProductListApi(APIView):
    """GET /api/company/products/ — the listings page."""

    permission_classes = (AllowAny,)

    # Filters are read off query_params, so the schema can't introspect them.
    @extend_schema(
        operation_id='company_products_list',
        summary='List published products',
        responses={200: PaginatedProductListSerializer},
        parameters=[
            OpenApiParameter(
                'tag', OpenApiTypes.STR, many=True,
                description='Repeatable. A product must carry every tag given.',
            ),
            OpenApiParameter(
                'status', OpenApiTypes.STR, many=True, enum=PUBLIC_STATUSES,
                description='Repeatable. Drafts are rejected.',
            ),
            OpenApiParameter('client', OpenApiTypes.STR, description='Case-insensitive contains.'),
            OpenApiParameter('q', OpenApiTypes.STR, description='Search title, client, summary and body.'),
            OpenApiParameter('launched_after', OpenApiTypes.DATE),
            OpenApiParameter('launched_before', OpenApiTypes.DATE),
            OpenApiParameter('has_images', OpenApiTypes.BOOL),
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
            queryset = list_published_products(
                tags=params.getlist('tag'),
                statuses=params.getlist('status'),
                client=params.get('client'),
                search=params.get('q'),
                launched_after=params.get('launched_after'),
                launched_before=params.get('launched_before'),
                has_images=params.get('has_images'),
                is_featured=params.get('is_featured'),
                ordering=params.get('ordering'),
            )
        except ProductFilterError as error:
            return Response(
                {'detail': str(error)}, status=http_status.HTTP_400_BAD_REQUEST
            )

        paginator = DefaultAPIPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = ProductListSerializer(
            page, many=True, context={'request': request}
        )
        return paginator.get_paginated_response(serializer.data)


class ProductDetailApi(APIView):
    """GET /api/company/products/<slug>/ — one expanded listing."""

    permission_classes = (AllowAny,)

    @extend_schema(
        operation_id='company_products_retrieve',
        summary='Retrieve one product by slug',
        responses={200: ProductDetailSerializer, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request, slug):
        product = get_published_product(slug)
        if product is None:
            return Response(
                {'detail': 'Not found.'}, status=http_status.HTTP_404_NOT_FOUND
            )

        serializer = ProductDetailSerializer(product, context={'request': request})
        return Response(serializer.data)
