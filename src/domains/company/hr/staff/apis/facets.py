from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..services.facets import (
    list_public_position_names,
    list_public_specialisation_names,
    list_public_team_names,
)


class MemberFacetListApi(APIView):
    """GET /api/company/hr/members/facets/ — the vocabularies the filter
    controls offer, so the UI never shows an option that matches nobody."""

    permission_classes = (AllowAny,)

    @extend_schema(
        operation_id='company_member_facets_list',
        summary='List the filter values in use by public members',
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        return Response({
            'positions': list_public_position_names(),
            'teams': list_public_team_names(),
            'specialisations': list_public_specialisation_names(),
        })
