import os

from django.db import models
from django.utils.text import slugify

from infrastructure.core.model_validators import Validators
from utils.enums import DefaultEnum


def product_image_path(instance, filename):
    """Screenshots live under a folder per product, so they stay grouped in S3."""
    ext = os.path.splitext(filename)[1].lower()
    slug = instance.product.slug or 'product'
    return f'company/products/{slug}/{instance.order}{ext}'


class ProductStatus(DefaultEnum):
    DRAFT = "Draft"
    IN_PROGRESS = "In Progress"
    LAUNCHED = "Launched"
    ARCHIVED = "Archived"
    MANAGED = "Managed"


class ProductTag(models.Model):
    """Scope tags shown on a listing — 'Wagtail', 'WooCommerce', 'Multilingual'."""
    label = models.CharField(max_length=100, unique=True, validators=[Validators.str])
    order = models.PositiveSmallIntegerField(default=1, blank=True)

    class Meta:
        verbose_name_plural = "Product Tags"
        ordering = ["order", "label"]

    def __str__(self):
        return self.label


class Product(models.Model):
    """Work we have done — one listing on the marketing site."""

    slug = models.SlugField(max_length=120, unique=True, blank=True)
    title = models.CharField(max_length=200, validators=[Validators.str])
    client = models.CharField(max_length=200, blank=True, null=True)
    tags = models.ManyToManyField(ProductTag, blank=True, related_name="products")

    summary = models.CharField(
        max_length=300,
        help_text="The single line shown while the listing is collapsed.",
    )
    body = models.TextField(help_text="What we built — shown when the listing expands.")
    outcome = models.TextField(
        blank=True, null=True,
        help_text="A result we can stand behind. Leave empty rather than guessing.",
    )

    live_url = models.URLField(max_length=1000, blank=True, null=True)
    status = models.CharField(
        max_length=50, choices=list(ProductStatus.key_value_pairs()),
        default=ProductStatus.DRAFT.name,
    )

    # Plain lists of names. JSONField rather than related models: these are
    # credits, not entities we query, join or de-duplicate on.
    contributors = models.JSONField(
        default=list, blank=True,
        help_text='Names of people who worked on it, e.g. ["Ada Lovelace"].',
    )
    sponsors = models.JSONField(
        default=list, blank=True,
        help_text='Names of funding or backing organisations.',
    )

    is_featured = models.BooleanField(
        default=False,
        help_text="Featured products sort ahead of the rest.",
    )
    launched_on = models.DateField(blank=True, null=True)
    order = models.PositiveSmallIntegerField(default=1, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Featured first, then the manual order. "-is_featured" because False
        # sorts before True ascending.
        ordering = ["-is_featured", "order", "-launched_on"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        return super().save(*args, **kwargs)


class ProductImage(models.Model):
    """Screenshots for a product. One with none renders type-only, never a
    stand-in mockup."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=product_image_path)
    alt_text = models.CharField(max_length=250, validators=[Validators.str])
    caption = models.CharField(max_length=250, blank=True, null=True)
    is_cover = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=1, blank=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.product.title} — {self.alt_text}"
