import os
import json
import mysql.connector
import boto3

def get_db_connection():
    IS_LOCAL = os.environ.get("AWS_SAM_LOCAL") == "true" or os.environ.get("LOCAL_MOCK") == "true"
    if IS_LOCAL:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))
        return mysql.connector.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=int(os.environ.get("DB_PORT", 3306)),
            user=os.environ.get("DB_USER", "eco_user"),
            password=os.environ.get("DB_PASSWORD", "1111"),
            database=os.environ.get("DB_NAME", "bio_encyclopedia")
        )
    else:
        secret_arn = os.environ.get("DB_SECRET_ARN")
        client = boto3.client('secretsmanager')
        secret_val = client.get_secret_value(SecretId=secret_arn)
        creds = json.loads(secret_val['SecretString'])
        return mysql.connector.connect(
            host=os.environ.get("DB_HOST"),
            port=3306,
            user=creds.get("username"),
            password=creds.get("password"),
            database="bio_encyclopedia"
        )
