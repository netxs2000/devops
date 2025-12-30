import zipfile
import re
import xml.etree.ElementTree as ET

docx_path = r'c:\Users\netxs\devops\devops\docs\api\MDM_DATA_DICTIONARY.docx'

try:
    with zipfile.ZipFile(docx_path) as z:
        xml_content = z.read('word/document.xml')
        
    # Python's XML parser might choke on namespaces if not handled, 
    # but let's try a simple regex approach first to extract tables if possible, 
    # or just all text.
    
    # Extract all text within <w:t> tags
    text_content = ""
    # Naive XML parsing to get text
    root = ET.fromstring(xml_content)
    
    # Namespaces
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    
    body = root.find('w:body', ns)
    
    # Iterate over paragraphs and tables
    for element in body:
        if element.tag.endswith('tbl'): # Table
            print("\n[TABLE START]")
            for row in element.findall('.//w:tr', ns):
                row_text = []
                for cell in row.findall('.//w:tc', ns):
                    cell_texts = []
                    for t in cell.findall('.//w:t', ns):
                        if t.text:
                            cell_texts.append(t.text)
                    row_text.append("".join(cell_texts))
                print(" | ".join(row_text))
            print("[TABLE END]\n")
        elif element.tag.endswith('p'): # Paragraph
            para_texts = []
            for t in element.findall('.//w:t', ns):
                if t.text:
                    para_texts.append(t.text)
            print("".join(para_texts))

except Exception as e:
    print(f"Error reading docx: {e}")
