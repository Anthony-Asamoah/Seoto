from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class ThemePreset(models.Model):
    """
    Represents a theme preset that can be official (admin-created) or
    user-published (pending verification).
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_themes')

    # Color fields (hex values)
    primary_color = models.CharField(max_length=7, default='#007bff', help_text='Hex color code (e.g., #007bff)')
    secondary_color = models.CharField(max_length=7, default='#6c757d', help_text='Hex color code')
    background_color = models.CharField(max_length=7, default='#ffffff', help_text='Hex color code')
    text_color = models.CharField(max_length=7, default='#212529', help_text='Body text color')
    text_head_color = models.CharField(max_length=7, default='#000000', help_text='Headers and labels color')
    navbar_bg = models.CharField(max_length=7, default='#f8f9fa', help_text='Navbar background color')
    navbar_text = models.CharField(max_length=7, default='#000000', help_text='Navbar text color')

    # Button colors
    btn_success_bg = models.CharField(max_length=7, default='#28a745', help_text='Success button background')
    btn_success_text = models.CharField(max_length=7, default='#ffffff', help_text='Success button text')
    btn_danger_bg = models.CharField(max_length=7, default='#dc3545', help_text='Danger button background')
    btn_danger_text = models.CharField(max_length=7, default='#ffffff', help_text='Danger button text')
    btn_warning_bg = models.CharField(max_length=7, default='#ffc107', help_text='Warning button background')
    btn_warning_text = models.CharField(max_length=7, default='#000000', help_text='Warning button text')
    btn_info_bg = models.CharField(max_length=7, default='#17a2b8', help_text='Info button background')
    btn_info_text = models.CharField(max_length=7, default='#ffffff', help_text='Info button text')
    btn_secondary_bg = models.CharField(max_length=7, default='#6c757d', help_text='Secondary button background')
    btn_secondary_text = models.CharField(max_length=7, default='#ffffff', help_text='Secondary button text')

    # Card colors
    card_bg_color = models.CharField(max_length=7, default='#ffffff', help_text='Card background color')
    card_header_bg_color = models.CharField(max_length=7, default='#f8f9fa', help_text='Card header background')
    card_text_color = models.CharField(max_length=7, default='#212529', help_text='Card text color')

    # Publishing and verification
    is_official = models.BooleanField(default=False, help_text='Official theme created by admin')
    is_public = models.BooleanField(default=False, help_text='User wants to share this theme')
    is_public_verified = models.BooleanField(default=False, help_text='Admin has verified this public theme')
    is_featured = models.BooleanField(default=False, help_text='Featured theme highlighted by admin')

    # Rating tracking
    rating_count = models.IntegerField(default=0)
    rating_sum = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_featured', '-is_official', '-rating_count', '-created_at']

    def __str__(self):
        return self.name

    @property
    def average_rating(self):
        """Calculate average rating"""
        if self.rating_count == 0:
            return 0
        return round(self.rating_sum / self.rating_count, 1)

    def update_rating(self):
        """Recalculate rating from ThemeRating objects"""
        ratings = self.ratings.all()
        self.rating_count = ratings.count()
        self.rating_sum = sum(r.rating for r in ratings)
        self.save()

    @property
    def is_available(self):
        """Check if theme is available for users to apply"""
        return self.is_official or (self.is_public and self.is_public_verified)


class UserTheme(models.Model):
    """
    Stores a user's current theme configuration.
    Can either use a preset or custom colors.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='theme')
    active_preset = models.ForeignKey(
        ThemePreset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users_using'
    )
    is_using_preset = models.BooleanField(default=True)

    # Custom color overrides (nullable - only used if is_using_preset=False)
    custom_primary_color = models.CharField(max_length=7, null=True, blank=True)
    custom_secondary_color = models.CharField(max_length=7, null=True, blank=True)
    custom_background_color = models.CharField(max_length=7, null=True, blank=True)
    custom_text_color = models.CharField(max_length=7, null=True, blank=True)
    custom_text_head_color = models.CharField(max_length=7, null=True, blank=True)
    custom_navbar_bg = models.CharField(max_length=7, null=True, blank=True)
    custom_navbar_text = models.CharField(max_length=7, null=True, blank=True)

    # Custom button colors
    custom_btn_success_bg = models.CharField(max_length=7, null=True, blank=True)
    custom_btn_success_text = models.CharField(max_length=7, null=True, blank=True)
    custom_btn_danger_bg = models.CharField(max_length=7, null=True, blank=True)
    custom_btn_danger_text = models.CharField(max_length=7, null=True, blank=True)
    custom_btn_warning_bg = models.CharField(max_length=7, null=True, blank=True)
    custom_btn_warning_text = models.CharField(max_length=7, null=True, blank=True)
    custom_btn_info_bg = models.CharField(max_length=7, null=True, blank=True)
    custom_btn_info_text = models.CharField(max_length=7, null=True, blank=True)
    custom_btn_secondary_bg = models.CharField(max_length=7, null=True, blank=True)
    custom_btn_secondary_text = models.CharField(max_length=7, null=True, blank=True)

    # Custom card colors
    custom_card_bg_color = models.CharField(max_length=7, null=True, blank=True)
    custom_card_header_bg_color = models.CharField(max_length=7, null=True, blank=True)
    custom_card_text_color = models.CharField(max_length=7, null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s theme"

    def get_colors(self):
        """
        Returns a dictionary of color values.
        Uses preset if is_using_preset=True, otherwise uses custom colors.
        """
        if self.is_using_preset and self.active_preset:
            return {
                'primary_color': self.active_preset.primary_color,
                'secondary_color': self.active_preset.secondary_color,
                'background_color': self.active_preset.background_color,
                'text_color': self.active_preset.text_color,
                'text_head_color': self.active_preset.text_head_color,
                'navbar_bg': self.active_preset.navbar_bg,
                'navbar_text': self.active_preset.navbar_text,
                'btn_success_bg': self.active_preset.btn_success_bg,
                'btn_success_text': self.active_preset.btn_success_text,
                'btn_danger_bg': self.active_preset.btn_danger_bg,
                'btn_danger_text': self.active_preset.btn_danger_text,
                'btn_warning_bg': self.active_preset.btn_warning_bg,
                'btn_warning_text': self.active_preset.btn_warning_text,
                'btn_info_bg': self.active_preset.btn_info_bg,
                'btn_info_text': self.active_preset.btn_info_text,
                'btn_secondary_bg': self.active_preset.btn_secondary_bg,
                'btn_secondary_text': self.active_preset.btn_secondary_text,
                'card_bg_color': self.active_preset.card_bg_color,
                'card_header_bg_color': self.active_preset.card_header_bg_color,
                'card_text_color': self.active_preset.card_text_color,
            }
        else:
            # Use custom colors or defaults
            return {
                'primary_color': self.custom_primary_color or '#007bff',
                'secondary_color': self.custom_secondary_color or '#6c757d',
                'background_color': self.custom_background_color or '#ffffff',
                'text_color': self.custom_text_color or '#212529',
                'text_head_color': self.custom_text_head_color or '#000000',
                'navbar_bg': self.custom_navbar_bg or '#f8f9fa',
                'navbar_text': self.custom_navbar_text or '#000000',
                'btn_success_bg': self.custom_btn_success_bg or '#28a745',
                'btn_success_text': self.custom_btn_success_text or '#ffffff',
                'btn_danger_bg': self.custom_btn_danger_bg or '#dc3545',
                'btn_danger_text': self.custom_btn_danger_text or '#ffffff',
                'btn_warning_bg': self.custom_btn_warning_bg or '#ffc107',
                'btn_warning_text': self.custom_btn_warning_text or '#000000',
                'btn_info_bg': self.custom_btn_info_bg or '#17a2b8',
                'btn_info_text': self.custom_btn_info_text or '#ffffff',
                'btn_secondary_bg': self.custom_btn_secondary_bg or '#6c757d',
                'btn_secondary_text': self.custom_btn_secondary_text or '#ffffff',
                'card_bg_color': self.custom_card_bg_color or '#ffffff',
                'card_header_bg_color': self.custom_card_header_bg_color or '#f8f9fa',
                'card_text_color': self.custom_card_text_color or '#212529',
            }


class ThemeRating(models.Model):
    """
    Allows users to rate public themes.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='theme_ratings')
    theme = models.ForeignKey(ThemePreset, on_delete=models.CASCADE, related_name='ratings')
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Rating from 1 to 5 stars'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'theme')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} rated {self.theme.name}: {self.rating}/5"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update theme rating when a new rating is saved
        self.theme.update_rating()
