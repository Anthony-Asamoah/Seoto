from typing import Optional

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import (
    Assignment,
    Certificate,
    Contact,
    Education,
    Hobby,
    JobExperience,
    Member,
    Membership,
    Specialisation,
)


class AssignmentSerializer(serializers.ModelSerializer):
    """A held position. Salary and currency are deliberately absent."""

    position = serializers.CharField(source='position.name', read_only=True)

    class Meta:
        model = Assignment
        fields = ('position', 'effective_from')


class MembershipSerializer(serializers.ModelSerializer):
    team = serializers.CharField(source='team.name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = Membership
        fields = ('team', 'role', 'role_display', 'joined_on')


class SpecialisationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialisation
        fields = ('name', 'tools')


class ContactSerializer(serializers.ModelSerializer):
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)

    class Meta:
        model = Contact
        fields = ('channel', 'channel_display', 'value', 'label')


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = (
            'school', 'certificate_title', 'other_certificate_type',
            'start_date', 'end_date', 'city', 'description',
        )


class CertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = ('course_name', 'issuing_body', 'awarded_on', 'expires_on', 'description')


class JobExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobExperience
        fields = ('job_title', 'employer', 'start_date', 'end_date', 'city', 'description')


class HobbySerializer(serializers.ModelSerializer):
    class Meta:
        model = Hobby
        fields = ('description',)


class MemberListSerializer(serializers.ModelSerializer):
    """The team-grid card. Everything here is safe to render publicly —
    salary, national ID, date of birth and addresses never leave the admin."""

    name = serializers.SerializerMethodField()
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    # Declared, not inferred: the model property carries no return hint.
    is_active = serializers.BooleanField(read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    profile_image = serializers.SerializerMethodField()
    positions = serializers.SerializerMethodField()
    teams = serializers.SerializerMethodField()
    specialisations = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = (
            'staff_id', 'name', 'first_name', 'last_name', 'profile_image',
            'positions', 'teams', 'specialisations', 'is_active', 'started_on',
        )

    def get_name(self, obj) -> str:
        return obj.user.get_full_name() or obj.user.get_username()

    def get_profile_image(self, obj) -> Optional[str]:
        if not obj.profile_image: return None
        request = self.context.get('request')
        url = obj.profile_image.url
        return request.build_absolute_uri(url) if request else url

    # ``active_*`` attributes come from the service's prefetches; falling back to
    # the model properties would re-query once per row.
    @extend_schema_field(AssignmentSerializer(many=True))
    def get_positions(self, obj):
        return AssignmentSerializer(getattr(obj, 'active_assignments', []), many=True).data

    @extend_schema_field(MembershipSerializer(many=True))
    def get_teams(self, obj):
        return MembershipSerializer(getattr(obj, 'active_memberships', []), many=True).data

    @extend_schema_field(SpecialisationSerializer(many=True))
    def get_specialisations(self, obj):
        return SpecialisationSerializer(getattr(obj, 'public_specialisations', []), many=True).data


class PaginatedMemberListSerializer(serializers.Serializer):
    """Mirrors the envelope ``PageNumberPagination`` returns. Declared by hand
    because the list view paginates in ``get()``, where the schema generator
    cannot see it."""

    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = MemberListSerializer(many=True)


class MemberDetailSerializer(MemberListSerializer):
    """The full public profile."""

    gender_display = serializers.CharField(source='get_gender_display', read_only=True)
    contacts = serializers.SerializerMethodField()
    education = serializers.SerializerMethodField()
    certificates = serializers.SerializerMethodField()
    job_experience = serializers.SerializerMethodField()
    hobbies = serializers.SerializerMethodField()

    class Meta(MemberListSerializer.Meta):
        fields = MemberListSerializer.Meta.fields + (
            'about', 'gender', 'gender_display', 'nationality', 'hometown',
            'ended_on', 'contacts', 'education', 'certificates',
            'job_experience', 'hobbies',
        )

    @extend_schema_field(ContactSerializer(many=True))
    def get_contacts(self, obj):
        return ContactSerializer(getattr(obj, 'public_contacts', []), many=True).data

    @extend_schema_field(EducationSerializer(many=True))
    def get_education(self, obj):
        return EducationSerializer(getattr(obj, 'public_education', []), many=True).data

    @extend_schema_field(CertificateSerializer(many=True))
    def get_certificates(self, obj):
        return CertificateSerializer(getattr(obj, 'public_certificates', []), many=True).data

    @extend_schema_field(JobExperienceSerializer(many=True))
    def get_job_experience(self, obj):
        return JobExperienceSerializer(getattr(obj, 'public_job_experience', []), many=True).data

    @extend_schema_field(HobbySerializer(many=True))
    def get_hobbies(self, obj):
        return HobbySerializer(getattr(obj, 'public_hobbies', []), many=True).data
