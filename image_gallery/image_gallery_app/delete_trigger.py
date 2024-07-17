from __future__ import print_function
import boto3
import urllib.parse
from boto3.dynamodb.conditions import Key
import json

print('Loading function')

dynamodb = boto3.resource('dynamodb')
rekognition = boto3.client('rekognition')


def delete_face_from_rekognition(faceId, collectionId="facerecognition_collection"):
    response = rekognition.delete_faces(
        CollectionId=collectionId,
        FaceIds=[faceId]
    )
    return response


def delete_item_from_dynamodb(tableName, objectUUID):
    # Fetch the faceId associated with the objectUUID
    try:
        table = dynamodb.Table(tableName)
        response = table.query(
            IndexName='ObjectUUID-index',
            KeyConditionExpression=Key('ObjectUUID').eq(objectUUID),
        )

        if response['Items']:
            for item in response['Items']:
                faceId = item['RekognitionId']
                # Delete the face from Rekognition collection
                delete_face_from_rekognition(faceId)
                # Delete the item from DynamoDB
                table.delete_item(
                    Key={'RekognitionId': item['RekognitionId']}
                )
    except Exception as e:
        print(e)
        print("Error processing deletion for table {} from object {}. ".format(tableName, objectUUID))
        raise e


def lambda_handler(event, context):
    # Get the object from the event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    # Decode the S3 object key
    key = urllib.parse.unquote_plus(key)
    print("Decoded Key: ", key)

    try:
        # Extract UUID from the object key
        objectUUID = key.split('/')[-1].split('.')[0]
        print(objectUUID)
        # Fetch faceId associated with the objectUUID from DynamoDB
        # Delete associated data from DynamoDB and Rekognition
        delete_item_from_dynamodb('facerecognition', objectUUID)

        print("Deleted associated data for key: ", key)
        return {
            'statusCode': 200,
            'body': json.dumps('Delete operation successful')
        }
    except Exception as e:
        print(e)
        print("Error processing deletion for object {} from bucket {}. ".format(key, bucket))
        raise e
