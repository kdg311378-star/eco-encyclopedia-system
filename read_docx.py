import zipfile
import xml.etree.ElementTree as ET

def extract(doc_path):
    doc = zipfile.ZipFile(doc_path)
    xml_content = doc.read('word/document.xml')
    tree = ET.XML(xml_content)
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    paras = [node.text for node in tree.findall('.//w:t', ns) if node.text]
    with open('docx_content.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(paras))

if __name__ == "__main__":
    extract(r'c:\Users\kdg99\Downloads\[참고 자료].docx')
