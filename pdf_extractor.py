#!/usr/bin/env python3
"""
PDF Extraction Pipeline for Large PDF Files

This pipeline downloads a single large PDF file, extracts its text content,
and saves both the PDF and extracted text to be committed to GitHub.
The files can then be shared with Claude in another project chat via direct link.

Usage:
    python pdf_extractor.py <url_or_path> [--output-name <name>]
    python pdf_extractor.py --help

Examples:
    python pdf_extractor.py "https://example.com/large-document.pdf"
    python pdf_extractor.py "https://drive.google.com/file/d/FILE_ID/view" --output-name "research-paper"
    python pdf_extractor.py "/path/to/local/file.pdf" --output-name "my-document"
"""

import os
import sys
import re
import json
import hashlib
import argparse
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

# Try to import PDF libraries
try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False


# Configuration
OUTPUT_DIR = Path(__file__).parent / "extracted_pdfs"
METADATA_FILE = Path(__file__).parent / "extraction_metadata.json"
MAX_FILE_SIZE_MB = 100  # Maximum file size to download in MB
CHUNK_SIZE = 8192  # Download chunk size


class PDFExtractor:
    """Main class for downloading and extracting PDF content."""

    def __init__(self, output_dir: Path = OUTPUT_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (self.output_dir / "pdfs").mkdir(exist_ok=True)
        (self.output_dir / "text").mkdir(exist_ok=True)
        (self.output_dir / "chunks").mkdir(exist_ok=True)

        # Determine best available PDF library
        self.pdf_library = self._get_best_pdf_library()

    def _get_best_pdf_library(self) -> str:
        """Determine the best available PDF library."""
        if HAS_PYMUPDF:
            return "pymupdf"
        elif HAS_PDFPLUMBER:
            return "pdfplumber"
        elif HAS_PYPDF2:
            return "pypdf2"
        else:
            return "none"

    def _generate_doc_id(self, source: str) -> str:
        """Generate a unique document ID from the source."""
        return hashlib.md5(source.encode()).hexdigest()[:16]

    def _extract_google_drive_id(self, url: str) -> Optional[str]:
        """Extract Google Drive file ID from various URL formats."""
        patterns = [
            r'/file/d/([a-zA-Z0-9_-]+)',
            r'id=([a-zA-Z0-9_-]+)',
            r'/open\?id=([a-zA-Z0-9_-]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _get_google_drive_download_url(self, file_id: str) -> str:
        """Convert Google Drive file ID to direct download URL."""
        return f"https://drive.google.com/uc?export=download&id={file_id}"

    def _download_file(self, url: str, output_path: Path, show_progress: bool = True) -> bool:
        """Download a file from URL with progress indicator."""
        try:
            # Check if it's a Google Drive URL
            drive_id = self._extract_google_drive_id(url)
            if drive_id:
                url = self._get_google_drive_download_url(drive_id)
                print(f"Detected Google Drive URL. File ID: {drive_id}")

            print(f"Downloading from: {url}")

            # Create request with headers to mimic browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            request = urllib.request.Request(url, headers=headers)

            with urllib.request.urlopen(request, timeout=300) as response:
                # Check content length if available
                content_length = response.headers.get('Content-Length')
                if content_length:
                    file_size = int(content_length)
                    file_size_mb = file_size / (1024 * 1024)
                    print(f"File size: {file_size_mb:.2f} MB")

                    if file_size_mb > MAX_FILE_SIZE_MB:
                        print(f"Warning: File exceeds {MAX_FILE_SIZE_MB}MB limit. Proceeding anyway...")

                # Download with progress
                downloaded = 0
                with open(output_path, 'wb') as f:
                    while True:
                        chunk = response.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if show_progress and content_length:
                            percent = (downloaded / file_size) * 100
                            print(f"\rProgress: {percent:.1f}% ({downloaded / (1024*1024):.2f} MB)", end="")

                if show_progress:
                    print()  # New line after progress

            print(f"Download complete: {output_path}")
            return True

        except Exception as e:
            print(f"Error downloading file: {e}")
            return False

    def _extract_text_pymupdf(self, pdf_path: Path) -> Tuple[str, int]:
        """Extract text using PyMuPDF (fitz)."""
        doc = fitz.open(pdf_path)
        text_parts = []
        page_count = len(doc)

        for page_num in range(page_count):
            page = doc.load_page(page_num)
            text = page.get_text()
            text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

        doc.close()
        return "\n\n".join(text_parts), page_count

    def _extract_text_pdfplumber(self, pdf_path: Path) -> Tuple[str, int]:
        """Extract text using pdfplumber."""
        text_parts = []

        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                text_parts.append(f"--- Page {i + 1} ---\n{text}")

        return "\n\n".join(text_parts), page_count

    def _extract_text_pypdf2(self, pdf_path: Path) -> Tuple[str, int]:
        """Extract text using PyPDF2."""
        text_parts = []

        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            page_count = len(reader.pages)

            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                text_parts.append(f"--- Page {i + 1} ---\n{text}")

        return "\n\n".join(text_parts), page_count

    def extract_text(self, pdf_path: Path) -> Tuple[str, int]:
        """Extract text from PDF using the best available library."""
        print(f"Extracting text using: {self.pdf_library}")

        if self.pdf_library == "pymupdf":
            return self._extract_text_pymupdf(pdf_path)
        elif self.pdf_library == "pdfplumber":
            return self._extract_text_pdfplumber(pdf_path)
        elif self.pdf_library == "pypdf2":
            return self._extract_text_pypdf2(pdf_path)
        else:
            raise RuntimeError(
                "No PDF library available. Install one of: "
                "PyMuPDF (pip install pymupdf), "
                "pdfplumber (pip install pdfplumber), "
                "or PyPDF2 (pip install pypdf2)"
            )

    def _chunk_text(self, text: str, chunk_size: int = 50000) -> list:
        """Split text into chunks for easier handling by Claude."""
        chunks = []
        current_chunk = ""

        paragraphs = text.split("\n\n")

        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def process_pdf(
        self,
        source: str,
        output_name: Optional[str] = None,
        title: Optional[str] = None,
        tags: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Main method to process a PDF file.

        Args:
            source: URL or local file path to the PDF
            output_name: Custom name for output files (without extension)
            title: Document title (auto-detected if not provided)
            tags: List of tags for categorization

        Returns:
            Dictionary with extraction results and file paths
        """
        print("=" * 60)
        print("PDF EXTRACTION PIPELINE")
        print("=" * 60)

        # Generate document ID and output name
        doc_id = self._generate_doc_id(source)

        if output_name:
            safe_name = re.sub(r'[^\w\-]', '_', output_name)
        else:
            safe_name = doc_id

        # Determine if source is URL or local file
        is_url = source.startswith(('http://', 'https://'))

        # Set up paths
        pdf_path = self.output_dir / "pdfs" / f"{safe_name}.pdf"
        text_path = self.output_dir / "text" / f"{safe_name}.txt"
        chunks_dir = self.output_dir / "chunks" / safe_name

        # Download or copy file
        if is_url:
            print(f"\nSource: {source}")
            if not self._download_file(source, pdf_path):
                return {"success": False, "error": "Download failed"}
        else:
            # Local file - copy to output directory
            source_path = Path(source)
            if not source_path.exists():
                return {"success": False, "error": f"File not found: {source}"}

            import shutil
            shutil.copy2(source_path, pdf_path)
            print(f"Copied local file to: {pdf_path}")

        # Extract text
        print("\nExtracting text from PDF...")
        try:
            extracted_text, page_count = self.extract_text(pdf_path)
            print(f"Extracted {len(extracted_text)} characters from {page_count} pages")
        except Exception as e:
            return {"success": False, "error": f"Text extraction failed: {e}"}

        # Save full text
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(extracted_text)
        print(f"Saved full text to: {text_path}")

        # Create chunks for easier Claude processing
        chunks = self._chunk_text(extracted_text)
        chunks_dir.mkdir(parents=True, exist_ok=True)

        chunk_files = []
        for i, chunk in enumerate(chunks):
            chunk_path = chunks_dir / f"chunk_{i+1:03d}.txt"
            with open(chunk_path, 'w', encoding='utf-8') as f:
                f.write(f"# Chunk {i+1} of {len(chunks)}\n")
                f.write(f"# Document: {title or safe_name}\n")
                f.write(f"# Characters: {len(chunk)}\n\n")
                f.write(chunk)
            chunk_files.append(str(chunk_path))

        print(f"Created {len(chunks)} text chunks in: {chunks_dir}")

        # Calculate file size
        pdf_size_mb = pdf_path.stat().st_size / (1024 * 1024)

        # Prepare result
        result = {
            "success": True,
            "doc_id": doc_id,
            "source_url": source if is_url else None,
            "local_source": source if not is_url else None,
            "title": title or safe_name,
            "tags": tags or [],
            "page_count": page_count,
            "character_count": len(extracted_text),
            "chunk_count": len(chunks),
            "file_size_mb": round(pdf_size_mb, 2),
            "extraction_date": datetime.now().isoformat(),
            "pdf_library_used": self.pdf_library,
            "files": {
                "pdf": str(pdf_path),
                "full_text": str(text_path),
                "chunks_dir": str(chunks_dir),
                "chunk_files": chunk_files
            },
            "github_paths": {
                "pdf": f"extracted_pdfs/pdfs/{safe_name}.pdf",
                "full_text": f"extracted_pdfs/text/{safe_name}.txt",
                "chunks": f"extracted_pdfs/chunks/{safe_name}/"
            }
        }

        # Update metadata file
        self._update_metadata(result)

        # Print summary
        self._print_summary(result)

        return result

    def _update_metadata(self, result: Dict[str, Any]) -> None:
        """Update the metadata JSON file with extraction results."""
        if METADATA_FILE.exists():
            with open(METADATA_FILE, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {
                "last_updated": None,
                "document_count": 0,
                "documents": {}
            }

        # Add/update document entry
        doc_id = result["doc_id"]
        metadata["documents"][doc_id] = {
            "doc_id": doc_id,
            "source_url": result.get("source_url"),
            "local_source": result.get("local_source"),
            "title": result["title"],
            "tags": result["tags"],
            "page_count": result["page_count"],
            "character_count": result["character_count"],
            "chunk_count": result["chunk_count"],
            "file_size_mb": result["file_size_mb"],
            "extraction_date": result["extraction_date"],
            "github_paths": result["github_paths"]
        }

        metadata["document_count"] = len(metadata["documents"])
        metadata["last_updated"] = datetime.now().isoformat()

        with open(METADATA_FILE, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"Updated metadata: {METADATA_FILE}")

    def _print_summary(self, result: Dict[str, Any]) -> None:
        """Print a summary of the extraction."""
        print("\n" + "=" * 60)
        print("EXTRACTION COMPLETE")
        print("=" * 60)
        print(f"Document ID:     {result['doc_id']}")
        print(f"Title:           {result['title']}")
        print(f"Pages:           {result['page_count']}")
        print(f"Characters:      {result['character_count']:,}")
        print(f"Chunks:          {result['chunk_count']}")
        print(f"File Size:       {result['file_size_mb']} MB")
        print(f"PDF Library:     {result['pdf_library_used']}")
        print("-" * 60)
        print("OUTPUT FILES:")
        print(f"  PDF:        {result['files']['pdf']}")
        print(f"  Full Text:  {result['files']['full_text']}")
        print(f"  Chunks:     {result['files']['chunks_dir']}")
        print("-" * 60)
        print("GITHUB PATHS (after commit):")
        print(f"  PDF:        {result['github_paths']['pdf']}")
        print(f"  Full Text:  {result['github_paths']['full_text']}")
        print(f"  Chunks:     {result['github_paths']['chunks']}")
        print("=" * 60)
        print("\nTo share with Claude in another chat, use the raw GitHub URL:")
        print(f"  https://raw.githubusercontent.com/<username>/pdf-library/main/{result['github_paths']['full_text']}")
        print("\nNext steps:")
        print("  1. git add extracted_pdfs/ extraction_metadata.json")
        print("  2. git commit -m 'Add extracted PDF: {}'".format(result['title']))
        print("  3. git push origin <branch-name>")
        print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PDF Extraction Pipeline - Download and extract text from large PDF files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "https://example.com/document.pdf"
  %(prog)s "https://drive.google.com/file/d/FILE_ID/view" --output-name "research-paper"
  %(prog)s "/path/to/local/file.pdf" --title "My Document" --tags research,science
        """
    )

    parser.add_argument(
        "source",
        help="URL or local file path to the PDF"
    )
    parser.add_argument(
        "--output-name", "-o",
        help="Custom name for output files (without extension)"
    )
    parser.add_argument(
        "--title", "-t",
        help="Document title"
    )
    parser.add_argument(
        "--tags",
        help="Comma-separated list of tags"
    )

    args = parser.parse_args()

    # Parse tags
    tags = None
    if args.tags:
        tags = [t.strip() for t in args.tags.split(",")]

    # Create extractor and process
    extractor = PDFExtractor()
    result = extractor.process_pdf(
        source=args.source,
        output_name=args.output_name,
        title=args.title,
        tags=tags
    )

    if not result["success"]:
        print(f"\nError: {result.get('error', 'Unknown error')}")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
