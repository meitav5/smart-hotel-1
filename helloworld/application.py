#!flask/bin/python
import json
from flask import Flask, render_template, request, redirect, Response
from helloworld.flaskrun import flaskrun
import os

application = Flask(__name__)

@application.route('/', methods=['GET'])
def get():
    url = os.environ.get('AWS_STATIC_WEBSITE_S3_URL')
    return redirect(url)

@application.route('/', methods=['POST'])
def post():
    return Response(json.dumps({'Output': 'Hello World'}), mimetype='application/json', status=200)

if __name__ == '__main__':
    flaskrun(application)
