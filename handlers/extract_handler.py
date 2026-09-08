from src.eco_encyclopedia.extract import extract_data

def lambda_handler(event, context):
    batch_id = event.get("batch_id")
    if not batch_id:
        return {"statusCode": 400, "body": "batch_id missing"}
        
    print(f"Starting extract for Batch: {batch_id}")
    extract_data(batch_id)
    
    event["next_step"] = "preprocess"
    return event
