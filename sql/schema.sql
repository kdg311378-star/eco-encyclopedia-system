CREATE DATABASE IF NOT EXISTS `bio_encyclopedia`
DEFAULT CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE `bio_encyclopedia`;

DROP TABLE IF EXISTS `species_images`;
DROP TABLE IF EXISTS `species`;

-- 1. 생물 종 기본 정보 테이블
CREATE TABLE IF NOT EXISTS `species` (
    `species_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `scientific_name` VARCHAR(255) NOT NULL COMMENT '학명 (고유 식별자, 예: Myocastor coypus)',
    `common_name_ko` VARCHAR(100) NOT NULL COMMENT '국명 (예: 뉴트리아)',
    `category_type` ENUM('INVASIVE', 'NATIVE', 'ENDANGERED') NOT NULL DEFAULT 'INVASIVE' COMMENT '분류',
    `risk_level` VARCHAR(50) NULL COMMENT '지정 등급 (예: 생태계교란생물)',
    `taxon_phylum` VARCHAR(100) NULL COMMENT '문 (Phylum)',
    `taxon_class` VARCHAR(100) NULL COMMENT '강 (Class)',
    `taxon_order` VARCHAR(100) NULL COMMENT '목 (Order)',
    `taxon_family` VARCHAR(100) NULL COMMENT '과 (Family)',
    `taxon_genus` VARCHAR(100) NULL COMMENT '속 (Genus)',
    `taxon_species` VARCHAR(100) NULL COMMENT '종 (Species)',
    `extra_taxonomy` JSON NULL COMMENT '기타 세부 분류',
    `habitat_info` TEXT NULL COMMENT '서식지 및 분포 정보',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`species_id`),
    UNIQUE KEY `uk_scientific_name` (`scientific_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. 수집 이미지 및 메타데이터 테이블 (1:N 매핑)
CREATE TABLE IF NOT EXISTS `species_images` (
    `image_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `species_id` BIGINT UNSIGNED NOT NULL COMMENT '소속 종 ID',
    `local_image_url` VARCHAR(500) NOT NULL COMMENT '로컬 정적 서빙 경로 (/static/images/species/...)',
    `source_origin_url` VARCHAR(1000) NULL COMMENT '위키미디어 원본 CDN 주소',
    `phash_value` VARCHAR(64) NOT NULL COMMENT '이미지 64비트 pHash 문자열',
    `license_type` VARCHAR(100) NOT NULL DEFAULT 'CC BY-SA 4.0' COMMENT '저작권 라이선스',
    `author` VARCHAR(255) NOT NULL DEFAULT 'Wikimedia Contributor' COMMENT '원작자/기여자',
    `is_representative` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '도감 대표 썸네일 여부 (1: 대표, 0: 일반)',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`image_id`),
    UNIQUE KEY `uk_species_phash` (`species_id`, `phash_value`),
    KEY `idx_species_id` (`species_id`),
    CONSTRAINT `fk_species_images_species_id` 
        FOREIGN KEY (`species_id`) REFERENCES `species` (`species_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
