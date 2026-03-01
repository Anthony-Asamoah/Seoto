import os

import boto3
from django.conf import settings
from django.core.management.base import BaseCommand

from foodie.models import meal

IMAGE_FIELDS = ['main_img', 'img_1', 'img_2', 'img_3']


class Command(BaseCommand):
    help = 'One-time migration of local foodie images to S3'

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

        meals = meal.objects.all()
        self.stdout.write(f'Processing {meals.count()} meals...\n')

        uploaded = skipped = missing = 0

        for m in meals:
            for field_name in IMAGE_FIELDS:
                field = getattr(m, field_name)
                if not field:
                    continue

                local_path = os.path.join(settings.MEDIA_ROOT, field.name)
                s3_key = f'{prefix}/{field.name}'

                if not os.path.exists(local_path):
                    self.stdout.write(
                        self.style.WARNING(f'  MISSING  [{m.name}] {field_name}: {local_path}')
                    )
                    missing += 1
                    continue

                # Check if already uploaded
                try:
                    s3.head_object(Bucket=bucket, Key=s3_key)
                    self.stdout.write(f'  SKIP     [{m.name}] {field_name} already in S3')
                    skipped += 1
                    continue
                except s3.exceptions.ClientError:
                    pass

                s3.upload_file(local_path, bucket, s3_key)
                self.stdout.write(
                    self.style.SUCCESS(f'  UPLOADED [{m.name}] {field_name} → s3://{bucket}/{s3_key}')
                )
                uploaded += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone. Uploaded: {uploaded}, Skipped: {skipped}, Missing: {missing}'
            )
        )
