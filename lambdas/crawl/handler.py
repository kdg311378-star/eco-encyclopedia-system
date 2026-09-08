import os
import json
import uuid
import urllib.parse
import requests
import boto3

# S3 Helper
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

def lambda_handler(event, context):
    """
    Crawling Lambda Handler
    Event: {"scientific_name": "...", "common_name_ko": "...", "batch_id": "..."}
    """
    sci_name = event.get("scientific_name")
    common_name = event.get("common_name_ko", "국명 미상")
    batch_id = event.get("batch_id", str(uuid.uuid4()))
    
    if not sci_name:
        return {"statusCode": 400, "body": "scientific_name is required"}
        
    print(f"Starting crawl for {sci_name} (Batch: {batch_id})")
    
    # 1. Fetch Wikipedia HTML
    wiki_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(sci_name)}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    wiki_html = ""
    try:
        res = requests.get(wiki_url, headers=headers, timeout=10)
        if res.status_code == 200:
            wiki_html = res.text
            save_to_s3(f"raw/{batch_id}/wikipedia.html", wiki_html)
        else:
            print(f"Wikipedia returned {res.status_code}")
    except Exception as e:
        print(f"Wikipedia Error: {e}")
        
    # 2. Fetch Commons API metadata
    search_api = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f'"{sci_name}" filetype:bitmap',
        "gsrnamespace": "6",
        "gsrlimit": "10",
        "prop": "imageinfo",
        "iiprop": "url|extmetadata"
    }
    commons_json = "{}"
    try:
        res2 = requests.get(search_api, params=params, headers=headers, timeout=10)
        if res2.status_code == 200:
            commons_json = res2.text
            save_to_s3(f"raw/{batch_id}/commons.json", commons_json)
    except Exception as e:
        print(f"Commons Error: {e}")
        
    return {
        "statusCode": 200,
        "batch_id": batch_id,
        "scientific_name": sci_name,
        "common_name_ko": common_name,
        "next_step": "extract"
    }
