from django.db import models
from django.utils.text import slugify

from infrastructure.core.model_validators import Validators


class FAQCategory(models.Model):
    """A section of the FAQ page — 'Billing', 'Getting Started'."""

    name = models.CharField(max_length=100, unique=True, validators=[Validators.str])
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.CharField(
        max_length=300, blank=True, null=True,
        help_text="Optional line under the section heading.",
    )
    order = models.PositiveSmallIntegerField(default=1, blank=True)

    class Meta:
        verbose_name_plural = "FAQ Categories"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:120]
        return super().save(*args, **kwargs)


class FAQ(models.Model):
    """One question and its answer."""

    category = models.ForeignKey(
        FAQCategory, on_delete=models.SET_NULL,
        blank=True, null=True, related_name="faqs",
    )
    slug = models.SlugField(
        max_length=140, unique=True, blank=True,
        help_text="Used to deep-link a single answer, e.g. /faq#refund-policy.",
    )
    question = models.CharField(max_length=300, validators=[Validators.str])
    answer = models.TextField()

    is_published = models.BooleanField(
        default=True,
        help_text="Unpublished questions are never served by the API.",
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Featured questions sort ahead of the rest.",
    )
    include_in_schema = models.BooleanField(
        default=True,
        help_text="Include in the FAQPage JSON-LD. Turn off for answers too long "
                  "or link-heavy to be valid structured data.",
    )

    order = models.PositiveSmallIntegerField(default=1, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
        # "-is_featured" because False sorts before True ascending.
        ordering = ["category__order", "-is_featured", "order"]

    def __str__(self):
        return self.question

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.question)[:140]
        return super().save(*args, **kwargs)
