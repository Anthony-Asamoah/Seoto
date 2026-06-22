from django.core.management.base import BaseCommand, CommandError
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64


def _b64url(raw_bytes):
    """base64url without padding (required for VAPID)."""
    return base64.urlsafe_b64encode(raw_bytes).decode('utf-8').rstrip('=')


def _private_key_raw(private_key):
    """Raw base64url of the 32-byte EC private scalar (env-safe, single line)."""
    private_value = private_key.private_numbers().private_value
    return _b64url(private_value.to_bytes(32, 'big'))


def _public_key_raw(public_key):
    """Uncompressed EC point (0x04 + X + Y) as base64url, required for Web Push."""
    numbers = public_key.public_numbers()
    uncompressed = b'\x04' + numbers.x.to_bytes(32, 'big') + numbers.y.to_bytes(32, 'big')
    return _b64url(uncompressed)


class Command(BaseCommand):
    help = 'Generate VAPID keys for web push notifications (raw base64url, env-safe)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--from-pem',
            dest='from_pem',
            metavar='PATH',
            help='Convert an existing PKCS8 PEM private key to raw base64url instead of '
                 'generating a new keypair. Preserves the keypair so existing browser '
                 'subscriptions keep working.',
        )

    def handle(self, *args, **options):
        from_pem = options.get('from_pem')

        if from_pem:
            try:
                with open(from_pem, 'rb') as f:
                    private_key = serialization.load_pem_private_key(
                        f.read(), password=None, backend=default_backend()
                    )
            except (OSError, ValueError) as e:
                raise CommandError(f'Could not load PEM private key from {from_pem!r}: {e}')
            converting = True
        else:
            private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
            converting = False

        private_key_base64 = _private_key_raw(private_key)
        public_key_base64 = _public_key_raw(private_key.public_key())

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS(
            'VAPID Key Converted!' if converting else 'VAPID Keys Generated Successfully!'
        ))
        self.stdout.write(self.style.SUCCESS('=' * 60 + '\n'))

        self.stdout.write(self.style.WARNING('Add these to your .env file:\n'))
        self.stdout.write(f'\nVAPID_PRIVATE_KEY={private_key_base64}')
        self.stdout.write(f'\nVAPID_PUBLIC_KEY={public_key_base64}')
        self.stdout.write(f'\nVAPID_ADMIN_EMAIL=admin@seoto.org\n')

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('IMPORTANT NOTES:'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('1. Both keys are single-line base64url — safe for .env / PythonAnywhere / Vercel.')
        self.stdout.write('2. No quotes or BEGIN/END lines needed.')
        if converting:
            self.stdout.write('3. Converted from your existing PEM — VAPID_PUBLIC_KEY is unchanged, '
                              'so existing subscriptions keep working.')
        else:
            self.stdout.write('3. This is a NEW keypair — existing subscriptions must re-subscribe.')
        self.stdout.write('4. Update local .env, PythonAnywhere, and Vercel environment variables.')
        self.stdout.write('5. Restart your web app after updating environment variables.')
        self.stdout.write(self.style.SUCCESS('=' * 60 + '\n'))
