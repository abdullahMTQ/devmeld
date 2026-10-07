# Domain: config, Purpose: parser, Layer: utility (internal to component)
import re
import os

def parse_firebase_config_txt(file_path: str) -> dict:
    """Parses the JS-style FIREBASE_CONFIG.txt into a Python dictionary."""
    config_dict = {}
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Config file not found: {file_path}")
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Regex to match key: "value" or key: 'value'
    pattern = r'(\w+)\s*:\s*["\']([^"\']*)["\']'
    matches = re.findall(pattern, content)
    
    for key, value in matches:
        config_dict[key] = value
        
    if not config_dict:
        raise ValueError("Failed to parse Firebase config. Check file format.")
        
    return config_dict
