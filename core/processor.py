import io
from PIL import Image
import imagehash

def calculate_phash(image_bytes: bytes) -> str:
    """
    이미지 바이너리로부터 64비트 pHash 값을 계산하여 반환합니다.
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        # pHash 계산 (hash size 8 -> 64bit)
        hash_val = imagehash.phash(img)
        return str(hash_val)

def is_duplicate(new_phash_str: str, db_phash_list: list[str], threshold: int = 5) -> bool:
    """
    새로운 이미지의 pHash 값이 기존 DB 해시값들과 해밍 거리가 threshold 이하인지 검사하여
    중복 여부를 판별합니다.
    """
    new_hash = imagehash.hex_to_hash(new_phash_str)
    
    for db_phash_str in db_phash_list:
        try:
            db_hash = imagehash.hex_to_hash(db_phash_str)
            # 해밍 거리 계산
            distance = new_hash - db_hash
            if distance <= threshold:
                return True
        except Exception:
            continue
            
    return False

def convert_and_save_webp(image_bytes: bytes, output_path: str, quality: int = 85) -> bool:
    """
    이미지 바이너리를 WebP 포맷으로 변환하여 지정된 경로에 저장합니다.
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            # RGBA 모드인 경우 (투명도 포함) 배경이 투명하게 유지되도록 처리하거나 RGB로 변환 필요
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                
            img.save(output_path, "WEBP", quality=quality)
        return True
    except Exception as e:
        print(f"Error converting to WebP: {e}")
        return False
