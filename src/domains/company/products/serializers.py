from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Product, ProductImage, ProductTag


class ProductTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductTag
        fields = ('id', 'label')


class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ('id', 'url', 'alt_text', 'caption', 'is_cover', 'order')

    def get_url(self, obj) -> str | None:
        if not obj.image: return None
        request = self.context.get('request')
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url


class ProductListSerializer(serializers.ModelSerializer):
    """The collapsed listing — enough to render the closed accordion row."""

    tags = serializers.SlugRelatedField(many=True, read_only=True, slug_field='label')
    # Both: ``status`` is the machine value clients filter on, ``status_display``
    # is the human label. Sending only the label would make the value the UI
    # receives untypable back into the ?status= filter.
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    cover = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            'slug', 'title', 'client', 'summary',
            'tags', 'status', 'status_display', 'live_url', 'launched_on',
            'is_featured', 'cover',
        )

    @extend_schema_field(ProductImageSerializer(allow_null=True))
    def get_cover(self, obj):
        image = next((i for i in obj.images.all() if i.is_cover), None)
        if image is None: return None
        return ProductImageSerializer(image, context=self.context).data


class PaginatedProductListSerializer(serializers.Serializer):
    """Mirrors the envelope ``PageNumberPagination`` returns. Declared by hand
    because the list view paginates in ``get()``, where the schema generator
    cannot see it."""

    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = ProductListSerializer(many=True)


class ProductDetailSerializer(ProductListSerializer):
    """The expanded panel; adds the long-form copy and every screenshot."""

    images = ProductImageSerializer(many=True, read_only=True)

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + (
            'body', 'outcome', 'contributors', 'sponsors', 'images',
        )
