from django.core.management.base import BaseCommand
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64


class Command(BaseCommand):
    help = 'Generate VAPID keys for web push notifications'

    def handle(self, *args, **options):
        # Generate EC private key using SECP256R1 curve (P-256)
        private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())

        # Get public key
        public_key = private_key.public_key()

        # Serialize private key to PEM format (for storage)
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        # Get public key in uncompressed point format (required for Web Push)
        # This is 65 bytes: 0x04 + X (32 bytes) + Y (32 bytes)
        public_numbers = public_key.public_numbers()
        x = public_numbers.x.to_bytes(32, 'big')
        y = public_numbers.y.to_bytes(32, 'big')
        uncompressed_public_key = b'\x04' + x + y

        # Convert to base64url without padding (required for VAPID)
        public_key_base64 = base64.urlsafe_b64encode(uncompressed_public_key).decode('utf-8').rstrip('=')

        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('VAPID Keys Generated Successfully!'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

        self.stdout.write(self.style.WARNING('Add these to your .env file:\n'))
        self.stdout.write(f'\nVAPID_PRIVATE_KEY="{private_pem.strip()}"')
        self.stdout.write(f'\nVAPID_PUBLIC_KEY={public_key_base64}')
        self.stdout.write(f'\nVAPID_ADMIN_EMAIL=admin@seoto.org\n')

        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('IMPORTANT NOTES:'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write('1. The public key is in base64url format (65 bytes uncompressed EC point)')
        self.stdout.write('2. Copy the ENTIRE private key including BEGIN/END lines')
        self.stdout.write('3. Keep the private key in quotes in .env file')
        self.stdout.write('4. Update both local .env and PythonAnywhere environment variables')
        self.stdout.write('5. Restart your web app after updating environment variables')
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))
