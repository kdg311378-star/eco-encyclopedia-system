import urllib.parse

import requests

from src.eco_encyclopedia.s3_storage import save_to_s3


def crawl_species(sci_name: str, batch_id: str):
    # 1. Fetch Wikipedia HTML
    wiki_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(sci_name)}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        res = requests.get(wiki_url, headers=headers, timeout=10)
        if res.status_code == 200:
            save_to_s3(f"raw/{batch_id}/wikipedia.html", res.text)
        else:
            print(f"Wikipedia returned {res.status_code}")
    except Exception as e:
        print(f"Wikipedia Error: {e}")
        
    # 2. Fetch Commons API metadata
    search_api = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f'"{sci_name}" filetype:bitmap',
        "gsrnamespace": "6",
        "gsrlimit": "10",
        "prop": "imageinfo",
        "iiprop": "url|extmetadata"
    }
    try:
        res2 = requests.get(search_api, params=params, headers=headers, timeout=10)
        if res2.status_code == 200:
            save_to_s3(f"raw/{batch_id}/commons.json", res2.text)
    except Exception as e:
        print(f"Commons Error: {e}")
