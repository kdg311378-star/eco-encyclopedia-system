import json

import mysql.connector

from src.eco_encyclopedia.database import get_db_connection
from src.eco_encyclopedia.s3_storage import read_from_s3


def load_data_to_db(batch_id: str):
    final_json_str = read_from_s3(f"processed/{batch_id}/final_metadata.json")
    if not final_json_str:
        raise Exception("No final_metadata.json found")
        
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
                pass
                
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"DB Error: {e}")
        raise e
    finally:
        cursor.close()
        conn.close()
