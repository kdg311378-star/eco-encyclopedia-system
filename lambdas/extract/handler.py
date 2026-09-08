import os
import json
from bs4 import BeautifulSoup
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

def parse_wikipedia_taxobox(html_content: str) -> str:
    taxonomy = {}
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        infobox = soup.find('table', class_='infobox biota')
        if infobox:
            rows = infobox.find_all('tr')
            for row in rows:
                tds = row.find_all(['td', 'th'])
                if len(tds) >= 2:
                    key_text = tds[0].get_text(separator=' ', strip=True)
                    val_text = tds[1].get_text(separator=' ', strip=True)
                    key = key_text.replace(":", "").replace("\xa0", " ").strip()
                    val = val_text.replace("\xa0", " ").strip()
                    taxonomy[key] = val
    except Exception as e:
        print(f"Error parsing Wikipedia taxobox: {e}")
    return json.dumps(taxonomy, ensure_ascii=False) if taxonomy else "{}"

def parse_habitat_info(html_content: str) -> str:
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        headings = soup.find_all(['h2', 'h3'])
        for h in headings:
            text = h.get_text(strip=True).lower()
            if 'distribution' in text or 'habitat' in text or 'range' in text:
                paras = []
                node = h.parent if 'mw-heading' in h.parent.get('class', []) else h
                node = node.find_next_sibling()
                while node and node.name not in ['h2', 'h3'] and 'mw-heading' not in node.get('class', []):
                    if node.name == 'p':
                        paras.append(node.get_text(strip=True))
                    node = node.find_next_sibling()
                return '\n'.join(paras).strip()
    except Exception as e:
        print(f"Error parsing habitat info: {e}")
    return None

def lambda_handler(event, context):
    """
    Extract Lambda Handler
    """
    batch_id = event.get("batch_id")
    if not batch_id:
        return {"statusCode": 400, "body": "batch_id missing"}
        
    print(f"Starting extract for Batch: {batch_id}")
    
    # 1. Read Wikipedia HTML from S3 raw/
    wiki_html = read_from_s3(f"raw/{batch_id}/wikipedia.html")
    
    # 2. Extract
    taxonomy_json = parse_wikipedia_taxobox(wiki_html) if wiki_html else "{}"
    habitat_text = parse_habitat_info(wiki_html) if wiki_html else None
    
    extracted_data = {
        "taxonomy": json.loads(taxonomy_json),
        "habitat": habitat_text
    }
    
    # 3. Save to S3 interim/
    save_to_s3(f"interim/{batch_id}/taxonomy_habitat.json", json.dumps(extracted_data, ensure_ascii=False))
    
    # 전달
    event["next_step"] = "preprocess"
    return event
