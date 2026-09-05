from infrastructure.utils import BaseChoices


class CurrencyChoices(BaseChoices):
    GHS = 'GHS', 'GHS'
    USD = 'USD', 'USD'
    EUR = 'EUR', 'EUR'
    GBP = 'GBP', 'GBP'


class GenderChoices(BaseChoices):
    MALE = 'male', 'Male'
    FEMALE = 'female', 'Female'
    OTHER = 'other', 'Other'


class ContactChannel(BaseChoices):
    MOBILE = 'mobile', 'Mobile'
    LANDLINE = 'landline', 'Landline'
    EMAIL = 'email', 'Email'
    WHATSAPP = 'whatsapp', 'WhatsApp'
    LINKEDIN = 'linkedin', 'LinkedIn'
    GITHUB = 'github', 'GitHub'
    WEBSITE = 'website', 'Website'
    OTHER = 'other', 'Other'


class ContactUsage(BaseChoices):
    PERSONAL = 'personal', 'Personal'
    WORK = 'work', 'Work'
    EMERGENCY = 'emergency', 'Emergency'


class AddressType(BaseChoices):
    RESIDENTIAL = 'residential', 'Residential'
    POSTAL = 'postal', 'Postal'
    HOMETOWN = 'hometown', 'Hometown'


class MembershipRole(BaseChoices):
    MEMBER = 'member', 'Member'
    LEAD = 'lead', 'Lead'


class CertificateType(BaseChoices):
    HIGH_SCHOOL_DIPLOMA = "High School Diploma"
    ASSOCIATE_DEGREE = "Associate Degree"
    BACHELORS_DEGREE = "Bachelor's Degree", "Bachelor's Degree"
    MASTERS_DEGREE = "Master's Degree", "Master's Degree"
    DOCTORATE_DEGREE = "Doctorate Degree"
    PROFESSIONAL_DEGREE = "Professional Degree"
    CERTIFICATE = "Certificate"
    DIPLOMA = "Diploma"
    POSTGRADUATE_CERTIFICATE = "Postgraduate Certificate"
    POSTGRADUATE_DIPLOMA = "Postgraduate Diploma"
    TRADE_CERTIFICATE = "Trade Certificate"
    VOCATIONAL_CERTIFICATE = "Vocational Certificate"
    HONORARY_DOCTORATE = "Honorary Doctorate"
    OTHER = "Other"
