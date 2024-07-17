import boto3
import io
from PIL import Image
from io import BytesIO
from django.conf import settings

rekognition = boto3.client('rekognition', aws_access_key_id=settings.AWS_ACCESS_KEY,
                           aws_secret_access_key=settings.AWS_SECRET_KEY,
                           region_name=settings.AWS_REGION)
dynamodb = boto3.client('dynamodb', aws_access_key_id=settings.AWS_ACCESS_KEY,
                        aws_secret_access_key=settings.AWS_SECRET_KEY, region_name=settings.AWS_REGION)


def resize_image(image, max_size=(1024, 1024)):
    # Convert image to RGB if it's in a different mode
    if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
        image = image.convert('RGB')
    # Resize the image to fit within the specified max_size
    image.thumbnail(max_size, Image.LANCZOS)
    stream = BytesIO()
    image.save(stream, format="JPEG")
    return stream.getvalue()


def match_faces(image_data):
    image = Image.open(BytesIO(image_data))
    # Resize the image if necessary
    image_binary = resize_image(image)
    try:

        response = rekognition.search_faces_by_image(
            CollectionId=settings.AWS_REKOGNITION_COLLECTION_ID,
            Image={'Bytes': image_binary}
        )

        data = []
        if not response['FaceMatches']:
            return data
        for match in response['FaceMatches']:
            face = dynamodb.get_item(
                TableName=settings.AWS_DYNAMODB_TABLE_NAME,
                Key={'RekognitionId': {'S': match['Face']['FaceId']}}
            )

            if 'Item' in face:
                data.append({
                    'image_uuid': face['Item']['ObjectUUID']['S'],
                    'match': match['Face']['Confidence']
                })
        return data
    except Exception as e:
        print(str(e))
        return []
