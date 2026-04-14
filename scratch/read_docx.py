import zipfile
import xml.etree.ElementTree as ET

def read_docx(path):
    with zipfile.ZipFile(path) as docx:
        tree = ET.XML(docx.read('word/document.xml'))
        namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        paragraphs = []
        for p in tree.findall('.//w:p', namespaces):
            texts = [node.text for node in p.findall('.//w:t', namespaces) if node.text]
            if texts:
                paragraphs.append(''.join(texts))
        return '\n\n'.join(paragraphs)

text = read_docx(r'd:\Antigravity\Project Directory\product_architecture_and_flow.docx')
with open(r'd:\Antigravity\Project Directory\scratch\project_document.md', 'w', encoding='utf-8') as f:
    f.write(text)
print("Successfully extracted docx to markdown.")
