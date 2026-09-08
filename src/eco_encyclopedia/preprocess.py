import io
import json
import datetime
import requests
from PIL import Image
import imagehash
from src.eco_encyclopedia.s3_storage import read_from_s3, save_to_s3

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

def preprocess_images(sci_name: str, common_name: str, batch_id: str):
    commons_json_str = read_from_s3(f"raw/{batch_id}/commons.json")
    interim_json_str = read_from_s3(f"interim/{batch_id}/taxonomy_habitat.json")
    
    interim_data = json.loads(interim_json_str) if interim_json_str else {}
    pages = {}
    if commons_json_str:
        try:
            pages = json.loads(commons_json_str).get("query", {}).get("pages", {})
        except Exception:
            pass

    processed_images = []
    batch_phashes = []
    
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
        
        try:
            res = requests.get(img_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            if res.status_code == 200:
                img_bytes = res.content
                phash = calculate_phash(img_bytes)
                
                is_dup = False
                new_hash_obj = imagehash.hex_to_hash(phash)
                for exist_hash_str in batch_phashes:
                    exist_hash_obj = imagehash.hex_to_hash(exist_hash_str)
                    if new_hash_obj - exist_hash_obj <= 5:
                        is_dup = True
                        break
                
                if is_dup:
                    continue
                
                batch_phashes.append(phash)
                webp_bytes = convert_to_webp(img_bytes)
                count += 1
                unique_filename = f"{date_str}_{safe_name}({safe_kor_name})_{count}.webp"
                s3_key = f"processed/{batch_id}/images/{unique_filename}"
                
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
            print(f"Failed to process image: {e}")
            
    final_data = {
        "scientific_name": sci_name,
        "common_name_ko": common_name,
        "taxonomy": interim_data.get("taxonomy", {}),
        "habitat": interim_data.get("habitat"),
        "images": processed_images
    }
    save_to_s3(f"processed/{batch_id}/final_metadata.json", json.dumps(final_data, ensure_ascii=False))
