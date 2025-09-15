
#%%
#%%
from pdfminer.high_level import extract_text
import re
import os
import requests
#%%
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


PATH = r"C:\Users\talha\OneDrive\Masaüstü\HTO\lit"


for root, dirs, files in os.walk(PATH):
    for file in files:
        if file.endswith(".pdf"):
            article = file
            article_path = os.path.join(PATH, article)
            text = extract_text(article_path)
            doi = find_doi(text)
            if not doi:
                print(f"No DOI found in {article}")
                continue
                
            url = f"https://api.crossref.org/works/{doi}"
            meta = requests.get(url).json()
            title = meta['message']['title'][0]
            author = f"{meta['message']['author'][0]['given']} {meta['message']['author'][0]['family']}"
            year = meta['message']['published-print']['date-parts'][0][0]
            new_name = f"{title} - {author} - {year}.pdf"
            new_name = sanitize_filename(new_name)
            new_path = os.path.join(PATH, new_name)

            os.rename(article_path, new_path)
            print(f"Renamed {article} to {new_name}")
            

