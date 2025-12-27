from django.core.management.base import BaseCommand
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64


class Command(BaseCommand):
    help = 'Generate VAPID keys for web push notifications'

    def handle(self, *args, **options):
        # Generate private key
        private_key = ec.generate_private_key(ec.SECP256R1())

        # Get public key
        public_key = private_key.public_key()

        # Serialize private key to PEM format
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # Serialize public key to PEM format
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        # Convert to base64 URL-safe format for VAPID
        private_key_base64 = base64.urlsafe_b64encode(private_pem).decode('utf-8').rstrip('=')
        public_key_base64 = base64.urlsafe_b64encode(public_pem).decode('utf-8').rstrip('=')

        self.stdout.write(self.style.SUCCESS('\nVAPID Keys Generated Successfully!\n'))
        self.stdout.write('Add these to your .env file:\n')
        self.stdout.write(f'VAPID_PUBLIC_KEY={public_key_base64}')
        self.stdout.write(f'VAPID_PRIVATE_KEY={private_key_base64}')
        self.stdout.write('VAPID_ADMIN_EMAIL=admin@seoto.pythonanywhere.com\n')
