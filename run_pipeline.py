import os
import sys
from core.crawler import fetch_taxonomy, fetch_images_and_metadata
from core.processor import calculate_phash, is_duplicate, convert_and_save_webp
from core.db_manager import DBManager

def run(scientific_name: str, common_name_ko: str, category_type: str = "INVASIVE"):
    print(f"--- Starting pipeline for {scientific_name} ({common_name_ko}) ---")
    
    db = DBManager()
    
    # 0. 사전 중복 검증
    print("0. Checking for existing species in DB...")
    existing = db.check_species_exists(scientific_name) or (common_name_ko != "국명 미상" and db.check_species_exists(common_name_ko))
    if existing:
        print(f"[{existing['scientific_name']}] Species already exists in DB (ID: {existing['species_id']}).")
        print("Skipping new crawling to prevent duplicates and save resources.")
        return

    # 1. Wikipedia에서 Taxonomy 수집
    print("1. Fetching taxonomy from Wikipedia...")
    taxonomy_json = fetch_taxonomy(scientific_name)
    print(f"Taxonomy: {taxonomy_json}")
    
    # 2. DB에 종 정보 적재
    print("2. Saving species to DB...")
    import json
    try:
        data = json.loads(taxonomy_json) if taxonomy_json else {}
        taxonomy_val = data.get("taxonomy", {})
        if isinstance(taxonomy_val, str):
            taxonomy_dict = json.loads(taxonomy_val) if taxonomy_val else {}
        else:
            taxonomy_dict = taxonomy_val
        habitat_info = data.get("habitat")
    except Exception:
        taxonomy_dict = {}
        habitat_info = None
        
    species_id = db.save_species(scientific_name, common_name_ko, category_type, taxonomy_dict, habitat_info)
    print(f"Species ID: {species_id}")
    
    # 기존 pHash 조회 (중복 검증용)
    db_phashes = db.get_species_phashes(species_id)
    print(f"Loaded {len(db_phashes)} existing phashes from DB.")
    
    # 3. 위키미디어 커먼즈에서 이미지 수집
    print("3. Fetching images from Wikimedia Commons...")
    images_data = fetch_images_and_metadata(scientific_name, max_images=5)
    
    # 4. 이미지 정제 및 DB 적재
    print(f"4. Processing {len(images_data)} downloaded images...")
    
    # 로컬 저장 디렉토리 생성
    safe_name = scientific_name.replace(" ", "_").replace("/", "_")
    save_dir = os.path.join("static", "images", "species", safe_name)
    os.makedirs(save_dir, exist_ok=True)
    
    saved_count = 0
    for i, data in enumerate(images_data):
        img_bytes = data["image_bytes"]
        meta = data["metadata"]
        
        # pHash 계산
        try:
            new_phash = calculate_phash(img_bytes)
        except Exception as e:
            print(f"Failed to calculate phash: {e}")
            continue
            
        # 중복 검사
        if is_duplicate(new_phash, db_phashes, threshold=5):
            print(f"Image {i+1} is duplicate (phash: {new_phash}). Skipping.")
            continue
            
        # WebP 변환 및 로컬 저장
        import datetime
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        safe_kor_name = common_name_ko.replace(" ", "_").replace("/", "_")
        unique_filename = f"{date_str}_{safe_name}({safe_kor_name})_{i+1}.webp"
        local_path = os.path.join(save_dir, unique_filename)
        
        if convert_and_save_webp(img_bytes, local_path):
            local_url = f"/static/images/species/{safe_name}/{unique_filename}"
            is_representative = (saved_count == 0 and len(db_phashes) == 0)
            
            # DB 저장
            try:
                db.save_image(
                    species_id=species_id,
                    local_image_url=local_url,
                    source_origin_url=meta["image_url"],
                    phash_value=new_phash,
                    license_type=meta.get("license_type", "CC BY-SA 4.0"),
                    author=meta.get("author", "Wikimedia Contributor"),
                    is_representative=is_representative
                )
                db_phashes.append(new_phash) # 방금 추가된 해시도 목록에 반영
                saved_count += 1
                print(f"Successfully saved image {i+1} to DB and {local_path}")
            except Exception as e:
                print(f"Failed to save image metadata to DB: {e}")
                
    print(f"--- Pipeline complete! Saved {saved_count} new images. ---")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_pipeline.py <scientific_name_or_korean_name> [common_name_ko] [category_type]")
        sys.exit(1)
        
    import re
    arg1 = sys.argv[1]
    if len(sys.argv) > 2:
        sci_name = arg1
        common_name = sys.argv[2]
        cat_type = sys.argv[3] if len(sys.argv) > 3 else "INVASIVE"
    else:
        if bool(re.search(r'[가-힣]', arg1)):
            sci_name = arg1
            common_name = arg1
        else:
            sci_name = arg1
            common_name = "국명 미상"
        cat_type = "INVASIVE"
    
    run(sci_name, common_name, cat_type)
