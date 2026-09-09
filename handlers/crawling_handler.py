import uuid

from src.eco_encyclopedia.crawling import crawl_species


def lambda_handler(event, context):
    sci_name = event.get("scientific_name")
    common_name = event.get("common_name_ko", "국명 미상")
    batch_id = event.get("batch_id", str(uuid.uuid4()))
    
    if not sci_name:
        return {"statusCode": 400, "body": "scientific_name is required"}
        
    print(f"Starting crawl for {sci_name} (Batch: {batch_id})")
    crawl_species(sci_name, batch_id)
        
    return {
        "statusCode": 200,
        "batch_id": batch_id,
        "scientific_name": sci_name,
        "common_name_ko": common_name,
        "next_step": "extract"
    }
