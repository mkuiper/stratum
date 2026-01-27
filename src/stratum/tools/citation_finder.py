"""Citation extraction tool using GROBID service."""
from pathlib import Path
from typing import List, Dict, Optional
import requests
from pydantic import Field
import xml.etree.ElementTree as ET
import urllib.parse
import time

from .base import StratumBaseTool


class CitationFinderTool(StratumBaseTool):
    """
    Extracts and parses citations from scientific papers using GROBID.

    GROBID achieves F1 of 0.89 for citation parsing, best-in-class
    for scientific literature.
    """

    name: str = "Citation Finder"
    description: str = (
        "Extracts structured citations from PDF files using GROBID service. "
        "Returns title, authors, year, and DOI for each citation. "
        "Requires GROBID service running on configured URL."
    )

    grobid_url: str = Field(
        default="http://localhost:8070/api/processReferences",
        description="GROBID API endpoint URL"
    )
    crossref_url: str = Field(
        default="https://api.crossref.org/works",
        description="CrossRef API endpoint for DOI lookup"
    )
    timeout: int = Field(default=60, description="Request timeout in seconds")
    lookup_dois: bool = Field(default=True, description="Enable DOI lookup via CrossRef")
    max_doi_lookups: int = Field(default=10, description="Max citations to look up DOIs for")

    def _run(self, pdf_path: str) -> List[Dict[str, any]]:
        """
        Extract citations from PDF using GROBID.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of citation dicts, each containing:
                - title: Paper title
                - authors: List of author names
                - year: Publication year (or None)
                - doi: DOI (or None)
                - raw_reference: Original reference string

        Raises:
            FileNotFoundError: If PDF doesn't exist
            ConnectionError: If GROBID service is not available
            Exception: If GROBID returns error
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        try:
            with open(pdf_path, 'rb') as f:
                files = {'input': f}
                response = requests.post(
                    self.grobid_url,
                    files=files,
                    timeout=self.timeout
                )
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(
                f"Cannot connect to GROBID at {self.grobid_url}. "
                "Is GROBID running? Start with: "
                "docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.0"
            ) from e
        except requests.exceptions.Timeout as e:
            raise Exception(f"GROBID request timed out after {self.timeout}s") from e

        if response.status_code != 200:
            raise Exception(
                f"GROBID error: HTTP {response.status_code}\n{response.text[:200]}"
            )

        # Parse GROBID TEI-XML response
        citations = self._parse_tei_xml(response.text)

        # Look up DOIs for citations that don't have them
        if self.lookup_dois:
            citations = self._enrich_with_dois(citations)

        return citations

    def _enrich_with_dois(self, citations: List[Dict]) -> List[Dict]:
        """
        Look up DOIs for citations using CrossRef API.

        Args:
            citations: List of citation dicts

        Returns:
            Citations with DOIs filled in where possible
        """
        lookups_done = 0

        for citation in citations:
            # Skip if already has DOI
            if citation.get("doi"):
                continue

            # Skip if no title to search
            if not citation.get("title"):
                continue

            # Limit lookups to avoid rate limiting
            if lookups_done >= self.max_doi_lookups:
                break

            # Try to find DOI via CrossRef
            doi = self._lookup_doi_crossref(
                title=citation["title"],
                authors=citation.get("authors", []),
                year=citation.get("year")
            )

            if doi:
                citation["doi"] = doi

            lookups_done += 1

            # Be nice to CrossRef API - small delay between requests
            time.sleep(0.1)

        return citations

    def _lookup_doi_crossref(
        self,
        title: str,
        authors: List[str] = None,
        year: int = None
    ) -> Optional[str]:
        """
        Look up a DOI using CrossRef API.

        Args:
            title: Paper title
            authors: List of author names (optional)
            year: Publication year (optional)

        Returns:
            DOI string if found, None otherwise
        """
        if not title or len(title) < 10:
            return None

        try:
            # Build query
            query = title

            # Add first author if available
            if authors and len(authors) > 0:
                first_author = authors[0].split(",")[0]  # Get surname
                query = f"{query} {first_author}"

            # URL encode the query
            encoded_query = urllib.parse.quote(query)

            # Build URL with filters
            url = f"{self.crossref_url}?query={encoded_query}&rows=3"

            # Add year filter if available
            if year:
                url += f"&filter=from-pub-date:{year},until-pub-date:{year}"

            # Make request with polite headers
            headers = {
                "User-Agent": "Stratum/1.0 (https://github.com/mkuiper/stratum; mailto:stratum@example.com)"
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                return None

            data = response.json()
            items = data.get("message", {}).get("items", [])

            if not items:
                return None

            # Check if top result is a good match
            top_result = items[0]
            result_title = " ".join(top_result.get("title", []))

            # Simple title similarity check (case-insensitive, first 50 chars)
            if self._titles_match(title, result_title):
                return top_result.get("DOI")

            return None

        except Exception as e:
            # Silently fail - DOI lookup is best-effort
            return None

    def _titles_match(self, title1: str, title2: str) -> bool:
        """
        Check if two titles are similar enough to be the same paper.

        Args:
            title1: First title
            title2: Second title

        Returns:
            True if titles match
        """
        # Normalize: lowercase, remove punctuation
        def normalize(t):
            return "".join(c.lower() for c in t if c.isalnum() or c.isspace())[:80]

        t1 = normalize(title1)
        t2 = normalize(title2)

        # Check if one contains the other, or very similar
        if t1 in t2 or t2 in t1:
            return True

        # Check word overlap
        words1 = set(t1.split())
        words2 = set(t2.split())

        if len(words1) < 3 or len(words2) < 3:
            return False

        overlap = len(words1 & words2)
        total = min(len(words1), len(words2))

        return overlap / total > 0.7

    def _parse_tei_xml(self, tei_xml: str) -> List[Dict[str, any]]:
        """
        Parse GROBID TEI-XML format to extract citation data.

        Args:
            tei_xml: TEI-XML string from GROBID

        Returns:
            List of parsed citations
        """
        # Use fallback parser - grobid-tei-xml expects full document XML
        # but processReferences returns simplified XML without full header
        return self._parse_tei_xml_fallback(tei_xml)

    def _parse_tei_xml_fallback(self, tei_xml: str) -> List[Dict[str, any]]:
        """
        Fallback TEI-XML parser using standard library.

        Args:
            tei_xml: TEI-XML string

        Returns:
            List of parsed citations (with less detail than full parser)
        """
        try:
            root = ET.fromstring(tei_xml)

            # TEI namespace
            ns = {'tei': 'http://www.tei-c.org/ns/1.0'}

            citations = []
            for bibl in root.findall('.//tei:listBibl/tei:biblStruct', ns):
                # Extract title
                title_elem = bibl.find('.//tei:title[@level="a"]', ns)
                title = title_elem.text if title_elem is not None else ""

                # Extract authors
                authors = []
                for author in bibl.findall('.//tei:author/tei:persName', ns):
                    forename = author.find('tei:forename', ns)
                    surname = author.find('tei:surname', ns)
                    if surname is not None:
                        name = f"{surname.text}"
                        if forename is not None:
                            name = f"{surname.text}, {forename.text}"
                        authors.append(name)

                # Extract year
                year_elem = bibl.find('.//tei:date[@type="published"]', ns)
                year = None
                if year_elem is not None and 'when' in year_elem.attrib:
                    try:
                        year = int(year_elem.attrib['when'][:4])
                    except (ValueError, IndexError):
                        pass

                # Extract DOI
                doi_elem = bibl.find('.//tei:idno[@type="DOI"]', ns)
                doi = doi_elem.text if doi_elem is not None else None

                citation = {
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "doi": doi,
                    "raw_reference": ""
                }
                citations.append(citation)

            return citations

        except ET.ParseError as e:
            # If XML parsing fails, return empty list
            print(f"Warning: Could not parse GROBID XML: {e}")
            return []

    def filter_citations_with_doi(self, citations: List[Dict]) -> List[Dict]:
        """
        Filter citations to only those with valid DOIs.

        Args:
            citations: List of citation dicts

        Returns:
            Filtered list containing only citations with DOIs
        """
        return [c for c in citations if c.get("doi")]

    def rank_by_importance(
        self,
        citations: List[Dict],
        max_citations: int = 5
    ) -> List[Dict]:
        """
        Rank citations by importance heuristics.

        Args:
            citations: List of citation dicts
            max_citations: Maximum number to return

        Returns:
            Top N citations ranked by:
            1. Has DOI (required for further processing)
            2. Has recent year (prefer newer foundational work)
            3. Has complete metadata (title, authors)
        """
        def score_citation(c: Dict) -> float:
            score = 0.0

            # Must have DOI
            if not c.get("doi"):
                return -1.0

            # Prefer recent (weight year highly)
            if c.get("year"):
                # Normalize year to 0-1 range (assuming 1900-2030)
                year_score = (c["year"] - 1900) / 130.0
                score += year_score * 3.0

            # Prefer complete metadata
            if c.get("title"):
                score += 1.0
            if c.get("authors"):
                score += 1.0

            return score

        # Score and filter
        scored = [(score_citation(c), c) for c in citations]
        valid = [(s, c) for s, c in scored if s >= 0]  # Remove citations without DOI

        # Sort by score (descending) and take top N
        valid.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in valid[:max_citations]]
