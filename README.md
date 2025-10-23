# ArticleRename

This very small project was born out of my laziness of renaming articles after I downloaded them. It automatically renames PDF articles 
based on their metadata (title, author, and publication year) by extracting DOI information from the PDFs.

## Installation

1. Clone this repository:
```bash
git clone https://github.com/Talhauzumcu/ArticleRename.git
cd ArticleRename
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```
## Usage

Run the script with the path to the directory containing your PDF files:

```bash
python main.py <path_to_directory>
```

### Example

```bash
python main.py "C:\Users\username\Documents\Research Papers"
```

The script will:
1. Scan the directory and all subdirectories for PDF files
2. Extract text from each PDF
3. Search for DOI patterns in the text
4. Query the CrossRef API for metadata
5. Rename the file to: `[Title] - [First Author] - [Year].pdf`