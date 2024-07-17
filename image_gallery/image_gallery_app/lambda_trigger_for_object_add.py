from __future__ import print_function
import boto3
from decimal import Decimal
import json
import urllib.parse

print('Loading function')

dynamodb = boto3.client('dynamodb')
s3 = boto3.client('s3')
rekognition = boto3.client('rekognition')


# --------------- Helper Functions ------------------

def index_faces(bucket, key):
    response = rekognition.index_faces(
        Image={"S3Object": {"Bucket": bucket, "Name": key}},
        CollectionId="facerecognition_collection"
    )
    return response


def update_index(tableName, faceId, objectUUID):
    response = dynamodb.put_item(
        TableName=tableName,
        Item={
            'RekognitionId': {'S': faceId},
            'ObjectUUID': {'S': objectUUID}
        }
    )


# --------------- Main handler ------------------

def lambda_handler(event, context):
    # Get the object from the event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    # Decode the S3 object key
    key = urllib.parse.unquote_plus(key)
    print("Decoded Key: ", key)

    try:
        # Calls Amazon Rekognition IndexFaces API to detect faces in S3 object
        # to index faces into specified collection
        response = index_faces(bucket, key)

        # Commit faceId and object UUID to DynamoDB
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            faceId = response['FaceRecords'][0]['Face']['FaceId']
            objectUUID = key.split('/')[-1].split('.')[0]  # Extracting UUID from the object key

            update_index('facerecognition', faceId, objectUUID)

        # Print response to console
        print(response)

        return response
    except Exception as e:
        print(e)
        print("Error processing object {} from bucket {}. ".format(key, bucket))
        raise e
