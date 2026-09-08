import os
import json
import mysql.connector
import boto3

# S3 Helper
IS_LOCAL = os.environ.get("AWS_SAM_LOCAL") == "true" or os.environ.get("LOCAL_MOCK") == "true"
BUCKET_NAME = os.environ.get("DATA_BUCKET_NAME", "local-bucket")
LOCAL_MOCK_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".local_s3_mock")

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

def get_db_connection():
    if IS_LOCAL:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))
        return mysql.connector.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=int(os.environ.get("DB_PORT", 3306)),
            user=os.environ.get("DB_USER", "eco_user"),
            password=os.environ.get("DB_PASSWORD", "1111"),
            database=os.environ.get("DB_NAME", "bio_encyclopedia")
        )
    else:
        # Get from AWS Secrets Manager
        secret_arn = os.environ.get("DB_SECRET_ARN")
        client = boto3.client('secretsmanager')
        secret_val = client.get_secret_value(SecretId=secret_arn)
        creds = json.loads(secret_val['SecretString'])
        return mysql.connector.connect(
            host=os.environ.get("DB_HOST"),
            port=3306,
            user=creds.get("username"),
            password=creds.get("password"),
            database="bio_encyclopedia"
        )

def lambda_handler(event, context):
    """
    Load Lambda Handler
    """
    batch_id = event.get("batch_id")
    if not batch_id:
        return {"statusCode": 400, "body": "Missing batch_id"}
        
    print(f"Starting load for Batch: {batch_id}")
    
    final_json_str = read_from_s3(f"processed/{batch_id}/final_metadata.json")
    if not final_json_str:
        return {"statusCode": 400, "body": "No final_metadata.json found"}
        
    data = json.loads(final_json_str)
    sci_name = data.get("scientific_name")
    common_name = data.get("common_name_ko")
    taxonomy = data.get("taxonomy", {})
    habitat = data.get("habitat")
    images = data.get("images", [])
    
    t_phylum = taxonomy.pop("Phylum", None)
    t_class = taxonomy.pop("Class", None)
    t_order = taxonomy.pop("Order", None)
    t_family = taxonomy.pop("Family", None)
    t_genus = taxonomy.pop("Genus", None)
    t_species = taxonomy.pop("Species", None)
    extra_json = json.dumps(taxonomy, ensure_ascii=False) if taxonomy else None
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Species
        cursor.execute("SELECT species_id FROM species WHERE scientific_name = %s", (sci_name,))
        row = cursor.fetchone()
        
        if row:
            species_id = row['species_id']
            sql = """
                UPDATE species 
                SET common_name_ko = %s, taxon_phylum = %s, taxon_class = %s, taxon_order = %s,
                    taxon_family = %s, taxon_genus = %s, taxon_species = %s, extra_taxonomy = %s, habitat_info = %s
                WHERE species_id = %s
            """
            cursor.execute(sql, (common_name, t_phylum, t_class, t_order, t_family, t_genus, t_species, extra_json, habitat, species_id))
        else:
            sql = """
                INSERT INTO species (scientific_name, common_name_ko, taxon_phylum, taxon_class, taxon_order, 
                    taxon_family, taxon_genus, taxon_species, extra_taxonomy, habitat_info)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (sci_name, common_name, t_phylum, t_class, t_order, t_family, t_genus, t_species, extra_json, habitat))
            species_id = cursor.lastrowid
            
        # Images
        for idx, img in enumerate(images):
            try:
                sql = """
                    INSERT INTO species_images 
                    (species_id, local_image_url, source_origin_url, phash_value, license_type, author, is_representative)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                is_rep = 1 if idx == 0 else 0
                cursor.execute(sql, (species_id, img["s3_key"], img["source_url"], img["phash"], img["license_type"], img["author"], is_rep))
            except mysql.connector.IntegrityError:
                pass # pHash duplicate in DB
                
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"DB Error: {e}")
        return {"statusCode": 500, "body": str(e)}
    finally:
        cursor.close()
        conn.close()
        
    return {
        "statusCode": 200,
        "body": "Successfully loaded to RDS"
    }
