import json
from bs4 import BeautifulSoup
from src.eco_encyclopedia.s3_storage import read_from_s3, save_to_s3

def parse_wikipedia_taxobox(html_content: str) -> str:
    taxonomy = {}
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        infobox = soup.find('table', class_='infobox biota')
        if infobox:
            rows = infobox.find_all('tr')
            for row in rows:
                tds = row.find_all(['td', 'th'])
                if len(tds) >= 2:
                    key_text = tds[0].get_text(separator=' ', strip=True)
                    val_text = tds[1].get_text(separator=' ', strip=True)
                    key = key_text.replace(":", "").replace("\xa0", " ").strip()
                    val = val_text.replace("\xa0", " ").strip()
                    taxonomy[key] = val
    except Exception as e:
        print(f"Error parsing taxobox: {e}")
    return json.dumps(taxonomy, ensure_ascii=False) if taxonomy else "{}"

def parse_habitat_info(html_content: str) -> str:
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        headings = soup.find_all(['h2', 'h3'])
        for h in headings:
            text = h.get_text(strip=True).lower()
            if 'distribution' in text or 'habitat' in text or 'range' in text:
                paras = []
                node = h.parent if 'mw-heading' in h.parent.get('class', []) else h
                node = node.find_next_sibling()
                while node and node.name not in ['h2', 'h3'] and 'mw-heading' not in node.get('class', []):
                    if node.name == 'p':
                        paras.append(node.get_text(strip=True))
                    node = node.find_next_sibling()
                return '\n'.join(paras).strip()
    except Exception as e:
        print(f"Error parsing habitat: {e}")
    return None

def extract_data(batch_id: str):
    wiki_html = read_from_s3(f"raw/{batch_id}/wikipedia.html")
    taxonomy_json = parse_wikipedia_taxobox(wiki_html) if wiki_html else "{}"
    habitat_text = parse_habitat_info(wiki_html) if wiki_html else None
    
    extracted_data = {
        "taxonomy": json.loads(taxonomy_json),
        "habitat": habitat_text
    }
    save_to_s3(f"interim/{batch_id}/taxonomy_habitat.json", json.dumps(extracted_data, ensure_ascii=False))
