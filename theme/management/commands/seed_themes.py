from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from theme.models import ThemePreset


class Command(BaseCommand):
    help = 'Seeds the database with 5 default official theme presets'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding default themes...')

        # Get or create system user for default themes
        system_user, created = User.objects.get_or_create(
            username='system',
            defaults={
                'email': 'system@seoto.com',
                'is_staff': True,
                'is_superuser': False,
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS('Created system user'))

        # Define the 5 official themes with all 18 colors
        themes_data = [
            {
                'name': 'Light',
                'description': 'Clean and modern light theme with blue accents - perfect for everyday use',
                'primary_color': '#007bff',
                'secondary_color': '#6c757d',
                'background_color': '#ffffff',
                'text_color': '#212529',
                'text_head_color': '#1a1a1a',
                'navbar_bg': '#f8f9fa',
                'navbar_text': '#000000',
                'btn_success_bg': '#28a745',
                'btn_success_text': '#ffffff',
                'btn_danger_bg': '#dc3545',
                'btn_danger_text': '#ffffff',
                'btn_warning_bg': '#ffc107',
                'btn_warning_text': '#000000',
                'btn_info_bg': '#17a2b8',
                'btn_info_text': '#ffffff',
                'card_bg_color': '#ffffff',
                'card_header_bg_color': '#f8f9fa',
                'card_text_color': '#212529',
            },
            {
                'name': 'Dark',
                'description': 'Easy on the eyes dark theme with purple highlights - ideal for night owls',
                'primary_color': '#9d4edd',
                'secondary_color': '#7209b7',
                'background_color': '#1a1a2e',
                'text_color': '#eaeaea',
                'text_head_color': '#ffffff',
                'navbar_bg': '#16213e',
                'navbar_text': '#ffffff',
                'btn_success_bg': '#3dd865',
                'btn_success_text': '#000000',
                'btn_danger_bg': '#ff4757',
                'btn_danger_text': '#ffffff',
                'btn_warning_bg': '#ffd93d',
                'btn_warning_text': '#000000',
                'btn_info_bg': '#48dbfb',
                'btn_info_text': '#000000',
                'card_bg_color': '#0f1419',
                'card_header_bg_color': '#16213e',
                'card_text_color': '#eaeaea',
            },
            {
                'name': 'High Contrast',
                'description': 'Maximum readability with high contrast colors - designed for accessibility',
                'primary_color': '#ffd60a',
                'secondary_color': '#ffc300',
                'background_color': '#000000',
                'text_color': '#ffffff',
                'text_head_color': '#ffffff',
                'navbar_bg': '#003566',
                'navbar_text': '#ffd60a',
                'btn_success_bg': '#00ff00',
                'btn_success_text': '#000000',
                'btn_danger_bg': '#ff0000',
                'btn_danger_text': '#ffffff',
                'btn_warning_bg': '#ffff00',
                'btn_warning_text': '#000000',
                'btn_info_bg': '#00ffff',
                'btn_info_text': '#000000',
                'card_bg_color': '#1a1a1a',
                'card_header_bg_color': '#003566',
                'card_text_color': '#ffffff',
            },
            {
                'name': 'Ocean',
                'description': 'Calming ocean-inspired theme with blues and teals - brings tranquility to your workspace',
                'primary_color': '#0077b6',
                'secondary_color': '#00b4d8',
                'background_color': '#caf0f8',
                'text_color': '#03045e',
                'text_head_color': '#023047',
                'navbar_bg': '#0096c7',
                'navbar_text': '#ffffff',
                'btn_success_bg': '#06d6a0',
                'btn_success_text': '#000000',
                'btn_danger_bg': '#e63946',
                'btn_danger_text': '#ffffff',
                'btn_warning_bg': '#ffd166',
                'btn_warning_text': '#000000',
                'btn_info_bg': '#118ab2',
                'btn_info_text': '#ffffff',
                'card_bg_color': '#ffffff',
                'card_header_bg_color': '#90e0ef',
                'card_text_color': '#03045e',
            },
            {
                'name': 'Forest',
                'description': 'Natural forest theme with earthy greens and browns - connect with nature',
                'primary_color': '#2d6a4f',
                'secondary_color': '#52b788',
                'background_color': '#d8f3dc',
                'text_color': '#1b4332',
                'text_head_color': '#081c15',
                'navbar_bg': '#40916c',
                'navbar_text': '#ffffff',
                'btn_success_bg': '#52b788',
                'btn_success_text': '#ffffff',
                'btn_danger_bg': '#d62828',
                'btn_danger_text': '#ffffff',
                'btn_warning_bg': '#fcbf49',
                'btn_warning_text': '#000000',
                'btn_info_bg': '#219ebc',
                'btn_info_text': '#ffffff',
                'card_bg_color': '#f1faee',
                'card_header_bg_color': '#95d5b2',
                'card_text_color': '#1b4332',
            },
        ]

        # Create each theme
        created_count = 0
        updated_count = 0

        for theme_data in themes_data:
            theme, created = ThemePreset.objects.update_or_create(
                name=theme_data['name'],
                is_official=True,
                defaults={
                    **theme_data,
                    'created_by': system_user,
                    'is_official': True,
                    'is_featured': True,
                    'is_public': False,
                    'is_public_verified': False,
                }
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Created theme: {theme.name}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'↻ Updated theme: {theme.name}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSeeding complete! Created: {created_count}, Updated: {updated_count}'
            )
        )
