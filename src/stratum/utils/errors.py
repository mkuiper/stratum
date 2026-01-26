"""Error handling and retry utilities."""
from typing import Callable, TypeVar, Optional
from functools import wraps
import time
from rich.console import Console

console = Console()

T = TypeVar('T')


class StratumError(Exception):
    """Base exception for Stratum errors."""
    pass


class PaperFetchError(StratumError):
    """Error fetching paper from external source."""
    pass


class PDFExtractionError(StratumError):
    """Error extracting text from PDF."""
    pass


class CitationParsingError(StratumError):
    """Error parsing citations with GROBID."""
    pass


class AnalysisError(StratumError):
    """Error during paper analysis (LLM call failed)."""
    pass


class ValidationError(StratumError):
    """Error validating output against schema."""
    pass


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator to retry a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries (seconds)
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry

    Example:
        @retry_with_backoff(max_retries=3, exceptions=(requests.RequestException,))
        def fetch_data():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        console.print(
                            f"[yellow]⚠️  Attempt {attempt + 1}/{max_retries} failed: {str(e)}[/yellow]"
                        )
                        console.print(f"[dim]Retrying in {delay:.1f}s...[/dim]")
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        console.print(
                            f"[red]❌ All {max_retries} retry attempts failed[/red]"
                        )

            raise last_exception

        return wrapper
    return decorator


def handle_error(error: Exception, context: str = "") -> None:
    """
    Handle error with user-friendly message.

    Args:
        error: The exception that occurred
        context: Additional context about what was being done
    """
    error_messages = {
        PaperFetchError: "Failed to fetch paper from external source",
        PDFExtractionError: "Failed to extract text from PDF",
        CitationParsingError: "Failed to parse citations (is GROBID running?)",
        AnalysisError: "Failed to analyze paper with LLM",
        ValidationError: "Failed to validate output against schema",
    }

    error_type = type(error)
    message = error_messages.get(error_type, "An unexpected error occurred")

    console.print(f"\n[bold red]❌ {message}[/bold red]")
    if context:
        console.print(f"[dim]Context: {context}[/dim]")
    console.print(f"[dim]Error: {str(error)}[/dim]\n")


def validate_doi(doi: str) -> bool:
    """
    Validate DOI format.

    Args:
        doi: DOI string to validate

    Returns:
        True if valid, False otherwise
    """
    import re
    # Basic DOI pattern: 10.xxxx/...
    pattern = r'^10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+$'
    return bool(re.match(pattern, doi))


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for all filesystems
    """
    import re
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    return filename


def check_dependencies() -> dict:
    """
    Check if required dependencies are available.

    Returns:
        Dict with dependency status
    """
    import requests
    from ..config.settings import settings

    status = {
        "grobid": False,
        "llm_api_key": False,
        "output_dir": False,
    }

    # Check GROBID
    try:
        response = requests.get(
            settings.GROBID_URL.replace("/api", "/isalive"),
            timeout=5
        )
        status["grobid"] = response.status_code == 200
    except Exception:
        pass

    # Check LLM API key
    api_key = settings.get_api_key()
    status["llm_api_key"] = api_key is not None and len(api_key) > 0

    # Check output directory is writable
    try:
        settings.ensure_directories()
        test_file = settings.OUTPUT_DIR / ".test"
        test_file.write_text("test")
        test_file.unlink()
        status["output_dir"] = True
    except Exception:
        pass

    return status


def print_dependency_status():
    """Print dependency status with colors."""
    status = check_dependencies()

    console.print("\n[bold]Dependency Check:[/bold]")

    for dep, available in status.items():
        icon = "✓" if available else "✗"
        color = "green" if available else "red"
        dep_name = {
            "grobid": "GROBID Service",
            "llm_api_key": "LLM API Key",
            "output_dir": "Output Directory"
        }.get(dep, dep)

        console.print(f"  [{color}]{icon}[/{color}] {dep_name}")

    if not all(status.values()):
        console.print("\n[yellow]⚠️  Some dependencies are not available[/yellow]")
        console.print("[dim]Run 'stratum doctor' for help[/dim]\n")
        return False

    console.print("\n[green]All dependencies available![/green]\n")
    return True
