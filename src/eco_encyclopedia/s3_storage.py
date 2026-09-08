import os
import boto3

IS_LOCAL = os.environ.get("AWS_SAM_LOCAL") == "true" or os.environ.get("LOCAL_MOCK") == "true"
BUCKET_NAME = os.environ.get("DATA_BUCKET_NAME", "local-bucket")
LOCAL_MOCK_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".local_s3_mock")

def save_to_s3(key: str, data: str | bytes):
    if IS_LOCAL:
        filepath = os.path.join(LOCAL_MOCK_DIR, key)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        mode = "wb" if isinstance(data, bytes) else "w"
        encoding = None if isinstance(data, bytes) else "utf-8"
        with open(filepath, mode, encoding=encoding) as f:
            f.write(data)
        print(f"[LOCAL S3 MOCK] Saved to {filepath}")
    else:
        s3 = boto3.client('s3')
        if isinstance(data, str):
            data = data.encode('utf-8')
        s3.put_object(Bucket=BUCKET_NAME, Key=key, Body=data)
        print(f"[AWS S3] Saved to s3://{BUCKET_NAME}/{key}")

def read_from_s3(key: str) -> str:
    if IS_LOCAL:
        filepath = os.path.join(LOCAL_MOCK_DIR, key)
        if not os.path.exists(filepath):
            return ""
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    else:
        s3 = boto3.client('s3')
        try:
            obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
            return obj['Body'].read().decode('utf-8')
        except Exception as e:
            print(f"[AWS S3] Error reading {key}: {e}")
            return ""
