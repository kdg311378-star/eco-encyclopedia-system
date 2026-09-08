import json
import urllib.parse
import requests
from core.parser import parse_wikipedia_taxobox, parse_habitat_info

def fetch_taxonomy(scientific_name: str) -> str:
    """위키백과에서 종 분류 정보 및 서식지 정보를 추출합니다."""
    wiki_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(scientific_name)}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(wiki_url, headers=headers, timeout=10)
        if response.status_code == 200:
            html = response.text
            taxonomy_json = parse_wikipedia_taxobox(html)
            habitat_text = parse_habitat_info(html)
            
            return json.dumps({
                "taxonomy": json.loads(taxonomy_json),
                "habitat": habitat_text
            }, ensure_ascii=False)
        else:
            print(f"Wikipedia returned status code {response.status_code}")
            return json.dumps({"taxonomy": {}, "habitat": None})
            
    except Exception as e:
        print(f"Error fetching Wikipedia: {e}")
        return json.dumps({"taxonomy": {}, "habitat": None})

def fetch_images_and_metadata(scientific_name: str, max_images: int = 5):
    """Wikimedia Commons API를 통해 고화질 이미지와 메타데이터를 추출합니다."""
    # 1. Search for files via Action API
    search_api = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f'"{scientific_name}" filetype:bitmap',
        "gsrnamespace": "6", # File namespace
        "gsrlimit": str(max_images * 2), # Request more to account for maps/svgs
        "prop": "imageinfo",
        "iiprop": "url|extmetadata"
    }
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    results = []
    try:
        response = requests.get(search_api, params=params, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Failed to connect to Wikimedia Commons API (Status: {response.status_code})")
            return results
            
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        
        count = 0
        for page_id, page_info in pages.items():
            if count >= max_images:
                break
                
            imageinfo = page_info.get("imageinfo", [])
            if not imageinfo:
                continue
                
            info = imageinfo[0]
            img_url = info.get("url")
            
            if not img_url:
                continue
                
            img_url_lower = img_url.lower()
            # 필터링: 지도, 분포도 제외
            if "map" in img_url_lower or "distribution" in img_url_lower or "range" in img_url_lower:
                continue
                
            ext_meta = info.get("extmetadata", {})
            description = ext_meta.get("ImageDescription", {}).get("value", "")
            author = ext_meta.get("Artist", {}).get("value", "Wikimedia Contributor")
            license_type = ext_meta.get("LicenseShortName", {}).get("value", "CC BY-SA 4.0")
            
            meta = {
                "image_url": img_url,
                "description": description,
                "author": author,
                "license_type": license_type
            }
            
            # 이미지 다운로드
            try:
                img_response = requests.get(img_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
                if img_response.status_code == 200:
                    results.append({
                        "metadata": meta,
                        "image_bytes": img_response.content
                    })
                    count += 1
                    print(f"[{count}/{max_images}] Image downloaded successfully from API.")
            except Exception as e:
                print(f"Failed to download image bytes: {e}")
                
    except Exception as e:
        print(f"Error calling Wikimedia API: {e}")
        
    return results
