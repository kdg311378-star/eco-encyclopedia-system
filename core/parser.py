import json
from bs4 import BeautifulSoup

def parse_wikipedia_taxobox(html_content: str) -> str:
    """
    위키백과 HTML에서 Kingdom, Phylum, Class 등의 계통 분류 정보를 추출하여
    JSON 문자열로 반환합니다.
    """
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
        print(f"Error parsing Wikipedia taxobox: {e}")
        
    return json.dumps(taxonomy, ensure_ascii=False) if taxonomy else "{}"

def parse_habitat_info(html_content: str) -> str:
    """
    위키백과 HTML에서 Distribution / Habitat 관련 단락을 추출합니다.
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        headings = soup.find_all(['h2', 'h3'])
        for h in headings:
            text = h.get_text(strip=True).lower()
            if 'distribution' in text or 'habitat' in text or 'range' in text:
                paras = []
                # mw-heading div 안에 있는지 확인
                node = h.parent if 'mw-heading' in h.parent.get('class', []) else h
                node = node.find_next_sibling()
                
                while node and node.name not in ['h2', 'h3'] and 'mw-heading' not in node.get('class', []):
                    if node.name == 'p':
                        paras.append(node.get_text(strip=True))
                    node = node.find_next_sibling()
                return '\n'.join(paras).strip()
    except Exception as e:
        print(f"Error parsing habitat info: {e}")
    return None
