import os
import boto3
from os.path import  join, dirname
from dotenv import load_dotenv
import json

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_REGION_NAME = os.environ.get("AWS_REGION_NAME")

dynamodb = boto3.client(
        "dynamodb",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION_NAME
    )

s3 = boto3.resource(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION_NAME
    )

def set_data_in_dynamo_db(item):

    try:
        dynamodb.put_item(TableName="Users", Item=item)
        return {'success': True }
    
    except Exception as e:
        print("Some error occured while setting data in dynamodb: ", e)
        return {'success': False, 'error': e}

def get_data_from_dynamo_db(item):

    try:    
        response = dynamodb.query(TableName="Users", 
                                    KeyConditionExpression='Username = :username', 
                                    ExpressionAttributeValues={
                                    ':username': item
                                    }
                                )
        if response and response["Items"]:
            if len(response["Items"]) == 0:
                return {"error": "Username not found.", "success": False}
            elif len(response["Items"]) == 1:
                user = response["Items"][0]
                del user["Password"]
                return {"user": user, "success": True}
            elif len(response["Items"]) > 1:
                return {"error": "Username already exists.", "success": False}
        else:
            return {"success": False, "error": "Some error occured"}
    except Exception as e:
        print("Some error occured while getting data from dynamodb: ", e)
        return {'success': False, 'error': e}


def get_all_data():

    try:    
        response = dynamodb.scan(TableName="Users")
        if response and response["Items"]:
            return {"users": response["Items"], "success": True}
        else:
            return {"success": False, "error": "Some error occured"}
    except Exception as e:
        print("Some error occured while getting data from dynamodb: ", e)
        return {'success': False, 'error': e}