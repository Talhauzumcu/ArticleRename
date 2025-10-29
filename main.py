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
    doi_regex = r'10\.\d{4,9}/[-._;()/:A-Z0-9]+'
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

def extract_first_pages(pdf_path, max_pages=2):
    """
    Extracts text from only the first N pages of a PDF.
    DOIs are typically found on the first page or two.
    """
    return extract_text(pdf_path, page_numbers=range(max_pages))

async def rename_file(pdf, session):
    print(f"Processing {pdf['article']}...")
    try:
        text = await asyncio.to_thread(extract_first_pages, pdf['path'])
        doi = find_doi(text)
        if not doi:
            print(f"No DOI found in {pdf['article']}, skipping.")
            return
        
        url = f"https://api.crossref.org/works/{doi}"
        async with session.get(url) as response:
            meta = await response.json()
        
        title = meta['message']['title'][0]
        author = f"{meta['message']['author'][0]['given']} {meta['message']['author'][0]['family']}"
        year = meta['message']['published-print']['date-parts'][0][0]
        new_name = f"{title} - {author} - {year}.pdf"
        new_name = sanitize_filename(new_name)
        new_path = os.path.join(pdf['root'], new_name)

        await asyncio.to_thread(os.rename, pdf['path'], new_path)
        print(f"Renamed {pdf['article']} to {new_name}")
    except Exception as e:
        print(f"Error processing {pdf['article']}: {e}")

    print(f"Finished processing {pdf['article']}.")

async def run():
    pdf_files = get_files(PATH)
    
    async with aiohttp.ClientSession() as session:
        tasks = [rename_file(pdf, session) for pdf in pdf_files.values()]
        await asyncio.gather(*tasks)
    


if __name__ == "__main__":
    start_time = time.perf_counter()
    asyncio.run(run())
    end_time = time.perf_counter()
    print(f"Total processing time: {end_time - start_time} seconds")