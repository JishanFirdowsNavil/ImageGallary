# Image Gallery App

## Setup Instructions

### 1. Create the .env File

Create a `.env` file in the root directory of your project to store your environment variables securely. This file should contain the following variables:
```
AWS_ACCESS_KEY=
AWS_DYNAMODB_TABLE_NAME=
AWS_REGION=
AWS_REKOGNITION_COLLECTION_ID=
AWS_SECRET_KEY=
EMAIL_HOST_PASSWORD=
EMAIL_HOST_USER=
MY_S3_BUCKET=
EMAIL_HOST=
DB_USER=
DB_PASSWORD=
DB_PORT=
DB_DATABASE=
DB_HOST=
```
## You must install redis
To install Redis on your server, follow these steps:

On Ubuntu/Debian
Update your package list:
```shell
sudo apt update
```
Install Redis:
```shell
sudo apt install redis-server
```
Start the Redis service and enable it to start on boot:
```shell
sudo systemctl start redis-server
sudo systemctl enable redis-server
```
On CentOS/RHEL
Add the EPEL repository:

```shell
sudo yum install epel-release
```
Install Redis:
```shell
sudo yum install redis
```
Start the Redis service and enable it to start on boot:
```shell
sudo systemctl start redis
sudo systemctl enable redis
```
Verify Redis is running:
```shell
redis-cli ping
```
You should see PONG as the response.


1. Lambda Trigger for S3 File Upload
Create a Lambda function that will be triggered when a new object is added to your S3 bucket. Save the code for this Lambda function as lambda_trigger_for_s3_object_add.py in the image_gallery_app folder.

Note: Ensure to change the table name and Rekognition collection according to your setup.

2. Lambda Trigger for S3 File Deletion
Create another Lambda function that will be triggered when an object is deleted from your S3 bucket. Save the code for this Lambda function as delete_object_s3.py in the image_gallery_app folder.

Note: Ensure to change the table name and Rekognition collection according to your setup.

## Usage
These Lambda functions will automatically handle the processing of images added to and deleted from your S3 bucket:

> - When an image is uploaded to the S3 bucket, the lambda_trigger_for_s3_object_add.py function will analyze the image using AWS Rekognition and store the detected labels in DynamoDB.
> - When an image is deleted from the S3 bucket, the delete_object_s3.py function will remove the corresponding entry from DynamoDB.

