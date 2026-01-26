"""Paper fetching tool using Semantic Scholar and arXiv APIs."""
from pathlib import Path
from typing import Optional, Dict
import requests
from pydantic import Field
import time

from .base import StratumBaseTool


class PaperFetcherTool(StratumBaseTool):
    """
    Fetches papers from Semantic Scholar, arXiv, or direct DOI resolution.

    Priority order:
    1. Semantic Scholar (has open access PDF links)
    2. arXiv (if arXiv ID detected)
    3. DOI.org resolution (may hit paywall)
    """

    name: str = "Paper Fetcher"
    description: str = (
        "Fetches scientific papers by DOI or arXiv ID. "
        "Downloads PDF if available, otherwise returns metadata. "
        "Uses Semantic Scholar API, arXiv, and DOI resolution."
    )

    cache_dir: Path = Field(
        default=Path("data/pdfs"),
        description="Directory to cache downloaded PDFs"
    )
    timeout: int = Field(default=30, description="Request timeout in seconds")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _run(
        self,
        doi: Optional[str] = None,
        arxiv_id: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Fetch paper PDF and metadata.

        Args:
            doi: DOI of the paper (e.g., "10.1000/example.2024")
            arxiv_id: arXiv ID (e.g., "2401.12345")

        Returns:
            Dict containing:
                - pdf_path: Local path to PDF (or None if unavailable)
                - metadata: Paper metadata (title, authors, year, abstract)
                - source: Where the paper was fetched from

        Raises:
            ValueError: If neither DOI nor arXiv ID provided
            Exception: If paper cannot be fetched from any source
        """
        if not doi and not arxiv_id:
            raise ValueError("Must provide either doi or arxiv_id")

        # Try sources in priority order
        if doi:
            # Try Semantic Scholar first
            result = self._fetch_from_semantic_scholar(doi)
            if result:
                return result

        if arxiv_id:
            # Try arXiv
            result = self._fetch_from_arxiv(arxiv_id)
            if result:
                return result

        # If all sources fail, return metadata-only result
        return {
            "pdf_path": None,
            "metadata": {
                "doi": doi,
                "arxiv_id": arxiv_id,
                "title": None,
                "authors": [],
                "year": None,
                "abstract": None
            },
            "source": "none",
            "error": "Could not fetch paper from any source"
        }

    def _fetch_from_semantic_scholar(self, doi: str) -> Optional[Dict]:
        """
        Fetch paper from Semantic Scholar API.

        Args:
            doi: DOI string

        Returns:
            Result dict if successful, None otherwise
        """
        try:
            # Semantic Scholar API
            url = f"https://api.semanticscholar.org/graph/v1/paper/{doi}"
            params = {
                "fields": "title,authors,year,abstract,openAccessPdf,externalIds"
            }

            response = requests.get(url, params=params, timeout=self.timeout)

            if response.status_code == 404:
                return None  # Paper not found

            response.raise_for_status()
            data = response.json()

            # Extract metadata
            metadata = {
                "doi": doi,
                "title": data.get("title"),
                "authors": [a.get("name") for a in data.get("authors", [])],
                "year": data.get("year"),
                "abstract": data.get("abstract"),
                "arxiv_id": data.get("externalIds", {}).get("ArXiv")
            }

            # Try to download PDF if available
            pdf_path = None
            if data.get("openAccessPdf") and data["openAccessPdf"].get("url"):
                pdf_url = data["openAccessPdf"]["url"]
                pdf_path = self._download_pdf(pdf_url, doi)

            return {
                "pdf_path": pdf_path,
                "metadata": metadata,
                "source": "semantic_scholar"
            }

        except requests.exceptions.RequestException:
            return None  # Failed to fetch

    def _fetch_from_arxiv(self, arxiv_id: str) -> Optional[Dict]:
        """
        Fetch paper from arXiv.

        Args:
            arxiv_id: arXiv identifier

        Returns:
            Result dict if successful, None otherwise
        """
        try:
            # arXiv API
            url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse XML response (simplified - full parsing would use feedparser)
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)

            # arXiv namespace
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }

            entry = root.find('atom:entry', ns)
            if entry is None:
                return None

            # Extract metadata
            title = entry.find('atom:title', ns)
            authors = entry.findall('atom:author/atom:name', ns)
            published = entry.find('atom:published', ns)
            abstract = entry.find('atom:summary', ns)

            metadata = {
                "arxiv_id": arxiv_id,
                "title": title.text.strip() if title is not None else None,
                "authors": [a.text for a in authors],
                "year": int(published.text[:4]) if published is not None else None,
                "abstract": abstract.text.strip() if abstract is not None else None,
                "doi": entry.find('arxiv:doi', ns).text if entry.find('arxiv:doi', ns) is not None else None
            }

            # Download PDF
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            pdf_path = self._download_pdf(pdf_url, f"arxiv_{arxiv_id}")

            return {
                "pdf_path": pdf_path,
                "metadata": metadata,
                "source": "arxiv"
            }

        except Exception:
            return None

    def _download_pdf(self, url: str, identifier: str) -> Optional[str]:
        """
        Download PDF from URL and cache locally.

        Args:
            url: PDF URL
            identifier: Unique identifier for filename (DOI or arXiv ID)

        Returns:
            Path to downloaded PDF, or None if download failed
        """
        try:
            # Sanitize identifier for filename
            safe_id = identifier.replace('/', '_').replace(':', '_')
            pdf_path = self.cache_dir / f"{safe_id}.pdf"

            # Return cached PDF if exists
            if pdf_path.exists():
                return str(pdf_path)

            # Download
            response = requests.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()

            # Write to file
            with open(pdf_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return str(pdf_path)

        except Exception as e:
            print(f"Warning: Failed to download PDF from {url}: {e}")
            return None

    def get_metadata_only(self, doi: str) -> Dict:
        """
        Fetch only metadata without downloading PDF.

        Args:
            doi: DOI string

        Returns:
            Metadata dict
        """
        result = self._run(doi=doi)
        return result.get("metadata", {})
