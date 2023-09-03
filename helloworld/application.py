#!flask/bin/python
import json
from flask import Flask, render_template, request, redirect, Response
from helloworld.flaskrun import flaskrun
import os
from dotenv import load_dotenv
from os.path import  join, dirname

application = Flask(__name__)

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

@application.route('/', methods=['GET'])
def get():
    return redirect("http://smart-hotel-static.s3-website-us-east-1.amazonaws.com")

@application.route('/', methods=['POST'])
def post():
    return Response(json.dumps({'Output': 'Hello World'}), mimetype='application/json', status=200)

if __name__ == '__main__':
    flaskrun(application)
