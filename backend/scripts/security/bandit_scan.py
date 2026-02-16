"""
Bandit SAST Scanner

Runs Bandit security static analysis on Python code to identify
common security issues.
"""

import json
import subprocess
import sys
from pathlib import Path

import typer

app = typer.Typer(help="Bandit SAST security scanner")


@app.command()
def scan(
    path: Path = typer.Argument(
        Path("app"),
        help="Path to scan",
    ),
    severity: str = typer.Option(
        "medium",
        "--severity",
        "-s",
        help="Minimum severity level (low, medium, high)",
    ),
    confidence: str = typer.Option(
        "medium",
        "--confidence",
        "-c",
        help="Minimum confidence level (low, medium, high)",
    ),
    output_format: str = typer.Option(
        "screen",
        "--format",
        "-f",
        help="Output format (screen, json, csv, xml)",
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path",
    ),
    recursive: bool = typer.Option(
        True,
        "--recursive/--no-recursive",
        "-r/-R",
        help="Scan directories recursively",
    ),
    skip_tests: bool = typer.Option(
        True,
        "--skip-tests/--include-tests",
        help="Skip test files",
    ),
) -> None:
    """
    Run Bandit security scan on Python code.
    
    Args:
        path: Path to scan
        severity: Minimum severity level
        confidence: Minimum confidence level
        output_format: Output format
        output_file: Output file path
        recursive: Scan recursively
        skip_tests: Skip test files
    """
    typer.echo(f"Running Bandit scan on {path}...")
    
    cmd = [
        "bandit",
        "-lll" if severity == "high" else "-ll" if severity == "medium" else "-l",
        "-iii" if confidence == "high" else "-ii" if confidence == "medium" else "-i",
        "-f", output_format,
    ]
    
    if recursive:
        cmd.append("-r")
    
    if skip_tests:
        cmd.extend(["-x", "tests,test"])
    
    if output_file:
        cmd.extend(["-o", str(output_file)])
    
    cmd.append(str(path))
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        
        if result.stdout:
            typer.echo(result.stdout)
        
        if result.stderr:
            typer.echo(result.stderr, err=True)
        
        if result.returncode != 0:
            typer.echo("Security issues found!", err=True)
            sys.exit(1)
        else:
            typer.echo("No security issues found.")
            
    except FileNotFoundError:
        typer.echo(
            "Error: 'bandit' command not found. Install with: pip install bandit[toml]",
            err=True,
        )
        sys.exit(1)


@app.command()
def config(
    output_file: Path = typer.Option(
        Path(".bandit"),
        "--output",
        "-o",
        help="Output config file path",
    ),
) -> None:
    """
    Generate Bandit configuration file.
    
    Args:
        output_file: Path to save configuration
    """
    config_content = """[bandit]
exclude_dirs = tests,test,venv,.venv,__pycache__,.git
skips = B101,B311
"""
    
    output_file.write_text(config_content)
    typer.echo(f"Bandit configuration saved to {output_file}")


if __name__ == "__main__":
    app()
