import os

import boto3
from django.conf import settings
from django.core.management.base import BaseCommand

from author.models import Intro

IMAGE_FIELDS = ['profile_image']


class Command(BaseCommand):
    help = 'One-time migration of local author images to S3'

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

        intros = Intro.objects.all()
        self.stdout.write(f'Processing {intros.count()} author profiles...\n')

        uploaded = skipped = missing = 0

        for intro in intros:
            for field_name in IMAGE_FIELDS:
                field = getattr(intro, field_name)
                if not field:
                    continue

                local_path = os.path.join(settings.MEDIA_ROOT, field.name)
                s3_key = f'{prefix}/{field.name}'

                if not os.path.exists(local_path):
                    self.stdout.write(
                        self.style.WARNING(f'  MISSING  [{intro.first_name} {intro.last_name}] {field_name}: {local_path}')
                    )
                    missing += 1
                    continue

                # Check if already uploaded
                try:
                    s3.head_object(Bucket=bucket, Key=s3_key)
                    self.stdout.write(f'  SKIP     [{intro.first_name} {intro.last_name}] {field_name} already in S3')
                    skipped += 1
                    continue
                except s3.exceptions.ClientError:
                    pass

                s3.upload_file(local_path, bucket, s3_key)
                self.stdout.write(
                    self.style.SUCCESS(f'  UPLOADED [{intro.first_name} {intro.last_name}] {field_name} → s3://{bucket}/{s3_key}')
                )
                uploaded += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone. Uploaded: {uploaded}, Skipped: {skipped}, Missing: {missing}'
            )
        )
