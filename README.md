# PDF Extraction Pipeline

A Python pipeline for downloading large PDF files, extracting their text content, and saving them to GitHub for sharing with Claude in other project chats via direct link.

## Features

- Downloads PDFs from URLs (including Google Drive links)
- Processes local PDF files
- Extracts text using multiple PDF libraries (PyMuPDF, pdfplumber, PyPDF2)
- Chunks large documents for easier Claude processing
- Generates metadata for document tracking
- Outputs GitHub-ready file paths for sharing

## Installation

```bash
# Clone the repository
git clone https://github.com/<username>/pdf-library.git
cd pdf-library

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

### Download and Extract a PDF from URL

```bash
python pdf_extractor.py "https://example.com/document.pdf"
```

### Process a Google Drive PDF

```bash
python pdf_extractor.py "https://drive.google.com/file/d/FILE_ID/view" --output-name "research-paper"
```

### Process a Local PDF File

```bash
python pdf_extractor.py "/path/to/local/file.pdf" --title "My Document"
```

### With Tags for Organization

```bash
python pdf_extractor.py "https://example.com/paper.pdf" --output-name "ml-paper" --title "Machine Learning Paper" --tags "research,ml,2024"
```

## Output Structure

After running the pipeline, files are organized as:

```
extracted_pdfs/
  pdfs/           # Original PDF files
    document.pdf
  text/           # Full extracted text
    document.txt
  chunks/         # Chunked text for Claude
    document/
      chunk_001.txt
      chunk_002.txt
      ...
extraction_metadata.json  # Document tracking metadata
```

## Sharing with Claude

After extracting a PDF and pushing to GitHub:

1. **Commit your changes:**
   ```bash
   git add extracted_pdfs/ extraction_metadata.json
   git commit -m "Add extracted PDF: Document Name"
   git push origin main
   ```

2. **Get the raw GitHub URL:**
   ```
   https://raw.githubusercontent.com/<username>/pdf-library/main/extracted_pdfs/text/<document>.txt
   ```

3. **Share with Claude:**
   - In another Claude chat, paste the raw GitHub URL
   - Claude can fetch and read the content directly
   - For large documents, share individual chunk files

## Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `source` | | URL or local file path to the PDF (required) |
| `--output-name` | `-o` | Custom name for output files |
| `--title` | `-t` | Document title |
| `--tags` | | Comma-separated list of tags |

## Supported PDF Sources

- **Direct URLs**: Any publicly accessible PDF URL
- **Google Drive**: Links in format `https://drive.google.com/file/d/FILE_ID/view`
- **Local files**: Absolute or relative paths to PDF files

## Configuration

Edit `config.json` to customize:

```json
{
  "pipeline_settings": {
    "output_directory": "extracted_pdfs",
    "max_file_size_mb": 100,
    "chunk_size_characters": 50000
  },
  "claude_integration": {
    "max_chunk_size": 50000,
    "include_page_markers": true
  }
}
```

## PDF Library Priority

The pipeline automatically selects the best available PDF library:

1. **PyMuPDF** (recommended) - Best quality extraction
2. **pdfplumber** - Good for tables and structured content
3. **PyPDF2** - Fallback for simple PDFs

## Example Workflow

```bash
# 1. Extract a large PDF
python pdf_extractor.py "https://arxiv.org/pdf/1234.56789.pdf" \
  --output-name "arxiv-paper" \
  --title "Important Research Paper" \
  --tags "research,arxiv,ml"

# 2. Review the extracted files
ls extracted_pdfs/text/
ls extracted_pdfs/chunks/arxiv-paper/

# 3. Commit to GitHub
git add .
git commit -m "Add extracted PDF: Important Research Paper"
git push

# 4. Share the raw URL with Claude in another chat
# https://raw.githubusercontent.com/<username>/pdf-library/main/extracted_pdfs/text/arxiv-paper.txt
```

## Troubleshooting

### "No PDF library available"
Install at least one PDF library:
```bash
pip install pymupdf  # Recommended
# or
pip install pdfplumber
# or
pip install pypdf2
```

### Google Drive download issues
- Ensure the file is set to "Anyone with the link can view"
- For very large files, Google Drive may require additional authentication

### Large file handling
- Files over 100MB will show a warning but still process
- Use chunks for sharing large documents with Claude

## License

MIT License
