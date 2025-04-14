from typing import Dict, Any

def to_camel(string: str) -> str:
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

def to_snake(string: str) -> str:
    return ''.join(['_'+c.lower() if c.isupper() else c for c in string]).lstrip('_')

def dict_to_camel(d: Dict[str, Any]) -> Dict[str, Any]:
    return {to_camel(k): v for k, v in d.items()}

def dict_to_snake(d: Dict[str, Any]) -> Dict[str, Any]:
    return {to_snake(k): v for k, v in d.items()} 