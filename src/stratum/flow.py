"""CrewAI Flow for recursive paper analysis."""
from crewai.flow.flow import Flow, listen, start
from pydantic import BaseModel, Field
from typing import List, Tuple, Optional, Dict
from pathlib import Path
import json

from .crew import StratumCrew
from .utils.recursion import RecursionManager
from .models.knowledge_table import KnowledgeTable
from .config.settings import settings


class PaperToProcess(BaseModel):
    """A paper queued for processing."""
    doi: str
    depth: int
    source_paper: Optional[str] = None  # DOI of paper that cited this one


class StratumFlowState(BaseModel):
    """State for the recursive paper analysis flow."""

    # Current paper being processed
    current_doi: Optional[str] = None
    current_depth: int = 0

    # Queue of papers to process
    papers_to_process: List[PaperToProcess] = Field(default_factory=list)

    # Completed papers
    completed_papers: List[str] = Field(default_factory=list)

    # Configuration
    max_depth: int = 3
    max_citations: int = 5

    # Results
    knowledge_tables: Dict[str, dict] = Field(default_factory=dict)  # DOI -> KnowledgeTable JSON


class StratumFlow(Flow):
    """
    Recursive flow for processing papers and their citations.

    Workflow:
    1. Start with seed paper (depth 0)
    2. Process paper: Librarian → Analyst → Archivist
    3. Extract "Foundational" citations
    4. Enqueue citations for processing at depth+1
    5. Repeat until queue empty or max_depth reached
    """

    def __init__(
        self,
        max_depth: int = 3,
        max_citations: int = 5,
        state_file: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        llm_model: Optional[str] = None,
        verbose: bool = True
    ):
        """
        Initialize Stratum Flow.

        Args:
            max_depth: Maximum recursion depth
            max_citations: Maximum citations per paper
            state_file: Path to state file for persistence
            output_dir: Output directory for markdown files
            llm_model: LLM model to use
            verbose: Enable verbose logging
        """
        super().__init__()

        self.max_depth = max_depth
        self.max_citations = max_citations
        self.verbose = verbose

        # Initialize crew
        self.crew = StratumCrew(
            llm_model=llm_model,
            output_dir=output_dir,
            verbose=verbose,
            max_citations=max_citations
        )

        # Initialize recursion manager
        if state_file is None:
            state_file = settings.CACHE_DIR / "state" / "recursion_state.json"
        self.recursion_manager = RecursionManager(
            state_file=state_file,
            max_depth=max_depth
        )

    @start()
    def start_analysis(self, seed_doi: str):
        """
        Start analysis with a seed paper.

        Args:
            seed_doi: DOI of the seed paper to analyze

        Returns:
            Updated state
        """
        if self.verbose:
            print(f"\n🌱 Starting recursive analysis of: {seed_doi}")
            print(f"   Max depth: {self.max_depth}, Max citations: {self.max_citations}\n")

        # Initialize state
        self.state = StratumFlowState(
            current_doi=seed_doi,
            current_depth=0,
            max_depth=self.max_depth,
            max_citations=self.max_citations
        )

        # Process the seed paper
        return self.process_paper()

    @listen(start_analysis)
    def process_paper(self):
        """
        Process the current paper.

        Returns:
            Updated state or triggers next paper
        """
        doi = self.state.current_doi
        depth = self.state.current_depth

        if self.verbose:
            print(f"\n📄 Processing paper at depth {depth}: {doi}")

        # Check if should process
        if not self.recursion_manager.should_process_paper(doi, depth):
            if self.verbose:
                print(f"   ⏭️  Skipping (already processed or max depth reached)")
            return self.process_next()

        try:
            # Run crew to process paper
            # NOTE: This is a simplified version - in production we'd need to:
            # 1. Fetch the paper
            # 2. Extract text
            # 3. Run Analyst to get KnowledgeTable
            # 4. Run Archivist to create markdown
            # 5. Extract citations

            # For now, we'll use the crew's individual methods
            result = self.crew.process_paper(
                doi=doi,
                current_depth=depth,
                max_depth=self.max_depth,
                max_citations=self.max_citations,
                processed_dois=self.recursion_manager.get_processed_dois()
            )

            # Mark as processed
            self.recursion_manager.mark_processed(doi, depth)
            self.state.completed_papers.append(doi)

            if self.verbose:
                print(f"   ✅ Completed: {doi}")

            # Extract citations for recursion
            if depth < self.max_depth - 1:
                citations = self._extract_foundational_citations(result)

                if self.verbose and citations:
                    print(f"   📚 Found {len(citations)} foundational citations to process")

                # Enqueue citations
                for cite_doi in citations:
                    if self.recursion_manager.should_process_paper(cite_doi, depth + 1):
                        self.state.papers_to_process.append(
                            PaperToProcess(
                                doi=cite_doi,
                                depth=depth + 1,
                                source_paper=doi
                            )
                        )

            # Store result
            if result.get("knowledge_table"):
                self.state.knowledge_tables[doi] = result["knowledge_table"]

        except Exception as e:
            print(f"   ❌ Error processing {doi}: {e}")
            # Continue with next paper despite error

        # Process next paper
        return self.process_next()

    @listen(process_paper)
    def process_next(self):
        """
        Process the next paper in the queue.

        Returns:
            Updated state or completes flow
        """
        if self.state.papers_to_process:
            # Get next paper
            next_paper = self.state.papers_to_process.pop(0)
            self.state.current_doi = next_paper.doi
            self.state.current_depth = next_paper.depth

            if self.verbose:
                print(f"\n⏭️  Queue size: {len(self.state.papers_to_process)} remaining")

            # Process it
            return self.process_paper()
        else:
            # No more papers - flow complete
            return self.complete_flow()

    def complete_flow(self):
        """
        Complete the flow and return summary.

        Returns:
            Summary dict
        """
        if self.verbose:
            print(f"\n✨ Analysis complete!")
            print(f"   Papers processed: {len(self.state.completed_papers)}")
            print(f"   Output directory: {self.crew.output_dir}")

        # Get stats
        stats = self.recursion_manager.get_stats()

        return {
            "completed_papers": self.state.completed_papers,
            "total_processed": len(self.state.completed_papers),
            "stats": stats,
            "output_dir": str(self.crew.output_dir)
        }

    def _extract_foundational_citations(self, crew_result: dict) -> List[str]:
        """
        Extract DOIs of foundational citations from crew result.

        Args:
            crew_result: Result from crew.process_paper()

        Returns:
            List of DOIs to process recursively
        """
        citations = crew_result.get("citations", [])

        # Filter for foundational citations only
        foundational = [
            cite for cite in citations
            if isinstance(cite, dict) and cite.get("usage_type") == "Foundational"
        ]

        # Extract DOIs
        dois = [cite.get("doi") for cite in foundational if cite.get("doi")]

        # Limit to max_citations
        return dois[:self.max_citations]

    def get_state(self) -> StratumFlowState:
        """Get current flow state."""
        return self.state

    def get_results(self) -> dict:
        """
        Get all results from the flow.

        Returns:
            Dict with completed papers and knowledge tables
        """
        return {
            "completed_papers": self.state.completed_papers,
            "knowledge_tables": self.state.knowledge_tables,
            "stats": self.recursion_manager.get_stats()
        }


def analyze_paper_recursive(
    seed_doi: str,
    max_depth: int = 3,
    max_citations: int = 5,
    verbose: bool = True
) -> dict:
    """
    Convenience function to analyze a paper recursively.

    Args:
        seed_doi: DOI of the seed paper
        max_depth: Maximum recursion depth
        max_citations: Maximum citations per paper
        verbose: Enable verbose logging

    Returns:
        Results dict with completed papers and stats
    """
    flow = StratumFlow(
        max_depth=max_depth,
        max_citations=max_citations,
        verbose=verbose
    )

    result = flow.kickoff(seed_doi=seed_doi)

    return flow.get_results()
