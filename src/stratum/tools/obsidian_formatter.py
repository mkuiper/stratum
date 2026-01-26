"""Obsidian markdown formatter tool."""
from pathlib import Path
from typing import Dict, Optional
import yaml
from pydantic import Field

from .base import StratumBaseTool
from ..models.knowledge_table import KnowledgeTable


class ObsidianFormatterTool(StratumBaseTool):
    """
    Converts JSON Knowledge Tables to Obsidian markdown format.

    Generates:
    - YAML frontmatter with metadata
    - Wikilinks for citation network
    - Structured markdown sections
    """

    name: str = "Obsidian Formatter"
    description: str = (
        "Converts Knowledge Table JSON to Obsidian markdown with YAML frontmatter "
        "and wikilinks for citations. Optimized for graph visualization."
    )

    output_dir: Path = Field(
        default=Path("output/papers"),
        description="Directory to save markdown files"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _run(
        self,
        kt_json: Dict,
        output_path: Optional[str] = None
    ) -> str:
        """
        Convert KnowledgeTable to Obsidian markdown.

        Args:
            kt_json: Knowledge Table as dict (will be validated)
            output_path: Optional custom output path (otherwise auto-generated)

        Returns:
            Path to created markdown file

        Raises:
            ValidationError: If kt_json doesn't match KnowledgeTable schema
        """
        # Validate with Pydantic
        kt = KnowledgeTable(**kt_json)

        # Generate frontmatter
        frontmatter = self._generate_frontmatter(kt)

        # Generate markdown content
        markdown = self._generate_markdown(kt)

        # Combine
        full_content = f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---\n\n{markdown}"

        # Determine output path
        if output_path is None:
            output_path = self.output_dir / f"{kt.kt_id}.md"
        else:
            output_path = Path(output_path)

        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        output_path.write_text(full_content, encoding='utf-8')

        return str(output_path)

    def _generate_frontmatter(self, kt: KnowledgeTable) -> Dict:
        """
        Generate YAML frontmatter for Obsidian.

        Args:
            kt: KnowledgeTable instance

        Returns:
            Dict for YAML frontmatter
        """
        return {
            'kt_id': kt.kt_id,
            'title': kt.meta.title,
            'authors': kt.meta.authors,
            'year': kt.meta.year,
            'doi': kt.meta.doi,
            'tags': ['knowledge-table', 'scientific-paper', 'stratum'],
            'aliases': [kt.kt_id, kt.meta.title],
            'created': self._get_timestamp(),
        }

    def _generate_markdown(self, kt: KnowledgeTable) -> str:
        """
        Generate markdown content sections.

        Args:
            kt: KnowledgeTable instance

        Returns:
            Markdown string
        """
        sections = []

        # Title
        sections.append(f"# {kt.meta.title}\n")

        # Metadata
        sections.append(f"**Authors**: {', '.join(kt.meta.authors)}")
        sections.append(f"**Year**: {kt.meta.year}")
        sections.append(f"**DOI**: [{kt.meta.doi}](https://doi.org/{kt.meta.doi})")
        sections.append("")

        # Central Hypothesis
        sections.append("## Central Hypothesis\n")
        sections.append(kt.core_analysis['central_hypothesis'])
        sections.append("")

        # Methodology
        sections.append("## Methodology\n")
        sections.append(kt.core_analysis['methodology_summary'])
        sections.append("")

        # Significance
        sections.append("## Significance\n")
        sections.append(kt.core_analysis['significance'])
        sections.append("")

        # Key Points
        sections.append("## Key Points\n")
        for kp in kt.key_points:
            sections.append(f"### {kp.id}: {kp.content}\n")
            sections.append(f"- **Evidence**: {kp.evidence_anchor}")
            sections.append(f"- **Confidence**: {kp.confidence_score:.2f}")
            sections.append("")

        # Logic Chains
        sections.append("## Logic Chains\n")
        for lc in kt.logic_chains:
            sections.append(f"### {lc.name}\n")
            sections.append(f"**Argument Flow**: {lc.argument_flow}\n")
            sections.append(f"**Conclusion**: {lc.conclusion_derived}")
            sections.append("")

        # Citation Network
        if kt.citation_network:
            sections.append("## Citation Network\n")

            # Group by usage type
            foundational = [c for c in kt.citation_network if c.usage_type == "Foundational"]
            comparison = [c for c in kt.citation_network if c.usage_type == "Comparison"]
            refuting = [c for c in kt.citation_network if c.usage_type == "Refuting"]

            if foundational:
                sections.append("### Foundational Papers\n")
                for cite in foundational:
                    wikilink = self._create_wikilink(cite.target_paper_doi, cite.target_paper_title)
                    sections.append(f"- {wikilink}")
                    sections.append(f"  - {cite.notes}")
                sections.append("")

            if comparison:
                sections.append("### Comparison Papers\n")
                for cite in comparison:
                    wikilink = self._create_wikilink(cite.target_paper_doi, cite.target_paper_title)
                    sections.append(f"- {wikilink}")
                    sections.append(f"  - {cite.notes}")
                sections.append("")

            if refuting:
                sections.append("### Refuting Papers\n")
                for cite in refuting:
                    wikilink = self._create_wikilink(cite.target_paper_doi, cite.target_paper_title)
                    sections.append(f"- {wikilink}")
                    sections.append(f"  - {cite.notes}")
                sections.append("")

        # Footer
        sections.append("---")
        sections.append("*Generated by Stratum - Scientific Paper Analysis System*")

        return "\n".join(sections)

    def _create_wikilink(self, doi: str, title: str) -> str:
        """
        Create Obsidian wikilink for a citation.

        Uses DOI as the link target (will correspond to the KT_ID
        of the cited paper once it's processed).

        Args:
            doi: DOI of cited paper
            title: Title for display

        Returns:
            Wikilink string
        """
        # Convert DOI to likely KT_ID format (will be created when paper is processed)
        # For now, use DOI as the link target
        safe_doi = doi.replace('/', '_')

        return f"[[{safe_doi}|{title}]]"

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()


# Utility function for easy access
def kt_to_obsidian(kt_json: Dict, output_path: Optional[str] = None) -> str:
    """
    Convenience function to convert KnowledgeTable to Obsidian markdown.

    Args:
        kt_json: Knowledge Table as dict
        output_path: Optional output path

    Returns:
        Path to created file
    """
    tool = ObsidianFormatterTool()
    return tool._run(kt_json, output_path)
