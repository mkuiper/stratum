"""Stratum CLI - Command-line interface for recursive paper analysis."""
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
import sys

from .flow import StratumFlow, analyze_paper_recursive
from .config.settings import settings
from .utils.recursion import RecursionManager
from .utils.errors import print_dependency_status, validate_doi, handle_error

app = typer.Typer(
    name="stratum",
    help="CrewAI-based multi-agent system for recursive forensic audits of scientific papers.",
    add_completion=False,
)
console = Console()


@app.command()
def analyze(
    doi: str = typer.Argument(..., help="DOI of the paper to analyze"),
    max_depth: int = typer.Option(
        3,
        "--max-depth",
        "-d",
        help="Maximum recursion depth for citation analysis"
    ),
    max_citations: int = typer.Option(
        5,
        "--max-citations",
        "-c",
        help="Maximum foundational citations to extract per paper"
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Output directory for markdown files (default: ./output)"
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="LLM model to use (default: from .env)"
    ),
    verbose: bool = typer.Option(
        True,
        "--verbose/--quiet",
        "-v/-q",
        help="Enable/disable verbose logging"
    ),
):
    """
    Analyze a scientific paper recursively.

    Fetches the paper by DOI, extracts Knowledge Table following the Whitesides
    Standard, generates Obsidian markdown, and recursively analyzes foundational
    citations up to MAX_DEPTH.

    Example:
        stratum analyze 10.1000/example.2024 --max-depth 2 --max-citations 3
    """
    console.print("\n[bold cyan]🔬 Stratum - Scientific Paper Analysis[/bold cyan]")
    console.print(f"[dim]Analyzing: {doi}[/dim]\n")

    # Validate DOI format
    if not validate_doi(doi):
        console.print(f"[red]❌ Invalid DOI format: {doi}[/red]")
        console.print("[dim]DOI should be in format: 10.xxxx/...[/dim]\n")
        sys.exit(1)

    # Display configuration
    config_table = Table(show_header=False, box=None)
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="yellow")
    config_table.add_row("DOI", doi)
    config_table.add_row("Max Depth", str(max_depth))
    config_table.add_row("Max Citations", str(max_citations))
    config_table.add_row("Model", model or settings.LLM_MODEL)
    config_table.add_row("Output", str(output_dir or settings.OUTPUT_DIR))
    console.print(config_table)
    console.print()

    try:
        # Run analysis
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Starting analysis...", total=None)

            # Create flow
            flow = StratumFlow(
                max_depth=max_depth,
                max_citations=max_citations,
                output_dir=output_dir,
                llm_model=model,
                verbose=verbose
            )

            progress.update(task, description="Processing papers...")

            # Run analysis
            results = flow.kickoff(seed_doi=doi)

        # Display results
        console.print("\n[bold green]✨ Analysis Complete![/bold green]\n")

        results_data = flow.get_results()
        stats = results_data.get("stats", {})

        # Results table
        results_table = Table(show_header=False, box=None)
        results_table.add_column("Metric", style="cyan")
        results_table.add_column("Value", style="green")
        results_table.add_row("Papers Processed", str(stats.get("total_processed", 0)))
        results_table.add_row("Output Directory", str(flow.crew.output_dir))

        if "papers_by_depth" in stats:
            for depth, count in stats["papers_by_depth"].items():
                results_table.add_row(f"  Depth {depth}", str(count))

        console.print(results_table)
        console.print()

        # View command
        console.print("[dim]View results in Obsidian or run:[/dim]")
        console.print(f"[dim]  stratum status[/dim]\n")

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Analysis interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[bold red]❌ Error:[/bold red] {str(e)}")
        if verbose:
            console.print_exception()
        sys.exit(1)


