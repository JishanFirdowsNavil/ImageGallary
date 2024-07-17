import logging
import boto3
from botocore.exceptions import ClientError
from django.conf import settings

# Explicitly provide AWS credentials
aws_access_key_id = settings.AWS_ACCESS_KEY
aws_secret_access_key = settings.AWS_SECRET_KEY
region_name = settings.AWS_REGION  # Optional, specify your region if needed

s3 = boto3.resource(
    's3',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=region_name
)


def delete_objects(links):
    """
    Removes a list of objects from a bucket.
    This operation is done as a batch in a single request.

    :param links: The list of object URLs to remove.
    :return: True if objects were deleted, False otherwise.
    """
    logger = logging.getLogger(__name__)
    bucket_name = settings.S3_BUCKET

    if not bucket_name:
        logger.error("Bucket name is not set in settings.")
        return False

    bucket = s3.Bucket(bucket_name)
    object_keys = []

    s3_r = boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name
    )

    try:
        region = s3_r.get_bucket_location(Bucket=bucket_name)['LocationConstraint']
    except ClientError as e:
        logger.error("Failed to get bucket location: %s", e)
        return False

    if region == 'us-east-1' or region is None:
        object_url = f"https://{bucket_name}.s3.amazonaws.com/"
    else:
        object_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/"

    for link in links:
        object_keys.append(link.replace(object_url, ""))

    try:
        response = bucket.delete_objects(
            Delete={"Objects": [{"Key": key} for key in object_keys]}
        )
        if "Deleted" in response:
            logger.info(
                "Deleted objects '%s' from bucket '%s'.",
                [del_obj["Key"] for del_obj in response["Deleted"]],
                bucket.name,
            )
            return True
        if "Errors" in response:
            logger.warning(
                "Could not delete objects '%s' from bucket '%s'.",
                [
                    f"{del_obj['Key']}: {del_obj['Code']}"
                    for del_obj in response["Errors"]
                ],
                bucket.name,
            )
            return False
    except ClientError:
        logger.exception("Couldn't delete any objects from bucket %s.", bucket.name)
        return False
