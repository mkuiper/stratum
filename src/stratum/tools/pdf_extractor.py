"""PDF text extraction tool using PyMuPDF."""
from pathlib import Path
from typing import Dict, List
import pymupdf
from pydantic import Field

from .base import StratumBaseTool


class PDFTextExtractorTool(StratumBaseTool):
    """
    Extracts text content from PDF files with figure/table detection.

    Uses PyMuPDF (fitz) which performs better on scientific papers
    than alternatives like PyPDF2 or pdfplumber.
    """

    name: str = "PDF Text Extractor"
    description: str = (
        "Extracts text content from PDF files. "
        "Handles scientific papers with complex layouts, equations, and multi-column text. "
        "Returns full text with page numbers and detected figure/table locations."
    )

    def _run(self, pdf_path: str) -> Dict[str, any]:
        """
        Extract text and metadata from PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dict containing:
                - text: Full extracted text
                - pages: Number of pages
                - metadata: PDF metadata (title, author, etc.)
                - figures_tables: List of detected figure/table references

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: If PDF cannot be opened or parsed
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        try:
            doc = pymupdf.open(pdf_path)
        except Exception as e:
            raise Exception(f"Cannot open PDF: {e}")

        # Extract text page by page
        text_content = []
        figures_tables = []

        for page_num, page in enumerate(doc, start=1):
            # Extract text
            text = page.get_text()

            # Simple figure/table detection by looking for keywords
            text_lower = text.lower()
            if "figure" in text_lower or "fig." in text_lower:
                figures_tables.append(f"Figure reference found on page {page_num}")
            if "table" in text_lower:
                figures_tables.append(f"Table reference found on page {page_num}")

            text_content.append(f"--- Page {page_num} ---\n{text}")

        # Extract metadata
        metadata = doc.metadata or {}

        doc.close()

        return {
            "text": "\n\n".join(text_content),
            "pages": len(doc),
            "metadata": {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "keywords": metadata.get("keywords", ""),
            },
            "figures_tables": figures_tables,
        }

    def extract_text_only(self, pdf_path: str) -> str:
        """
        Convenience method to extract just the text content.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text as string
        """
        result = self._run(pdf_path)
        return result["text"]
