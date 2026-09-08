from src.eco_encyclopedia.preprocess import preprocess_images

def lambda_handler(event, context):
    batch_id = event.get("batch_id")
    sci_name = event.get("scientific_name")
    common_name = event.get("common_name_ko", "국명 미상")
    
    if not batch_id or not sci_name:
        return {"statusCode": 400, "body": "Missing required fields"}
        
    print(f"Starting preprocess for Batch: {batch_id}")
    preprocess_images(sci_name, common_name, batch_id)
    
    event["next_step"] = "load"
    return event
