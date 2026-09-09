import logging

from src.eco_encyclopedia.dispatch import get_target_species_for_today

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    EventBridge 스케줄러에 의해 매일 호출되는 지휘관 람다입니다.
    GBIF에서 신규 생물을 찾아 배열로 반환하며, 
    Step Functions의 Map state가 이 배열을 받아 병렬로 크롤링을 수행하게 됩니다.
    """
    try:
        limit = event.get('limit', 5) # 기본 5마리
        logger.info(f"Starting dispatcher to find {limit} new species.")
        
        target_species, new_offset = get_target_species_for_today(limit=limit)
        
        logger.info(f"Found {len(target_species)} species. Next GBIF offset: {new_offset}")
        
        return {
            "statusCode": 200,
            "target_species": target_species,
            "next_offset": new_offset
        }
    except Exception as e:
        logger.error(f"Dispatcher failed: {e}")
        return {
            "statusCode": 500,
            "error": str(e)
        }
