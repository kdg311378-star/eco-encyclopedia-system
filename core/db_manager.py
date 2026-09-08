import mysql.connector
from config.database import get_connection_config

class DBManager:
    def __init__(self):
        self.config = get_connection_config()

    def get_connection(self):
        return mysql.connector.connect(**self.config)

    def check_species_exists(self, search_term: str):
        """학명 또는 국명으로 종 존재 여부를 확인합니다."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM species WHERE scientific_name = %s OR common_name_ko = %s LIMIT 1", (search_term, search_term))
            return cursor.fetchone()
        except Exception as e:
            print(f"Error checking species exists: {e}")
            return None
        finally:
            cursor.close()
            conn.close()

    def save_species(self, scientific_name: str, common_name_ko: str, category_type: str, taxonomy_data: dict, habitat_info: str = None) -> int:
        """
        종 정보를 DB에 저장하거나 기존 종이 존재할 경우 ID를 반환합니다.
        """
        import json
        
        # 기본 6계층 추출
        t_phylum = taxonomy_data.pop("Phylum", None)
        t_class = taxonomy_data.pop("Class", None)
        t_order = taxonomy_data.pop("Order", None)
        t_family = taxonomy_data.pop("Family", None)
        t_genus = taxonomy_data.pop("Genus", None)
        t_species = taxonomy_data.pop("Species", None)
        
        # 나머지는 JSON으로 변환
        extra_json = json.dumps(taxonomy_data, ensure_ascii=False) if taxonomy_data else None

        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        species_id = None
        try:
            # 1. 기존 종 존재 여부 확인
            cursor.execute("SELECT species_id FROM species WHERE scientific_name = %s", (scientific_name,))
            result = cursor.fetchone()
            
            if result:
                species_id = result['species_id']
                # Taxonomy 갱신
                update_sql = """
                    UPDATE species 
                    SET common_name_ko = %s, category_type = %s,
                        taxon_phylum = %s, taxon_class = %s, taxon_order = %s,
                        taxon_family = %s, taxon_genus = %s, taxon_species = %s,
                        extra_taxonomy = %s, habitat_info = %s
                    WHERE species_id = %s
                """
                cursor.execute(update_sql, (
                    common_name_ko, category_type, 
                    t_phylum, t_class, t_order, t_family, t_genus, t_species, extra_json, habitat_info,
                    species_id
                ))
            else:
                # 2. 신규 종 INSERT
                insert_sql = """
                    INSERT INTO species (
                        scientific_name, common_name_ko, category_type,
                        taxon_phylum, taxon_class, taxon_order, 
                        taxon_family, taxon_genus, taxon_species, extra_taxonomy, habitat_info
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_sql, (
                    scientific_name, common_name_ko, category_type,
                    t_phylum, t_class, t_order, t_family, t_genus, t_species, extra_json, habitat_info
                ))
                species_id = cursor.lastrowid
                
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error saving species: {e}")
            raise e
        finally:
            cursor.close()
            conn.close()
            
        return species_id

    def get_species_phashes(self, species_id: int) -> list[str]:
        """특정 종의 기존 저장된 pHash 목록을 조회합니다."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        phashes = []
        try:
            cursor.execute("SELECT phash_value FROM species_images WHERE species_id = %s", (species_id,))
            rows = cursor.fetchall()
            phashes = [row['phash_value'] for row in rows]
        except Exception as e:
            print(f"Error fetching phashes: {e}")
        finally:
            cursor.close()
            conn.close()
        return phashes

    def get_all_species(self) -> list[dict]:
        """모든 종 정보를 최근 추가된 순으로 조회합니다."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM species ORDER BY species_id DESC")
            return cursor.fetchall()
        except Exception as e:
            print(f"Error fetching all species: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    def get_images_for_species(self, species_id: int) -> list[dict]:
        """특정 종의 모든 이미지 레코드를 조회합니다."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM species_images WHERE species_id = %s", (species_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error fetching images for species {species_id}: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    def get_all_species_dataframe_data(self) -> list[dict]:
        """표(Dataframe) 및 CSV 출력용으로 가공된 데이터를 조회합니다."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            sql = """
                SELECT 
                    s.species_id as 'ID',
                    s.scientific_name as '학명(Scientific Name)',
                    s.common_name_ko as '국명(Common Name)',
                    s.category_type as '구분(Category)',
                    s.taxon_phylum as '문(Phylum)',
                    s.taxon_class as '강(Class)',
                    s.taxon_order as '목(Order)',
                    s.taxon_family as '과(Family)',
                    s.taxon_genus as '속(Genus)',
                    s.taxon_species as '종(Species)',
                    s.habitat_info as '서식지(Habitat)',
                    COUNT(i.image_id) as '수집된 이미지 수(Image Count)'
                FROM species s
                LEFT JOIN species_images i ON s.species_id = i.species_id
                GROUP BY s.species_id
                ORDER BY s.species_id DESC
            """
            cursor.execute(sql)
            return cursor.fetchall()
        except Exception as e:
            print(f"Error fetching dataframe data: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    def get_all_species_images_dataframe_data(self) -> list[dict]:
        """이미지(species_images) 상세 정보를 표(Dataframe) 및 CSV 출력용으로 가공하여 조회합니다."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            sql = """
                SELECT 
                    i.image_id as '이미지 ID',
                    s.scientific_name as '학명(Scientific Name)',
                    i.local_image_url as '로컬 경로',
                    i.source_origin_url as '원본 출처 URL',
                    i.phash_value as '이미지 pHash',
                    i.license_type as '라이선스',
                    i.author as '저작자',
                    IF(i.is_representative=1, '예', '아니오') as '대표 이미지 여부',
                    i.created_at as '수집 일시'
                FROM species_images i
                JOIN species s ON i.species_id = s.species_id
                ORDER BY i.image_id DESC
            """
            cursor.execute(sql)
            return cursor.fetchall()
        except Exception as e:
            print(f"Error fetching images dataframe data: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    def save_image(self, species_id: int, local_image_url: str, source_origin_url: str, 
                   phash_value: str, license_type: str, author: str, is_representative: bool):
        """
        검증이 완료된 이미지 메타데이터를 DB에 적재합니다.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            insert_sql = """
                INSERT INTO species_images 
                (species_id, local_image_url, source_origin_url, phash_value, license_type, author, is_representative)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_sql, (
                species_id, local_image_url, source_origin_url, phash_value, 
                license_type, author, 1 if is_representative else 0
            ))
            conn.commit()
        except mysql.connector.IntegrityError:
            # Unique Key (species_id, phash_value) 중복 방어
            conn.rollback()
            print(f"Image already exists in DB with phash {phash_value}")
        except Exception as e:
            conn.rollback()
            print(f"Error saving image: {e}")
            raise e
        finally:
            cursor.close()
            conn.close()
