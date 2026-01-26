"""CrewAI crew orchestration."""
from crewai import Crew, Process
from pathlib import Path
from typing import Dict, List, Optional
import json

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
        verbose: bool = True
    ):
        """
        Initialize Stratum crew.

        Args:
            llm_model: LLM model string (defaults to settings.LLM_MODEL)
            output_dir: Output directory for markdown files
            verbose: Enable verbose logging
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

        # Create tasks
        fetch_task = create_fetch_paper_task(
            agent=self.librarian,
            doi=doi,
            pdf_path=pdf_path,
            current_depth=current_depth,
            max_depth=max_depth,
            max_citations=max_citations,
            processed_dois=processed_dois
        )

        # Placeholder for analyze task (will be created after fetch completes)
        # For now, we'll create a crew with just the fetch task
        # In a real implementation, we'd need the fetch results to create analyze task

        # Create crew with sequential process
        crew = Crew(
            agents=[self.librarian, self.analyst, self.archivist],
            tasks=[fetch_task],  # More tasks will be added dynamically
            process=Process.sequential,
            verbose=self.verbose
        )

        # Execute crew
        result = crew.kickoff()

        return self._parse_crew_result(result)

    def _parse_crew_result(self, result) -> Dict:
        """
        Parse crew execution result.

        Args:
            result: CrewAI execution result

        Returns:
            Parsed result dict
        """
        # TODO: Parse actual crew result
        # For now, return a placeholder structure
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
