from src.eco_encyclopedia.load import load_data_to_db


def lambda_handler(event, context):
    batch_id = event.get("batch_id")
    if not batch_id:
        return {"statusCode": 400, "body": "Missing batch_id"}
        
    print(f"Starting load for Batch: {batch_id}")
    try:
        load_data_to_db(batch_id)
        return {"statusCode": 200, "body": "Successfully loaded to RDS"}
    except Exception as e:
        return {"statusCode": 500, "body": str(e)}
