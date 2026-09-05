from .contact import AddressAdmin, AddressInline, ContactAdmin, ContactInline
from .profile import (
    CertificateAdmin,
    CertificateInline,
    EducationAdmin,
    EducationInline,
    HobbyAdmin,
    HobbyInline,
    JobExperienceAdmin,
    JobExperienceInline,
    ProfileSectionAdmin,
    SpecialisationAdmin,
    SpecialisationInline,
)
from .staff import AssignmentAdmin, AssignmentInline, MemberAdmin, PositionAdmin
from .team import MembershipAdmin, MembershipInline, TeamAdmin

__all__ = [
    'AddressAdmin',
    'AddressInline',
    'AssignmentAdmin',
    'AssignmentInline',
    'CertificateAdmin',
    'CertificateInline',
    'ContactAdmin',
    'ContactInline',
    'EducationAdmin',
    'EducationInline',
    'HobbyAdmin',
    'HobbyInline',
    'JobExperienceAdmin',
    'JobExperienceInline',
    'MemberAdmin',
    'MembershipAdmin',
    'MembershipInline',
    'PositionAdmin',
    'ProfileSectionAdmin',
    'SpecialisationAdmin',
    'SpecialisationInline',
    'TeamAdmin',
]
