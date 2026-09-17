from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status as http_status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import DefaultAPIPagination

from ..serializers import (
    MemberDetailSerializer,
    MemberListSerializer,
    PaginatedMemberListSerializer,
)
from ..services.members import (
    GENDERS,
    ORDERING_FIELDS,
    ROLES,
    MemberFilterError,
    get_public_member,
    list_public_members,
)

_REPEATABLE = 'Repeatable. A member must match every value given.'


class MemberListApi(APIView):
    """GET /api/company/hr/members/ — the team directory."""

    permission_classes = (AllowAny,)

    # Filters are read off query_params, so the schema can't introspect them.
    @extend_schema(
        operation_id='company_members_list',
        summary='List public company members',
        responses={200: PaginatedMemberListSerializer},
        parameters=[
            OpenApiParameter('position', OpenApiTypes.STR, many=True, description=f'{_REPEATABLE} Currently held positions only.'),
            OpenApiParameter('team', OpenApiTypes.STR, many=True, description=f'{_REPEATABLE} Active memberships only.'),
            OpenApiParameter('specialisation', OpenApiTypes.STR, many=True, description=_REPEATABLE),
            OpenApiParameter('role', OpenApiTypes.STR, many=True, enum=ROLES, description='Team role on an active membership.'),
            OpenApiParameter('gender', OpenApiTypes.STR, many=True, enum=GENDERS),
            OpenApiParameter('nationality', OpenApiTypes.STR, description='Case-insensitive contains.'),
            OpenApiParameter('hometown', OpenApiTypes.STR, description='Case-insensitive contains.'),
            OpenApiParameter('school', OpenApiTypes.STR, description='Case-insensitive contains, over visible education.'),
            OpenApiParameter('certificate', OpenApiTypes.STR, description='Matches a certificate course or an education title.'),
            OpenApiParameter('q', OpenApiTypes.STR, description='Search name, staff ID, bio, specialisation and position.'),
            OpenApiParameter('started_after', OpenApiTypes.DATE),
            OpenApiParameter('started_before', OpenApiTypes.DATE),
            OpenApiParameter('is_active', OpenApiTypes.BOOL, description='False returns former members.'),
            OpenApiParameter('has_image', OpenApiTypes.BOOL),
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
            queryset = list_public_members(
                positions=params.getlist('position'),
                teams=params.getlist('team'),
                specialisations=params.getlist('specialisation'),
                roles=params.getlist('role'),
                genders=params.getlist('gender'),
                nationality=params.get('nationality'),
                hometown=params.get('hometown'),
                school=params.get('school'),
                certificate=params.get('certificate'),
                search=params.get('q'),
                started_after=params.get('started_after'),
                started_before=params.get('started_before'),
                is_active=params.get('is_active'),
                has_image=params.get('has_image'),
                ordering=params.get('ordering'),
            )
        except MemberFilterError as error:
            return Response(
                {'detail': str(error)}, status=http_status.HTTP_400_BAD_REQUEST
            )

        paginator = DefaultAPIPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = MemberListSerializer(
            page, many=True, context={'request': request}
        )
        return paginator.get_paginated_response(serializer.data)


class MemberDetailApi(APIView):
    """GET /api/company/hr/members/<staff_id>/ — one public profile."""

    permission_classes = (AllowAny,)

    @extend_schema(
        operation_id='company_members_retrieve',
        summary='Retrieve one member by staff ID',
        responses={200: MemberDetailSerializer, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request, staff_id):
        member = get_public_member(staff_id)
        if member is None:
            return Response(
                {'detail': 'Not found.'}, status=http_status.HTTP_404_NOT_FOUND
            )

        serializer = MemberDetailSerializer(member, context={'request': request})
        return Response(serializer.data)
