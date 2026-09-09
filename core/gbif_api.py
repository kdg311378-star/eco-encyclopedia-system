import json
import urllib.parse
import urllib.request


def get_taxon_key(name: str, rank: str) -> int:
    """
    GBIF API를 이용해 입력된 이름과 랭크(예: 'Mammalia', 'CLASS')의 Taxon Key를 조회합니다.
    """
    url = f"https://api.gbif.org/v1/species/match?name={urllib.parse.quote(name)}&rank={urllib.parse.quote(rank.upper())}"
    try:
        req = urllib.request.urlopen(url)
        data = json.loads(req.read().decode('utf-8'))
        return data.get('usageKey')
    except Exception as e:
        print(f"Error fetching taxon key for {name}: {e}")
        return None

def get_species_list(taxon_key: int, limit: int = 50) -> list[str]:
    """
    주어진 Taxon Key 하위에 있는 종(Species)들의 영문 학명(Canonical Name) 목록을 반환합니다.
    """
    url = f"https://api.gbif.org/v1/species/search?rank=SPECIES&highertaxon_key={taxon_key}&status=ACCEPTED&limit={limit}"
    try:
        req = urllib.request.urlopen(url)
        data = json.loads(req.read().decode('utf-8'))
        
        species_list = []
        for result in data.get('results', []):
            canonical = result.get('canonicalName')
            if canonical and canonical not in species_list:
                species_list.append(canonical)
        return species_list
    except Exception as e:
        print(f"Error fetching species list for taxon_key {taxon_key}: {e}")
        return []
