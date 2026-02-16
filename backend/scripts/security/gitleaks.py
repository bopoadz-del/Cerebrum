"""
Gitleaks Pre-commit Hook

Scans code for secrets and credentials before commits.
"""

import subprocess
import sys
from pathlib import Path

import typer

app = typer.Typer(help="Gitleaks secret scanner")


@app.command()
def scan(
    path: Path = typer.Argument(
        Path("."),
        help="Path to scan",
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Gitleaks config file",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose output",
    ),
    redact: bool = typer.Option(
        True,
        "--redact/--no-redact",
        help="Redact secrets in output",
    ),
) -> None:
    """
    Run gitleaks scan on code.
    
    Args:
        path: Path to scan
        config_file: Gitleaks configuration file
        verbose: Verbose output
        redact: Redact secrets in output
    """
    typer.echo(f"Running gitleaks scan on {path}...")
    
    cmd = ["gitleaks", "detect", "-s", str(path)]
    
    if config_file:
        cmd.extend(["-c", str(config_file)])
    
    if verbose:
        cmd.append("-v")
    
    if redact:
        cmd.append("--redact")
    
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
            typer.echo("Secrets detected! Commit blocked.", err=True)
            sys.exit(1)
        else:
            typer.echo("No secrets detected.")
            
    except FileNotFoundError:
        typer.echo(
            "Error: 'gitleaks' command not found.",
            err=True,
        )
        typer.echo("Install from: https://github.com/gitleaks/gitleaks")
        sys.exit(1)


@app.command()
def install_hook(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing hook",
    ),
) -> None:
    """
    Install gitleaks as a pre-commit hook.
    
    Args:
        force: Overwrite existing hook
    """
    git_dir = Path(".git")
    hooks_dir = git_dir / "hooks"
    pre_commit = hooks_dir / "pre-commit"
    
    if not git_dir.exists():
        typer.echo("Error: Not a git repository", err=True)
        sys.exit(1)
    
    hooks_dir.mkdir(parents=True, exist_ok=True)
    
    if pre_commit.exists() and not force:
        typer.echo("Pre-commit hook already exists. Use --force to overwrite.")
        sys.exit(1)
    
    hook_content = """#!/bin/sh
# Gitleaks pre-commit hook

echo "Running gitleaks secret scan..."

gitleaks detect -v --redact

if [ $? -ne 0 ]; then
    echo "Secrets detected! Commit blocked."
    exit 1
fi

echo "No secrets detected."
exit 0
"""
    
    pre_commit.write_text(hook_content)
    pre_commit.chmod(0o755)
    
    typer.echo(f"Pre-commit hook installed at {pre_commit}")


@app.command()
def protect(
    repo_url: str = typer.Argument(
        ...,
        help="Repository URL to protect",
    ),
) -> None:
    """
    Enable gitleaks protection for a repository.
    
    Args:
        repo_url: Repository URL
    """
    typer.echo(f"Enabling gitleaks protection for {repo_url}...")
    
    # This would typically use the gitleaks API or GitHub Actions
    typer.echo("To enable gitleaks protection:")
    typer.echo("1. Add .github/workflows/gitleaks.yml to your repository")
    typer.echo("2. Configure gitleaks to run on pull requests")


if __name__ == "__main__":
    app()
