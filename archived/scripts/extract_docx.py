"""TODO: Add module description."""
import zipfile
import re
import xml.etree.ElementTree as ET
docx_path = 'c:\\Users\\netxs\\devops\\devops\\docs\\api\\MDM_DATA_DICTIONARY.docx'
try:
    with zipfile.ZipFile(docx_path) as z:
        xml_content = z.read('word/document.xml')
    text_content = ''
    root = ET.fromstring(xml_content)
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    body = root.find('w:body', ns)
    for element in body:
        if element.tag.endswith('tbl'):
            print('\n[TABLE START]')
            for row in element.findall('.//w:tr', ns):
                row_text = []
                for cell in row.findall('.//w:tc', ns):
                    cell_texts = []
                    for t in cell.findall('.//w:t', ns):
                        if t.text:
                            cell_texts.append(t.text)
                    row_text.append(''.join(cell_texts))
                print(' | '.join(row_text))
            print('[TABLE END]\n')
        elif element.tag.endswith('p'):
            para_texts = []
            for t in element.findall('.//w:t', ns):
                if t.text:
                    para_texts.append(t.text)
            print(''.join(para_texts))
except Exception as e:
    print(f'Error reading docx: {e}')