import logging
import boto3
from botocore.exceptions import ClientError
import os
import sys
import threading
from django.conf import settings


def upload_to_s3(file_obj, key):
    # Explicitly provide AWS credentials
    s3 = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_KEY,
        region_name=settings.AWS_REGION  # Optional, specify your region if needed
    )

    bucket = settings.S3_BUCKET
    try:
        s3.upload_fileobj(file_obj, bucket, key)
        region = s3.get_bucket_location(Bucket=bucket)['LocationConstraint']

        if region == 'us-east-1' or region is None:
            object_url = f"https://{bucket}.s3.amazonaws.com/{key}"
        else:
            object_url = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"

        return True, object_url
    except Exception as e:
        print("Error uploading file to S3:", str(e))
        return False, str(e)
