"""Citation extraction tool using GROBID service."""
from pathlib import Path
from typing import List, Dict, Optional
import requests
from pydantic import Field
import xml.etree.ElementTree as ET

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
    timeout: int = Field(default=60, description="Request timeout in seconds")

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
        return citations

    def _parse_tei_xml(self, tei_xml: str) -> List[Dict[str, any]]:
        """
        Parse GROBID TEI-XML format to extract citation data.

        Args:
            tei_xml: TEI-XML string from GROBID

        Returns:
            List of parsed citations
        """
        try:
            # Try using grobid-tei-xml library if available
            from grobid_tei_xml import parse_document_xml
            doc = parse_document_xml(tei_xml)

            citations = []
            for ref in doc.references:
                citation = {
                    "title": ref.article_title or "",
                    "authors": [a.full_name for a in (ref.authors or [])],
                    "year": ref.year,
                    "doi": ref.doi,
                    "raw_reference": ref.unstructured or ""
                }
                citations.append(citation)

            return citations

        except ImportError:
            # Fallback: basic XML parsing if grobid-tei-xml not available
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
