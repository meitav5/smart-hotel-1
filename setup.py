from setuptools import setup, find_packages

setup(
    name='helloworld',
    packages=find_packages(),
    include_package_data=True,
    install_requires=['awscli', 'pycryptodome', 'blinker', 'boto3', 'botocore', 'click', 'Flask', 'Flask-Cors', 'Flask-JWT-Extended', 'gunicorn', 'importlib-metadata', 'itsdangerous', 'Jinja2', 'jmespath', 'MarkupSafe', 'pyasn1', 'PyJWT', 'python-dateutil', 'python-dotenv', 'rsa', 's3transfer', 'six', 'urllib3', 'Werkzeug', 'zipp'],
    setup_requires=[
        'awscli', 'pycryptodome', 'blinker', 'boto3', 'botocore', 'click', 'Flask', 'Flask-Cors', 'Flask-JWT-Extended', 'gunicorn', 'importlib-metadata', 'itsdangerous', 'Jinja2', 'jmespath', 'MarkupSafe', 'pyasn1', 'PyJWT', 'python-dateutil', 'python-dotenv', 'rsa', 's3transfer', 'six', 'urllib3', 'Werkzeug', 'zipp', 'pytest-runner',
    ],
    tests_require=[
        'pytest',
    ],
)
