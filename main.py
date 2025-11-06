from asyncio import tasks
from pdfminer.high_level import extract_text
import re
import os
import aiohttp
import sys
import asyncio
import time

if len(sys.argv) != 2:
    print("Usage: python main.py <path_to_directory>")
    sys.exit(1)

PATH = sys.argv[1]

def find_doi(text):
    """
    Finds a DOI in a string of text.
    """
    # doi_regex = r'10\.\d{4,9}/[-._;()/:A-Z0-9]+'
    doi_regex = r'(10\.\d{4,9}/[^\s"<>]+)'
    match = re.search(doi_regex, text, re.IGNORECASE)
    if match:
        return match.group(0)
    return None

def sanitize_filename(name):
    """
    Removes illegal characters from a string so it can be used as a filename.
    """
    # This regex matches any character that is NOT allowed in a Windows filename
    return re.sub(r'[\\/*?:"<>|]', "", name)

def get_files(path):
    """
    Gets all PDF files in a directory and its subdirectories.
    """
    pdf_files = {}
    
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".pdf"):
                pdf_files[file] = {'path': os.path.join(root, file), 'root': root, 'article': file} 
    return pdf_files

def extract_first_pages(pdf_path, max_pages=4):
    """
    Extracts text from only the first N pages of a PDF.
    DOIs are typically found on the first page or two.
    """
    return extract_text(pdf_path, page_numbers=range(max_pages))

async def find_meta_by_metadata(text, session):
    # crude title extraction: first line(s)
    first_lines = " ".join(text.splitlines()[:15])
    query = first_lines[:500]
    url = f"https://api.crossref.org/works?query.title={query}&rows=1"
    try:
        async with session.get(url) as r:
            if r.status != 200:
                return None
            meta = await r.json()
            if meta.get('message', {}).get('items'):
                return {'message': meta['message']['items'][0]}
            return None
    except Exception as e:
        print(f"Metadata lookup failed: {e}")
        return None

def get_newname(meta):
    msg = meta.get('message', {})
    title = msg.get('title', ['Unknown Title'])[0] if msg.get('title') else 'Unknown Title'
    
    author = 'Unknown Author'
    if msg.get('author') and len(msg['author']) > 0:
        first_author = msg['author'][0]
        given = first_author.get('given', '')
        family = first_author.get('family', '')
        if given and family:
            author = f"{given} {family}"
        elif family:
            author = family
        elif given:
            author = given
    elif msg.get('editor') and len(msg['editor']) > 0:
        # Fallback to editor if no author
        first_editor = msg['editor'][0]
        given = first_editor.get('given', '')
        family = first_editor.get('family', '')
        if given and family:
            author = f"{given} {family}"
        elif family:
            author = family
    
    year = 'Unknown Year'
    date_fields = ['published-print', 'published-online', 'created', 'issued']
    for field in date_fields:
        if msg.get(field) and msg[field].get('date-parts'):
            try:
                year = msg[field]['date-parts'][0][0]
                break
            except (IndexError, TypeError):
                continue
    
    new_name = f"{author}, {year} - {title}.pdf"
    new_name = sanitize_filename(new_name)
    return new_name

async def rename_file(pdf, session):
    try:
        text = await asyncio.to_thread(extract_first_pages, pdf['path'])
        text = re.sub(r'\s+', ' ', text)
        doi = find_doi(text)

        if doi:
            doi = doi.strip().rstrip('.,;()[]{}<>')
            url = f"https://api.crossref.org/works/{doi}"
            async with session.get(url) as response:
                if response.status != 200:
                    print(f"Failed to fetch DOI {doi} for {pdf['article']}: Status {response.status}")
                    return
                if "application/json" not in response.headers.get("Content-Type", ""):
                    print(f"Non-JSON response for {pdf['article']} ({doi})")
                    return
                # Read the JSON INSIDE the context manager
                meta = await response.json()
        else:
            print(f"No DOI found in {pdf['article']} via direct search, trying metadata lookup.")
            meta = await find_meta_by_metadata(text, session)

        if not meta:
            print(f"No meta found for {pdf['article']}, skipping.")
            return

        new_name = get_newname(meta)
        
        # Check if we actually got useful metadata
        if 'Unknown' in new_name:
            print(f"Incomplete metadata for {pdf['article']}: {new_name}")
        new_path = os.path.join(pdf['root'], new_name)

        # Check if file already exists with that name
        if os.path.exists(new_path):
            # print(f"File already exists: {new_name}, skipping {pdf['article']}")
            return

        await asyncio.to_thread(os.rename, pdf['path'], new_path)
        print(f"✓ Renamed: {pdf['article']} → {new_name}")
    except Exception as e:
        print(f"✗ Error processing {pdf['article']}: {e}")


async def run():
    pdf_files = get_files(PATH)
    
    # Configure timeout and connection limits
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
    
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        tasks = [rename_file(pdf, session) for pdf in pdf_files.values()]
        await asyncio.gather(*tasks, return_exceptions=True)
    
if __name__ == "__main__":
    start_time = time.perf_counter()
    asyncio.run(run())
    end_time = time.perf_counter()
    print(f"Total processing time: {end_time - start_time} seconds")