"""TODO: Add module description."""
import zipfile
import xml.etree.ElementTree as ET
import sys
import os

def get_text(filename):
    '''"""TODO: Add description.

Args:
    filename: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    try:
        with zipfile.ZipFile(filename) as z:
            xml_content = z.read('word/document.xml')
        tree = ET.fromstring(xml_content)
        lines = []
        for elem in tree.iter():
            if elem.tag.endswith('}p'):
                lines.append('\n')
            elif elem.tag.endswith('}t'):
                if elem.text:
                    lines.append(elem.text)
            elif elem.tag.endswith('}tab'):
                lines.append('\t')
        return ''.join(lines)
    except Exception as e:
        return f'Error: {str(e)}'
if __name__ == '__main__':
    sys.stdout.buffer.write(get_text('c:\\Users\\netxs\\devops\\devops\\Devops效能平台需求规格说明书V2.0.docx').encode('utf-8'))