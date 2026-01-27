"""CrewAI crew orchestration."""
from crewai import Crew, Process
from pathlib import Path
from typing import Dict, List, Optional
import json
import re

from .agents.librarian import create_librarian_agent
from .agents.analyst import create_analyst_agent
from .agents.archivist import create_archivist_agent
from .tasks.fetch_paper import create_fetch_paper_task
from .tasks.analyze_paper import create_analyze_paper_task
from .tasks.archive_paper import create_archive_paper_task
from .config.settings import settings
from .llm.provider import create_llm_for_crewai
from .models.knowledge_table import KnowledgeTable


class StratumCrew:
    """
    Main crew orchestration for Stratum.

    Coordinates three agents in sequential workflow:
    1. Librarian: Fetch paper and extract citations
    2. Analyst: Extract Knowledge Table (JSON)
    3. Archivist: Generate Obsidian markdown
    """

    def __init__(
        self,
        llm_model: Optional[str] = None,
        output_dir: Optional[Path] = None,
        verbose: bool = True,
        max_citations: int = 5
    ):
        """
        Initialize Stratum crew.

        Args:
            llm_model: LLM model string (defaults to settings.LLM_MODEL)
            output_dir: Output directory for markdown files
            verbose: Enable verbose logging
            max_citations: Maximum citations to extract per paper
        """
        # Ensure directories exist
        settings.ensure_directories()

        # Configure LLM
        if llm_model is None:
            llm_model = create_llm_for_crewai(settings)
        self.llm_model = llm_model

        # Set output directory
        self.output_dir = output_dir or settings.OUTPUT_DIR
        self.verbose = verbose
        self.max_citations = max_citations

        # Create agents
        self.librarian = create_librarian_agent(self.llm_model)
        self.analyst = create_analyst_agent(self.llm_model)
        self.archivist = create_archivist_agent(self.llm_model)

    def process_paper(
        self,
        doi: Optional[str] = None,
        pdf_path: Optional[str] = None,
        current_depth: int = 0,
        max_depth: int = 3,
        max_citations: int = 5,
        processed_dois: Optional[List[str]] = None
    ) -> Dict:
        """
        Process a single paper through the crew.

        Args:
            doi: DOI of paper to process
            pdf_path: Path to local PDF (alternative to DOI)
            current_depth: Current recursion depth
            max_depth: Maximum recursion depth
            max_citations: Maximum citations to extract
            processed_dois: List of already processed DOIs

        Returns:
            Dict containing:
                - knowledge_table: Parsed KnowledgeTable
                - markdown_path: Path to generated markdown
                - citations: List of citation DOIs for recursion

        Raises:
            ValueError: If neither DOI nor pdf_path provided
            Exception: If crew execution fails
        """
        if not doi and not pdf_path:
            raise ValueError("Must provide either doi or pdf_path")

        processed_dois = processed_dois or []

        # Task 1: Fetch paper, extract text, and find citations
        fetch_task = create_fetch_paper_task(
            agent=self.librarian,
            doi=doi,
            pdf_path=pdf_path,
            current_depth=current_depth,
            max_depth=max_depth,
            max_citations=max_citations,
            processed_dois=processed_dois
        )

        # Task 2: Analyze paper text to create Knowledge Table JSON
        # This task depends on fetch_task's output via context
        analyze_task = create_analyze_paper_task(
            agent=self.analyst,
            paper_text="{paper_text}",  # Placeholder - will be filled from fetch_task context
            title=doi or "Unknown",  # Placeholder
            authors=["Unknown"],  # Placeholder
            year=2024,  # Placeholder
            doi=doi or "unknown"
        )
        analyze_task.context = [fetch_task]  # Wire dependency

        # Task 3: Archive Knowledge Table as Obsidian markdown
        # This task depends on analyze_task's output via context
        archive_task = create_archive_paper_task(
            agent=self.archivist,
            knowledge_table_json={"kt_id": "placeholder"},  # Placeholder - will use analyze_task output
            output_dir=str(self.output_dir)
        )
        archive_task.context = [analyze_task]  # Wire dependency

        # Create crew with all three tasks in sequential order
        crew = Crew(
            agents=[self.librarian, self.analyst, self.archivist],
            tasks=[fetch_task, analyze_task, archive_task],
            process=Process.sequential,
            verbose=self.verbose
        )

        # Execute crew
        result = crew.kickoff()

        return self._parse_crew_result(result, doi=doi)

    def _parse_crew_result(self, result, doi: Optional[str] = None) -> Dict:
        """
        Parse crew execution result.

        Args:
            result: CrewAI execution result
            doi: DOI of the processed paper

        Returns:
            Parsed result dict with:
                - knowledge_table: KnowledgeTable dict or None
                - markdown_path: Path to generated markdown or None
                - citations: List of citation dicts for recursion
        """
        try:
            # CrewAI result might be a string, dict, or CrewOutput object
            result_str = str(result)

            # Try to extract markdown path from result
            markdown_path = None
            if "archived to" in result_str.lower():
                # Parse path from confirmation message
                import re
                path_match = re.search(r'(/[^\s]+\.md)', result_str)
                if path_match:
                    markdown_path = path_match.group(1)

            # Try to extract citations from result
            citations = []
            if hasattr(result, 'tasks_output') and result.tasks_output:
                # Get fetch task output (first task)
                fetch_output = str(result.tasks_output[0])

                # Parse citations from fetch output
                # Look for DOI patterns
                doi_pattern = r'10\.\d{4,}/[^\s,\])"]+'
                found_dois = re.findall(doi_pattern, fetch_output)

                # Create citation dicts
                for cite_doi in found_dois[:self.max_citations if hasattr(self, 'max_citations') else 5]:
                    if cite_doi != doi:  # Don't include self-citation
                        citations.append({
                            "doi": cite_doi,
                            "usage_type": "Foundational"  # Default assumption
                        })

            # Try to load knowledge table if markdown was created
            knowledge_table = None
            if markdown_path and Path(markdown_path).exists():
                # Read the markdown file to extract YAML frontmatter
                with open(markdown_path, 'r') as f:
                    content = f.read()
                    # Knowledge table would be reconstructable from markdown
                    # For now, we'll leave it as None
                    pass

            return {
                "knowledge_table": knowledge_table,
                "markdown_path": markdown_path,
                "citations": citations
            }

        except Exception as e:
            if self.verbose:
                print(f"Warning: Error parsing crew result: {e}")
            # Return empty result on parse failure
            return {
                "knowledge_table": None,
                "markdown_path": None,
                "citations": []
            }

    def create_knowledge_table(
        self,
        paper_text: str,
        title: str,
        authors: List[str],
        year: int,
        doi: str
    ) -> KnowledgeTable:
        """
        Create Knowledge Table from paper text using Analyst agent.

        Args:
            paper_text: Full text of the paper
            title: Paper title
            authors: List of authors
            year: Publication year
            doi: Paper DOI

        Returns:
            Validated KnowledgeTable instance

        Raises:
            ValidationError: If generated JSON doesn't match schema
        """
        # Create analyze task
        analyze_task = create_analyze_paper_task(
            agent=self.analyst,
            paper_text=paper_text,
            title=title,
            authors=authors,
            year=year,
            doi=doi
        )

        # Create single-task crew
        crew = Crew(
            agents=[self.analyst],
            tasks=[analyze_task],
            process=Process.sequential,
            verbose=self.verbose
        )

        # Execute
        result = crew.kickoff()

        # Parse JSON result
        try:
            if isinstance(result, str):
                kt_json = json.loads(result)
            else:
                kt_json = result

            # Validate with Pydantic
            kt = KnowledgeTable(**kt_json)
            return kt

        except json.JSONDecodeError as e:
            raise ValueError(f"Analyst output is not valid JSON: {e}")
        except Exception as e:
            raise ValueError(f"Failed to create Knowledge Table: {e}")

    def archive_knowledge_table(
        self,
        knowledge_table: KnowledgeTable
    ) -> str:
        """
        Archive Knowledge Table as Obsidian markdown.

        Args:
            knowledge_table: KnowledgeTable instance

        Returns:
            Path to created markdown file

        Raises:
            Exception: If archiving fails
        """
        # Convert to dict
        kt_json = knowledge_table.model_dump()

        # Create archive task
        archive_task = create_archive_paper_task(
            agent=self.archivist,
            knowledge_table_json=kt_json,
            output_dir=str(self.output_dir)
        )

        # Create single-task crew
        crew = Crew(
            agents=[self.archivist],
            tasks=[archive_task],
            process=Process.sequential,
            verbose=self.verbose
        )

        # Execute
        result = crew.kickoff()

        # Extract file path from result
        # TODO: Parse actual result
        return str(self.output_dir / "papers" / f"{knowledge_table.kt_id}.md")

    def __repr__(self) -> str:
        return f"StratumCrew(model={self.llm_model}, output_dir={self.output_dir})"
