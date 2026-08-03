import io

import qrcode
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django_otp.plugins.otp_totp.models import TOTPDevice


class Command(BaseCommand):
    help = (
        'Enrol a TOTP device (Google Authenticator, 1Password, Authy, ...) for a user so '
        'they can sign in to the admin. Prints a QR code to scan.'
    )

    def add_arguments(self, parser):
        parser.add_argument('username', help='Username of the account to enrol.')
        parser.add_argument('--name', default='Authenticator', help='Label for the device.')
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete any existing device with the same name and issue a fresh secret.',
        )
        parser.add_argument(
            '--noinput',
            action='store_true',
            help='Trust the device immediately instead of asking for a code to prove it works.',
        )
        parser.add_argument(
            '--light-terminal',
            action='store_true',
            help='Draw the QR code for a light background instead of a dark one.',
        )

    def handle(self, *args, **options):
        user_model = get_user_model()
        username = options['username']
        name = options['name']

        try:
            user = user_model.objects.get(**{user_model.USERNAME_FIELD: username})
        except user_model.DoesNotExist:
            raise CommandError(f'No user named {username!r}.')

        existing = TOTPDevice.objects.filter(user=user, name=name)
        if existing.exists():
            if not options['reset']:
                raise CommandError(
                    f'{user} already has a device named {name!r}. '
                    f'Pass --reset to replace it, or --name to add a second one.'
                )
            existing.delete()

        device = TOTPDevice.objects.create(user=user, name=name, confirmed=options['noinput'])

        self.stdout.write(self._qrcode(device.config_url, invert=not options['light_terminal']))
        self.stdout.write(f'Setup URL: {device.config_url}\n')

        if not options['noinput']:
            token = input('Enter the code your app is showing now (blank to abort): ').strip()
            if not device.verify_token(token):
                device.delete()
                raise CommandError('That code did not match — nothing was saved. Run the command again.')
            device.confirmed = True
            device.save(update_fields=['confirmed'])

        self.stdout.write(self.style.SUCCESS(f'TOTP device {name!r} is now active for {user}.'))

        if not user.is_staff:
            self.stdout.write(self.style.WARNING(f'Note: {user} is not staff, so the admin stays closed to them.'))

        self.stdout.write(
            f'Generate emergency single-use codes with: '
            f'python manage.py addstatictoken {username}'
        )

    @staticmethod
    def _qrcode(data, invert):
        qr = qrcode.QRCode(border=2)
        qr.add_data(data)
        buffer = io.StringIO()
        qr.print_ascii(out=buffer, invert=invert)
        return buffer.getvalue()
