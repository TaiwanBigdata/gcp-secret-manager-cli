from rich.console import Console
from rich.table import Table
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional
from google.cloud import secretmanager

console = Console()


def create_progress() -> Progress:
    """Create a progress indicator with bar"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    )


def create_spinner_progress() -> Progress:
    """Create a simple spinner progress indicator"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    )


def show_secrets_table(
    secrets: List[secretmanager.Secret], timezone: str = "UTC"
) -> None:
    """
    Display secrets list in a table

    Args:
        secrets (List[secretmanager.Secret]): List of secrets
        timezone (str, optional): Timezone name
    """
    table = Table(title="Secrets List")
    table.add_column("Secret Name", justify="left", style="cyan")
    table.add_column(f"Created At ({timezone})", justify="left", style="green")

    for secret in secrets:
        # Extract secret name from full path
        secret_name = secret.name.split("/")[-1]

        # Handle creation time
        create_time = secret.create_time.replace(tzinfo=ZoneInfo("UTC"))
        local_time = create_time.astimezone(ZoneInfo(timezone))
        formatted_time = local_time.strftime("%Y-%m-%d %H:%M:%S")

        table.add_row(secret_name, formatted_time)

    console.print(table)


def show_operation_table(
    results: List[Dict[str, str]], title: str = "Operation Results"
) -> None:
    """Display operation results table"""
    table = Table(title=title)
    table.add_column("Secret Name", justify="right", style="cyan")
    table.add_column("Status", justify="left", style="green")

    for result in results:
        table.add_row(result["name"], result["status"])

    console.print(table)


def show_summary(summary: Dict[str, int]) -> None:
    """Display operation summary"""
    console.print("\nSummary:")
    for key, value in summary.items():
        console.print(f"{key}: {value}")


def confirm(message: str) -> bool:
    """Display confirmation prompt"""
    return console.input(f"\n{message} (y/N) ").lower() == "y"


def print_error(message: str) -> None:
    """Display error message"""
    console.print(f"[red]Error: {message}[/red]")


def print_warning(message: str) -> None:
    """Display warning message"""
    console.print(f"[yellow]Warning: {message}[/yellow]")
