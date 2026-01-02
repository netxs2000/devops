"""TODO: Add module description."""
import zipfile
import xml.etree.ElementTree as ET
import sys
import os

def read_docx(file_path):
    '''"""TODO: Add description.

Args:
    file_path: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    try:
        with zipfile.ZipFile(file_path) as z:
            xml_content = z.read('word/document.xml')
        tree = ET.fromstring(xml_content)
        namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        text_content = []
        for p in tree.findall('.//w:p', namespaces):
            paragraph_text = []
            for r in p.findall('.//w:r', namespaces):
                for t in r.findall('.//w:t', namespaces):
                    if t.text:
                        paragraph_text.append(t.text)
            if paragraph_text:
                text_content.append(''.join(paragraph_text))
            else:
                text_content.append('')
        print('\n'.join(text_content))
    except Exception as e:
        print(f'Error reading .docx file: {str(e)}')
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python extract_docx.py <path_to_docx>')
    else:
        read_docx(sys.argv[1])