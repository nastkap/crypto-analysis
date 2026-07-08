#!/usr/bin/env python3
"""Generate PNG from PlantUML using online API"""

import urllib.request
import urllib.parse
import base64
import zlib
import os
import sys

def encode_plantuml(puml_code: str) -> str:
    """Encode PlantUML code to URL-safe format"""
    compressed = zlib.compress(puml_code.encode('utf-8'))
    # PlantUML uses a custom base64 alphabet
    b64 = base64.b64encode(compressed).decode('ascii')
    # Replace standard base64 chars with PlantUML's alphabet
    return b64.replace('+', '-').replace('/', '_')

def generate_diagram(puml_file: str, output_file: str = None):
    """Generate PNG from .puml file using online PlantUML API"""
    
    if not os.path.exists(puml_file):
        print(f"File not found: {puml_file}")
        sys.exit(1)
    
    if output_file is None:
        output_file = puml_file.replace('.puml', '.png')
    
    # Read PlantUML file
    with open(puml_file, 'r', encoding='utf-8') as f:
        puml_code = f.read()
    
    print(f"Reading: {puml_file}")
    print(f"PlantUML code length: {len(puml_code)} chars")
    
    # Encode
    encoded = encode_plantuml(puml_code)
    print(f"Encoded successfully: {len(encoded)} chars")
    
    # Build URL for PlantUML online service
    url = f"https://www.plantuml.com/plantuml/png/{encoded}"
    
    print(f"Fetching from: {url[:80]}...")
    
    try:
        # Fetch PNG from PlantUML online service
        response = urllib.request.urlopen(url, timeout=30)
        png_data = response.read()
        
        # Save PNG
        with open(output_file, 'wb') as f:
            f.write(png_data)
        
        file_size_kb = len(png_data) / 1024
        print(f" Generated: {output_file}")
        print(f" File size: {file_size_kb:.1f} KB")
        
    except Exception as e:
        print(f" Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python generate_diagram.py <input.puml> [output.png]")
        sys.exit(1)
    
    puml_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    generate_diagram(puml_file, output_file)
