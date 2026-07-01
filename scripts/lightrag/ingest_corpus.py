#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import urllib.error

def extract_text_from_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.md' or ext == '.txt':
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    elif ext == '.docx':
        try:
            import docx
            doc = docx.Document(filepath)
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            print(f"Error reading DOCX {filepath}: {e}")
            return None
    elif ext == '.pdf':
        try:
            import pypdf
            reader = pypdf.PdfReader(filepath)
            text = []
            for page in reader.pages:
                text.append(page.extract_text() + "\n")
            return "".join(text)
        except Exception as e:
            # Fallback to PyMuPDF if pypdf is not available
            try:
                import fitz
                doc = fitz.open(filepath)
                text = []
                for page in doc:
                    text.append(page.get_text())
                return "".join(text)
            except Exception as e2:
                print(f"Error reading PDF {filepath}: {e} / {e2}")
                return None
    else:
        print(f"Unsupported extension: {ext}")
        return None

def ingest_to_lightrag(text, api_url="http://localhost:9621"):
    if not text.strip():
        return False
    endpoint = f"{api_url}/insert"
    payload = json.dumps({"text": text}).encode('utf-8')
    req = urllib.request.Request(endpoint, data=payload, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as response:
            result = response.read()
            print(f"Ingested successfully: {result}")
            return True
    except urllib.error.URLError as e:
        print(f"Failed to ingest to LightRAG at {endpoint}: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python ingest_corpus.py <file_or_directory>")
        sys.exit(1)
        
    target = sys.argv[1]
    
    # Check env for LightRAG URL
    api_url = os.environ.get("LIGHTRAG_API_URL", "http://localhost:9621")
    
    if os.path.isfile(target):
        print(f"Processing file: {target}")
        text = extract_text_from_file(target)
        if text:
            ingest_to_lightrag(text, api_url)
    elif os.path.isdir(target):
        print(f"Processing directory: {target}")
        for root, _, files in os.walk(target):
            for file in files:
                filepath = os.path.join(root, file)
                print(f"Processing {filepath}...")
                text = extract_text_from_file(filepath)
                if text:
                    ingest_to_lightrag(text, api_url)
    else:
        print(f"Not found: {target}")

if __name__ == '__main__':
    main()
