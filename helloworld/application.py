#!flask/bin/python
from flask import Flask, render_template, request, redirect
from flask_cors import CORS
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
from os.path import  join, dirname
from dotenv import load_dotenv
import flask
import os
import uuid
import rsa
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    get_jwt,
    jwt_required,
    JWTManager,
    verify_jwt_in_request
)
import json
import random
import boto3

from helloworld.flaskrun import flaskrun
import logging

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

app = Flask(__name__)

logging.basicConfig(filename='FLASK_BACKEND.log', level=logging.DEBUG, format=f'%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

jwt = JWTManager(app)

cors = CORS(app, allow_headers=[
    "Content-Type", "Authorization", "Access-Control-Allow-Credentials", "withCredentials", "Access-Control-Allow-Origin"],
            supports_credentials=True, resources={r"/*": {"origins": "*"}})

AWS_SECRET_ACCESS_KEY = "AKIA2HA3C4EPQI2TDR5B"
AWS_ACCESS_KEY_ID = "525cvr4FPKr/3l7jYxmRAcM0XFP56EeKczChE33D"
AWS_REGION_NAME = "us-east-1"

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
    
def parse_user(user_obj):
    
    temp = {}
    temp["role"] = user_obj["Role"]["S"]
    temp["occupied"] = user_obj["Occupied"]["BOOL"]
    temperature = user_obj["AC"]["M"]["temperature"]["S"] if "temperature" in user_obj["AC"]["M"] else ''
    fan_level = user_obj["AC"]["M"]["fanLevel"]["S"] if "fanLevel" in user_obj["AC"]["M"] else ''
    temp_ac = {"temperature": temperature, "fan_level": fan_level}
    temp["AC"] = temp_ac
    issues =  user_obj["Issues"]["L"]
    issue_list = []
    for issue in issues:
        issue_obj = issue["M"]["issue"]["S"] if "issue" in issue["M"] else ''
        id = issue["M"]["id"]["S"] if "id" in issue["M"] else ''
        t = {"issue": issue_obj, "id": id}
        issue_list.append(t)
    temp["issues"] = issue_list
    temp["floor_number"] =  user_obj["FloorNumber"]["S"]
    temp["room_number"] =  user_obj["RoomNumber"]["S"]
    temp["id"] =  user_obj["ID"]["S"]
    devices = user_obj["Devices"]["L"]
    devices_list = []
    for device in devices:
        wattage = device["M"]["wattage"]["S"] if "wattage" in device["M"] else ''
        device_name = device["M"]["device_name"]["S"] if "device_name" in device["M"] else ''
        status = device["M"]["status"]["BOOL"] if "status" in device["M"] else ''
        device_id = device["M"]["id"]["S"] if "id" in device["M"] else ''
        t = {"wattage": wattage, "device_name": device_name, "status": status, "id": device_id}
        devices_list.append(t)
    temp["devices"] =  devices_list
    temp["username"] = user_obj["Username"]["S"]
    temp["locked"] = user_obj["Locked"]["BOOL"]

    return temp

@app.route('/', methods=['GET'])
def index():
    return redirect("http://smart-hotel-static.s3-website-us-east-1.amazonaws.com")

@app.route('/api/login/', methods=['POST'])
def login():
    from helloworld.aws import get_all_data, get_data_from_dynamo_db

    post_data = json.loads(request.data)
    username = post_data["userName"]
    password = post_data["password"]
    role = post_data["role"]

    public_key, private_key = rsa.newkeys(512)
    encoded_password = rsa.encrypt(password.encode(),public_key)

    floor_number = random.randint(1, 20)

    room_number_l = floor_number * 100
    room_number_r = room_number_l + 100

    room_number = random.randint(room_number_l, room_number_r)

    id_ = str(uuid.uuid4())
    put_user_item  = {
        'ID': {'S': id_},
        'Username': {'S': username },
        'RoomNumber': {'S': str(room_number)},
        'FloorNumber': {'S': str(floor_number)},
        'Password': {'S': str(encoded_password) },
        'Locked': {'BOOL': True},
        'Devices': {'L': []},
        'Issues': {'L': []},
        'Occupied': {'BOOL': True},
        'AC': {'M': {}},
        'Role': {'S': role }
    }

    fetch_item = {'S': username }
    fetch_response = get_data_from_dynamo_db(fetch_item)
    if fetch_response["success"]:
        user = fetch_response["user"]
        access_token = create_access_token(identity=user["Username"], fresh=True)
        refresh_token = create_refresh_token(user["Username"])
        user = parse_user(user)
        u_list = []
        if role == "staff":
            all_data = get_all_data()
            all_users = all_data["users"]
            for user_obj in all_users:
                temp = parse_user(user_obj)
                u_list.append(temp)
        
        if user["role"] != role:
            error = "You dont have the correct role assigned."
            return flask.jsonify(ok=False, error=error)
        return flask.jsonify(ok=True, user=user, access=access_token, refresh=refresh_token, all_data=u_list)
    # else:
    #     return flask.jsonify(ok=False, error=fetch_response["error"])
    else:
        try:
            dynamodb.put_item(TableName="Users", Item=put_user_item)
            return flask.jsonify(ok=True, success=True)
    
        except Exception as e:
            print("Some error occured while setting data in dynamodb: ", e)
            # "Some error occured."
            return flask.jsonify(ok=False, error=json.dumps(e))

@jwt_required()
@app.route('/api/users/change_ac_settings/', methods=['PATCH'])
def change_ac_settings():

    current_user = get_jwt_identity()
    key = {"Username": current_user}

    user = dynamodb.get_item(TableName="Users", Key=key)
    user_data = user["Item"]    

    post_data = json.loads(request.data)
    
    expression_attribute_name = {}
    update_expression = {}
    if post_data["temperature"] and post_data["fanLevel"]:
        expression_attribute_name = {
            '#k': 'AC',
            '#k1': 'fanLevel',
            '#k2': 'temperature'
        }
        expression_attribute_value = {
            ':obj1': {"S": post_data["fanLevel"] },
            ':obj2': {"S": post_data["temperature"] }
        }
        update_expression = 'SET #k.#k1 = :obj1, #k.#k2 = :obj2'
    elif post_data["fanLevel"]:
        expression_attribute_name = {
            '#k': 'AC',
            '#k1': 'fanLevel',
        }
        expression_attribute_value = {
            ':obj': {"S": post_data["fanLevel"] },
        }
        update_expression = 'SET #k.#k1 = :obj'
    elif post_data["temperature"]:
        expression_attribute_name = {
            '#k': 'AC',
            '#k1': 'fanLevel',
        }
        expression_attribute_value = {
            ':obj': {"S": post_data["temperature"] },
        }
        update_expression = 'SET #k.#k1 = :obj'
    try:
        dynamodb.update_item(
            TableName="Users",
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_name,
            ExpressionAttributeValues=expression_attribute_value,
            ReturnValues="UPDATED_NEW"
        )
    
        user = dynamodb.get_item(TableName="Users", Key=key)
        user_data = user["Item"]
        user = parse_user(user_data)
        del user_data["Password"]
        return flask.jsonify(ok=True, user=user)

    except Exception as e:
        print("Some error occured while updating data from dynamodb: ", e)
        return flask.jsonify(ok=False, is_logged_in=False, error=json.dumps(e))

@jwt_required()
@app.route('/api/users/add_devices/', methods=['POST'])
def add_device():
    from helloworld.aws import get_all_data

    current_user = get_jwt_identity()
    key = {"Username": current_user}

    user = dynamodb.get_item(TableName="Users", Key=key)
    user_data = user["Item"]    

    post_data = json.loads(request.data)

    device_id = str(uuid.uuid4())

    new_device = {"L": [{
        "M": {
            "wattage": {"S": post_data["wattage"] },
            "device_name": {"S": post_data["deviceName"] },
            "status": {"BOOL": False },
            "id": {"S": device_id },
        }
    }]}
    
    try:
        dynamodb.update_item(
            TableName="Users",
            Key=key,
            UpdateExpression="SET Devices=list_append(Devices, :obj)",
            ExpressionAttributeValues={
                ":obj": new_device,
            },
            ReturnValues="UPDATED_NEW"
        )
    
        user = dynamodb.get_item(TableName="Users", Key=key)
        user_data = user["Item"]
        user = parse_user(user_data)
        del user_data["Password"]
        return flask.jsonify(ok=True, user=user)

    except Exception as e:
        print("Some error occured while updating data from dynamodb: ", e)
        return flask.jsonify(ok=False, is_logged_in=False, error=json.dumps(e))

@jwt_required()
@app.route('/api/users/add_issues/', methods=['POST'])
def add_issue():
    from helloworld.aws import get_all_data

    current_user = get_jwt_identity()
    key = {"Username": current_user}

    user = dynamodb.get_item(TableName="Users", Key=key)
    user_data = user["Item"]    

    post_data = json.loads(request.data)

    issue_id = str(uuid.uuid4())

    new_issue = {"L": [{
        "M": {
            "issue": {"S": post_data["issue"] },
            "id": {"S": issue_id },
        }
    }]}
    
    try:
        dynamodb.update_item(
            TableName="Users",
            Key=key,
            UpdateExpression="SET Issues=list_append(Issues, :obj)",
            ExpressionAttributeValues={
                ":obj": new_issue,
            },
            ReturnValues="UPDATED_NEW"
        )
    
        user = dynamodb.get_item(TableName="Users", Key=key)
        user_data = user["Item"]
        user = parse_user(user_data)
        del user_data["Password"]
        return flask.jsonify(ok=True, user=user)

    except Exception as e:
        print("Some error occured while updating data from dynamodb: ", e)
        return flask.jsonify(ok=False, is_logged_in=False, error=json.dumps(e))

@jwt_required(refresh=True)
@app.route('/api/users/token/refresh/', methods=['POST'])
def refresh_token():
    current_user = get_jwt_identity()
    access_token = create_access_token(identity=current_user, fresh=False)
    
    return flask.jsonify(ok=True, access=access_token)    

@app.route('/api/users/logout/', methods=['GET'])
def logout():
    pass

@jwt_required()
@app.route('/api/users/is_authenticated/', methods=['GET'])
def is_authenticated():
    
    from helloworld.aws import get_all_data

    current_user = get_jwt_identity()
    user = None

    key = {
        'Username': current_user
    }

    try:
        user = dynamodb.get_item(TableName="Users", Key=key)
        user_data = user["Item"]
        user = parse_user(user_data)
        u_list = []
        if user["role"] == "staff":
            all_data = get_all_data()
            all_users = all_data["users"]
            for user_obj in all_users:
                temp = parse_user(user_obj)
                u_list.append(temp)
        del user_data["Password"]

    except Exception as e:
        print("Some error occured while getting data from dynamodb: ", e)
        return flask.jsonify(ok=False, is_logged_in=False, error=e) 
    if user:
        return flask.jsonify(ok=True, is_logged_in=True, user=user, all_data=u_list)
    else:
        return flask.jsonify(ok=False, is_logged_in=False)

@jwt_required()
@app.route('/api/users/change_room_status/', methods=['PATCH'])
def change_room_status():
    
    from helloworld.aws import get_all_data

    post_data = json.loads(request.data)

    occupancy = request.args.get('occupancy')
    locked = request.args.get('locked')

    update_expression = ''
    if occupancy:
        update_expression = 'set Occupied = :status'
    elif locked:
        update_expression = 'set Locked = :status'

    status = post_data["status"]

    current_user = get_jwt_identity()
    
    key = {"Username": current_user}

    user = dynamodb.get_item(TableName="Users", Key=key)
    user_data = user["Item"]
    user_obj = parse_user(user_data)
    del user_data["Password"]
    
    devices = user_obj["devices"]
    status_obj = False
    if locked:
        if status == False:
            status_obj = True

        if len(devices) > 0:
            d_obj = {"L": []}
            for device in devices:
                d_obj["L"].append({
                    "M": {
                    "wattage": {"S": device["wattage"] },
                    "device_name": {"S": device["device_name"] },
                    "status": {"BOOL": status_obj },
                    "id": {"S": device["id"] },
                    }
                })
            dynamodb.update_item(
                TableName="Users",
                Key=key,
                UpdateExpression="SET Devices=:devices",
                ExpressionAttributeValues={
                    ":devices": d_obj,
                },
                ReturnValues="UPDATED_NEW"
            )
    try:
        dynamodb.update_item(
            TableName="Users",
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeValues={
                ':status': {"BOOL": status},
            },
            ReturnValues="UPDATED_NEW"
        )
        
        user = dynamodb.get_item(TableName="Users", Key=key)
        user_data = user["Item"]
        user = parse_user(user_data)
        del user_data["Password"]

        u_list = []
        if user["role"] == "staff":
            all_data = get_all_data()
            all_users = all_data["users"]
            for user_obj in all_users:
                temp = parse_user(user_obj)
                u_list.append(temp)

        return flask.jsonify(ok=True, user=user, all_data=u_list)

    except Exception as e:
        print("Some error occured while updating data from dynamodb: ", e)
        return flask.jsonify(ok=False, is_logged_in=False, error=e)
    
@jwt_required()
@app.route('/api/users/all_devices/', methods=['GET'])
def all_devices():

    current_user = get_jwt_identity()

    key = {"Username": current_user}

    user = dynamodb.get_item(TableName="Users", Key=key)
    user_data = user["Item"]
    user = parse_user(user_data)

    return flask.jsonify(ok=True, devices=user["devices"])


@jwt_required()
@app.route('/api/users/change_device_status/', methods=['PATCH'])
def change_device_status():
    
    from helloworld.aws import get_all_data

    post_data = json.loads(request.data)

    devices = post_data["deviceList"]

    current_user = get_jwt_identity()

    d_obj = {"L": []}
    for device in devices:
        d_obj["L"].append({
            "M": {
            "wattage": {"S": device["wattage"] },
            "device_name": {"S": device["device_name"] },
            "status": {"BOOL": device["status"] },
            "id": {"S": device["id"] },
        }
        })
    key = {"Username": current_user}

    try:
        dynamodb.update_item(
            TableName="Users",
            Key=key,
            UpdateExpression="SET Devices=:devices",
            ExpressionAttributeValues={
                ":devices": d_obj,
            },
            ReturnValues="UPDATED_NEW"
        )
    
        user = dynamodb.get_item(TableName="Users", Key=key)
        user_data = user["Item"]
        user = parse_user(user_data)
        del user_data["Password"]
        return flask.jsonify(ok=True, user=user)

    except Exception as e:
        print("Some error occured while updating data from dynamodb: ", e)
        return flask.jsonify(ok=False, is_logged_in=False, error=json.dumps(e))
    
@app.before_request
def before_request():
    if request.endpoint != 'login' and request.endpoint != 'index':
        verify_jwt_in_request()

if __name__ == '__main__':
    flaskrun(app)
