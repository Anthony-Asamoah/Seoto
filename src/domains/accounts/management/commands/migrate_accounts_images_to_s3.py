import os

import boto3
from django.conf import settings
from django.core.management.base import BaseCommand

from domains.accounts.models import user_profile

IMAGE_FIELDS = ['picture']


class Command(BaseCommand):
    help = 'One-time migration of local accounts images to S3'

    def handle(self, *args, **kwargs):
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        prefix = settings.AWS_S3_BUCKET_PREFIX.rstrip('/')
        region = settings.AWS_S3_REGION_NAME

        s3 = boto3.client(
            's3',
            region_name=region,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

        profiles = user_profile.objects.select_related('user').all()
        self.stdout.write(f'Processing {profiles.count()} profiles...\n')

        uploaded = skipped = missing = 0

        for profile in profiles:
            for field_name in IMAGE_FIELDS:
                field = getattr(profile, field_name)
                if not field:
                    continue

                local_path = os.path.join(settings.MEDIA_ROOT, field.name)
                s3_key = f'{prefix}/{field.name}'

                if not os.path.exists(local_path):
                    self.stdout.write(
                        self.style.WARNING(f'  MISSING  [{profile.user.username}] {field_name}: {local_path}')
                    )
                    missing += 1
                    continue

                # Check if already uploaded
                try:
                    s3.head_object(Bucket=bucket, Key=s3_key)
                    self.stdout.write(f'  SKIP     [{profile.user.username}] {field_name} already in S3')
                    skipped += 1
                    continue
                except s3.exceptions.ClientError:
                    pass

                s3.upload_file(local_path, bucket, s3_key)
                self.stdout.write(
                    self.style.SUCCESS(f'  UPLOADED [{profile.user.username}] {field_name} → s3://{bucket}/{s3_key}')
                )
                uploaded += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone. Uploaded: {uploaded}, Skipped: {skipped}, Missing: {missing}'
            )
        )
