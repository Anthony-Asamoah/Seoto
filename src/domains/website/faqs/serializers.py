from rest_framework import serializers

from .models import FAQ, FAQCategory


class FAQCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQCategory
        fields = ('id', 'name', 'slug', 'description', 'order')


class FAQSerializer(serializers.ModelSerializer):
    """One accordion row. Unlike products there is no collapsed/expanded split:
    the answer ships with the list so the panel opens without a second request
    and the JSON-LD can be built from the same payload."""

    category = serializers.SlugRelatedField(read_only=True, slug_field='slug')
    category_name = serializers.CharField(
        source='category.name', read_only=True, default=None,
    )

    class Meta:
        model = FAQ
        fields = (
            'slug', 'question', 'answer',
            'category', 'category_name',
            'is_featured', 'include_in_schema', 'order', 'updated_at',
        )


class PaginatedFAQListSerializer(serializers.Serializer):
    """Mirrors the envelope ``PageNumberPagination`` returns. Declared by hand
    because the list view paginates in ``get()``, where the schema generator
    cannot see it."""

    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = FAQSerializer(many=True)
