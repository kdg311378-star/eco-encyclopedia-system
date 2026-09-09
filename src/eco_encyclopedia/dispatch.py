import json
import urllib.parse
import urllib.request

from src.eco_encyclopedia.database import get_db_connection


def get_current_offset() -> int:
    """DB에서 마지막으로 검색한 GBIF 오프셋을 가져옵니다."""
    conn = get_db_connection()
    if not conn:
        return 0
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT last_gbif_offset FROM sync_state WHERE id = 1")
        result = cursor.fetchone()
        
        if result:
            return result['last_gbif_offset']
        else:
            # 테이블에 데이터가 없으면 초기값 세팅
            cursor.execute("INSERT INTO sync_state (id, last_gbif_offset) VALUES (1, 0)")
            conn.commit()
            return 0
    except Exception as e:
        print(f"Error reading offset: {e}")
        return 0
    finally:
        cursor.close()
        conn.close()

def update_offset(new_offset: int):
    """검색 완료 후 새로운 오프셋으로 갱신합니다."""
    conn = get_db_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE sync_state SET last_gbif_offset = %s WHERE id = 1", (new_offset,))
        conn.commit()
    except Exception as e:
        print(f"Error updating offset: {e}")
    finally:
        cursor.close()
        conn.close()

def is_species_collected(scientific_name: str) -> bool:
    """해당 학명이 우리 DB에 이미 수집되었는지 확인합니다."""
    conn = get_db_connection()
    if not conn:
        # 안전장치: DB 연결 실패시 이미 수집된 것으로 간주하여 크롤링 폭주 방지
        return True
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM species WHERE scientific_name = %s", (scientific_name,))
        result = cursor.fetchone()
        return result is not None
    except Exception as e:
        print(f"Error checking if species collected: {e}")
        return True
    finally:
        cursor.close()
        conn.close()

def fetch_gbif_species(offset: int, limit: int = 10) -> list:
    """GBIF API에서 새로운 종 목록을 페이징하여 가져옵니다."""
    url = f"https://api.gbif.org/v1/species/search?rank=SPECIES&status=ACCEPTED&limit={limit}&offset={offset}"
    try:
        req = urllib.request.urlopen(url)
        data = json.loads(req.read().decode('utf-8'))
        return data.get('results', [])
    except Exception as e:
        print(f"Error fetching from GBIF API: {e}")
        return []

def get_target_species_for_today(limit: int = 5) -> tuple[list[dict], int]:
    """
    오늘 수집할 타겟 종의 목록과 다음 검색을 위한 오프셋을 반환합니다.
    """
    offset = get_current_offset()
    target_species = []
    
    # DB에 없는 새로운 생물을 limit 개수만큼 찾을 때까지 계속 API 호출 (최대 5회 페이징)
    attempts = 0
    max_attempts = 5
    
    while len(target_species) < limit and attempts < max_attempts:
        results = fetch_gbif_species(offset, limit=20)
        
        if not results:
            # 더 이상 결과가 없으면 오프셋을 0으로 리셋하여 처음부터 새로 수집 시작 (Infinite Loop)
            print("Reached end of GBIF data. Resetting offset to 0.")
            offset = 0
            break
            
        for result in results:
            sci_name = result.get('canonicalName')
            if sci_name:
                if not is_species_collected(sci_name):
                    # 아직 없는 신규 종 발견!
                    target_species.append({
                        "scientific_name": sci_name,
                        "common_name_ko": result.get('vernacularName', '국명 미상')
                    })
                    
            if len(target_species) >= limit:
                break
                
        # 한 페이지 검사 끝
        offset += 20
        attempts += 1
        
    update_offset(offset)
    return target_species, offset
