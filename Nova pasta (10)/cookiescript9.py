# cookiescript/xml.py
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional

class XMLOps:
    """Operações com XML"""

    def parse_xml(self, xml_string: str) -> ET.Element:
        """Faz parse de uma string XML"""
        return ET.fromstring(xml_string)

    def xml_to_dict(self, xml_element: ET.Element) -> Dict[str, Any]:
        """Converte elemento XML para dicionário"""
        def element_to_dict(element):
            result = {}
            result['tag'] = element.tag
            result['attributes'] = element.attrib
            result['text'] = element.text.strip() if element.text else None
            result['children'] = [element_to_dict(child) for child in element]
            return result

        return element_to_dict(xml_element)

    def dict_to_xml(self, data: Dict[str, Any]) -> str:
        """Converte dicionário para XML string"""
        def dict_to_element(data, parent=None):
            if isinstance(data, dict):
                element = ET.Element(data.get('tag', 'root'))
                for key, value in data.get('attributes', {}).items():
                    element.set(key, str(value))
                if 'text' in data and data['text']:
                    element.text = str(data['text'])
                for child in data.get('children', []):
                    dict_to_element(child, element)
                if parent is not None:
                    parent.append(element)
                return element
            return None

        root = dict_to_element(data)
        return ET.tostring(root, encoding='unicode', method='xml')

    def find_element(self, xml_element: ET.Element, xpath: str) -> Optional[ET.Element]:
        """Encontra elemento usando XPath"""
        return xml_element.find(xpath)

    def find_all_elements(self, xml_element: ET.Element, xpath: str) -> list:
        """Encontra todos os elementos usando XPath"""
        return xml_element.findall(xpath)

    def get_element_text(self, xml_element: ET.Element) -> str:
        """Obtém texto de um elemento"""
        return xml_element.text or ""

    def get_element_attribute(self, xml_element: ET.Element, attribute: str) -> Optional[str]:
        """Obtém atributo de um elemento"""
        return xml_element.get(attribute)