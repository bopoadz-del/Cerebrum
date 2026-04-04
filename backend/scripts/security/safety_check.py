"""
Safety Check Script

Runs safety check on Python dependencies to identify known
security vulnerabilities.
"""

import subprocess
import sys
from pathlib import Path

import typer

app = typer.Typer(help="Security vulnerability scanner")


@app.command()
def check(
    requirements_file: Path = typer.Option(
        Path("requirements.txt"),
        "--requirements",
        "-r",
        help="Path to requirements file",
    ),
    full_report: bool = typer.Option(
        False,
        "--full-report",
        "-f",
        help="Show full report",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output as JSON",
    ),
    ignore_ids: str = typer.Option(
        "",
        "--ignore",
        "-i",
        help="Comma-separated list of vulnerability IDs to ignore",
    ),
) -> None:
    """
    Run safety check on dependencies.
    
    Args:
        requirements_file: Path to requirements.txt
        full_report: Show full vulnerability details
        json_output: Output results as JSON
        ignore_ids: Vulnerability IDs to ignore
    """
    typer.echo(f"Running safety check on {requirements_file}...")
    
    cmd = ["safety", "check"]
    
    if requirements_file.exists():
        cmd.extend(["--file", str(requirements_file)])
    
    if full_report:
        cmd.append("--full-report")
    
    if json_output:
        cmd.append("--json")
    
    if ignore_ids:
        for vid in ignore_ids.split(","):
            cmd.extend(["--ignore", vid.strip()])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        
        if result.stdout:
            typer.echo(result.stdout)
        
        if result.returncode != 0:
            typer.echo("Security vulnerabilities found!", err=True)
            sys.exit(1)
        else:
            typer.echo("No known security vulnerabilities found.")
            
    except FileNotFoundError:
        typer.echo(
            "Error: 'safety' command not found. Install with: pip install safety",
            err=True,
        )
        sys.exit(1)


@app.command()
def audit(
    output_file: Path = typer.Option(
        Path("security-audit.json"),
        "--output",
        "-o",
        help="Output file for audit results",
    ),
) -> None:
    """
    Run full security audit and save results.
    
    Args:
        output_file: Path to save audit results
    """
    typer.echo("Running full security audit...")
    
    try:
        result = subprocess.run(
            ["safety", "check", "--json", "--full-report"],
            capture_output=True,
            text=True,
        )
        
        output_file.write_text(result.stdout)
        typer.echo(f"Audit results saved to {output_file}")
        
        if result.returncode != 0:
            typer.echo("Security vulnerabilities found!", err=True)
            sys.exit(1)
            
    except FileNotFoundError:
        typer.echo(
            "Error: 'safety' command not found. Install with: pip install safety",
            err=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    app()