@app.command()
def status(
    state_file: Optional[Path] = typer.Option(
        None,
        "--state-file",
        "-s",
        help="Path to state file (default: data/state/recursion_state.json)"
    ),
):
    """
    Show analysis status and statistics.

    Displays:
    - Total papers processed
    - Papers by depth level
    - List of processed DOIs
    """
    console.print("\n[bold cyan]📊 Analysis Status[/bold cyan]\n")

    # Load state
    if state_file is None:
        state_file = settings.CACHE_DIR / "state" / "recursion_state.json"

    if not state_file.exists():
        console.print("[yellow]No analysis state found. Run 'stratum analyze' first.[/yellow]\n")
        return

    try:
        manager = RecursionManager(state_file, max_depth=3)
        stats = manager.get_stats()

        # Stats table
        stats_table = Table(show_header=False, box=None)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="yellow")
        stats_table.add_row("Total Papers Processed", str(stats["total_processed"]))
        stats_table.add_row("Maximum Depth", str(stats["max_depth"]))

        console.print(stats_table)
        console.print()

        # Papers by depth
        if stats["papers_by_depth"]:
            console.print("[bold]Papers by Depth:[/bold]")
            depth_table = Table(show_header=True)
            depth_table.add_column("Depth", style="cyan")
            depth_table.add_column("Count", style="yellow")

            for depth in range(stats["max_depth"]):
                count = stats["papers_by_depth"].get(depth, 0)
                depth_table.add_row(str(depth), str(count))

            console.print(depth_table)
            console.print()

        # Processed DOIs
        dois = manager.get_processed_dois()
        if dois:
            console.print(f"[bold]Processed DOIs[/bold] ({len(dois)} total):")
            for i, doi in enumerate(dois[:10], 1):
                depth = manager.state.depth_map.get(doi, "?")
                console.print(f"  {i}. [dim]depth {depth}:[/dim] {doi}")

            if len(dois) > 10:
                console.print(f"  [dim]... and {len(dois) - 10} more[/dim]")
            console.print()

    except Exception as e:
        console.print(f"[red]Error loading status: {e}[/red]\n")
        sys.exit(1)


@app.command()
def reset(
    state_file: Optional[Path] = typer.Option(
        None,
        "--state-file",
        "-s",
        help="Path to state file (default: data/state/recursion_state.json)"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt"
    ),
):
    """
    Reset analysis state (clear processed papers).

    Warning: This will allow reprocessing of previously analyzed papers.
    """
    # Load state
    if state_file is None:
        state_file = settings.CACHE_DIR / "state" / "recursion_state.json"

    if not state_file.exists():
        console.print("[yellow]No state file found. Nothing to reset.[/yellow]\n")
        return

    # Confirmation
    if not force:
        manager = RecursionManager(state_file, max_depth=3)
        count = len(manager.get_processed_dois())

        console.print(f"\n[yellow]⚠️  This will reset the analysis state.[/yellow]")
        console.print(f"[dim]Currently tracking {count} processed papers.[/dim]\n")

        confirm = typer.confirm("Are you sure you want to reset?")
        if not confirm:
            console.print("[dim]Reset cancelled.[/dim]\n")
            return

    try:
        manager = RecursionManager(state_file, max_depth=3)
        manager.reset()
        console.print("\n[green]✓ State reset successfully[/green]\n")

    except Exception as e:
        console.print(f"\n[red]Error resetting state: {e}[/red]\n")
        sys.exit(1)


@app.command()
def doctor():
    """
    Check system dependencies and configuration.

    Verifies:
    - GROBID service is running
    - LLM API key is configured
    - Output directory is writable
    """
    console.print("\n[bold cyan]🏥 System Health Check[/bold cyan]\n")

    all_ok = print_dependency_status()

    if not all_ok:
        console.print("[bold]Troubleshooting:[/bold]")
        console.print("  • GROBID: Run 'docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.0'")
        console.print("  • API Key: Set LLM_API_KEY in .env file")
        console.print("  • Output: Check directory permissions\n")
        sys.exit(1)


@app.command()
def version():
    """Show version information."""
    console.print("\n[bold cyan]Stratum[/bold cyan] v0.1.0")
    console.print("[dim]Multi-agent system for recursive paper analysis[/dim]")
    console.print("[dim]Powered by CrewAI, LiteLLM, and GROBID[/dim]\n")


@app.callback()
def main_callback():
    """
    Stratum - Recursive forensic audits of scientific papers.

    Extract hypothesis-driven Knowledge Tables following the Whitesides Standard.
    Build citation networks. Generate Obsidian graph visualizations.
    """
    pass


if __name__ == "__main__":
    app()
