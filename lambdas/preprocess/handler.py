import os
import io
import json
import uuid
import datetime
import requests
from PIL import Image
import imagehash
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

def calculate_phash(image_bytes: bytes) -> str:
    with Image.open(io.BytesIO(image_bytes)) as img:
        return str(imagehash.phash(img))

def convert_to_webp(image_bytes: bytes, quality: int = 85) -> bytes:
    with Image.open(io.BytesIO(image_bytes)) as img:
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        out = io.BytesIO()
        img.save(out, "WEBP", quality=quality)
        return out.getvalue()

def lambda_handler(event, context):
    """
    Preprocess Lambda Handler
    """
    batch_id = event.get("batch_id")
    sci_name = event.get("scientific_name")
    common_name = event.get("common_name_ko", "국명 미상")
    
    if not batch_id or not sci_name:
        return {"statusCode": 400, "body": "Missing required fields"}
        
    print(f"Starting preprocess for Batch: {batch_id}")
    
    # 1. Read metadata
    commons_json_str = read_from_s3(f"raw/{batch_id}/commons.json")
    interim_json_str = read_from_s3(f"interim/{batch_id}/taxonomy_habitat.json")
    
    interim_data = json.loads(interim_json_str) if interim_json_str else {}
    
    pages = {}
    if commons_json_str:
        try:
            data = json.loads(commons_json_str)
            pages = data.get("query", {}).get("pages", {})
        except Exception:
            pass

    processed_images = []
    batch_phashes = [] # 로컬 중복 검사용
    
    safe_name = sci_name.replace(" ", "_").replace("/", "_")
    safe_kor_name = common_name.replace(" ", "_").replace("/", "_")
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    
    count = 0
    for page_id, page_info in pages.items():
        imageinfo = page_info.get("imageinfo", [])
        if not imageinfo: continue
        
        info = imageinfo[0]
        img_url = info.get("url")
        if not img_url: continue
        
        # 다운로드
        try:
            res = requests.get(img_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            if res.status_code == 200:
                img_bytes = res.content
                
                # pHash
                phash = calculate_phash(img_bytes)
                
                # 중복 방지 (배치 내)
                is_dup = False
                new_hash_obj = imagehash.hex_to_hash(phash)
                for exist_hash_str in batch_phashes:
                    exist_hash_obj = imagehash.hex_to_hash(exist_hash_str)
                    if new_hash_obj - exist_hash_obj <= 5:
                        is_dup = True
                        break
                
                if is_dup:
                    print(f"Duplicate image found (phash: {phash}). Skipping.")
                    continue
                
                batch_phashes.append(phash)
                
                # WebP 변환
                webp_bytes = convert_to_webp(img_bytes)
                count += 1
                unique_filename = f"{date_str}_{safe_name}({safe_kor_name})_{count}.webp"
                s3_key = f"processed/{batch_id}/images/{unique_filename}"
                
                # S3 저장
                save_to_s3(s3_key, webp_bytes)
                
                ext_meta = info.get("extmetadata", {})
                processed_images.append({
                    "s3_key": s3_key,
                    "source_url": img_url,
                    "phash": phash,
                    "license_type": ext_meta.get("LicenseShortName", {}).get("value", "CC BY-SA 4.0"),
                    "author": ext_meta.get("Artist", {}).get("value", "Wikimedia Contributor")
                })
        except Exception as e:
            print(f"Failed to process image {img_url}: {e}")
            
    # 최종 메타데이터 S3 저장
    final_data = {
        "scientific_name": sci_name,
        "common_name_ko": common_name,
        "taxonomy": interim_data.get("taxonomy", {}),
        "habitat": interim_data.get("habitat"),
        "images": processed_images
    }
    
    save_to_s3(f"processed/{batch_id}/final_metadata.json", json.dumps(final_data, ensure_ascii=False))
    
    event["next_step"] = "load"
    return event
