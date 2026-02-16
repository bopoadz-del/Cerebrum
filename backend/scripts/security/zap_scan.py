"""
OWASP ZAP Baseline Scan

Runs OWASP ZAP baseline scan against the application to identify
common security vulnerabilities.
"""

import subprocess
import sys
import time
from pathlib import Path

import typer

app = typer.Typer(help="OWASP ZAP security scanner")


@app.command()
def baseline(
    target: str = typer.Argument(
        ...,
        help="Target URL to scan",
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="ZAP configuration file",
    ),
    report_file: Path = typer.Option(
        Path("zap-report.html"),
        "--report",
        "-r",
        help="Report output file",
    ),
    timeout: int = typer.Option(
        600,
        "--timeout",
        "-t",
        help="Scan timeout in seconds",
    ),
    spider_minutes: int = typer.Option(
        1,
        "--spider",
        "-s",
        help="Spider scan duration in minutes",
    ),
) -> None:
    """
    Run OWASP ZAP baseline scan.
    
    Args:
        target: Target URL to scan
        config_file: ZAP configuration file
        report_file: Report output file
        timeout: Scan timeout
        spider_minutes: Spider scan duration
    """
    typer.echo(f"Running OWASP ZAP baseline scan on {target}...")
    
    # Check if ZAP is running
    check_cmd = ["docker", "ps", "--filter", "name=zap", "--format", "{{.Names}}"]
    result = subprocess.run(check_cmd, capture_output=True, text=True)
    
    if "zap" not in result.stdout:
        typer.echo("Starting OWASP ZAP container...")
        subprocess.run([
            "docker", "run", "-d",
            "--name", "zap",
            "-p", "8080:8080",
            "-v", f"{Path.cwd()}:/zap/wrk",
            "ghcr.io/zaproxy/zaproxy:stable",
            "zap.sh", "-daemon", "-host", "0.0.0.0", "-port", "8080",
            "-config", "api.disablekey=true",
        ])
        
        # Wait for ZAP to start
        typer.echo("Waiting for ZAP to start...")
        time.sleep(30)
    
    # Run baseline scan
    cmd = [
        "docker", "exec", "zap",
        "zap-baseline.py",
        "-t", target,
        "-r", str(report_file),
        "-m", str(spider_minutes),
    ]
    
    if config_file:
        cmd.extend(["-c", str(config_file)])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        
        typer.echo(result.stdout)
        
        if result.stderr:
            typer.echo(result.stderr, err=True)
        
        # Exit codes: 0=pass, 1=warn, 2=fail
        if result.returncode == 2:
            typer.echo("ZAP scan failed - vulnerabilities found!", err=True)
            sys.exit(1)
        elif result.returncode == 1:
            typer.echo("ZAP scan warnings - review recommended")
        else:
            typer.echo("ZAP scan passed!")
            
    except subprocess.TimeoutExpired:
        typer.echo("ZAP scan timed out!", err=True)
        sys.exit(1)
    except FileNotFoundError:
        typer.echo(
            "Error: Docker not found. Please install Docker.",
            err=True,
        )
        sys.exit(1)


@app.command()
def full(
    target: str = typer.Argument(
        ...,
        help="Target URL to scan",
    ),
    report_file: Path = typer.Option(
        Path("zap-full-report.html"),
        "--report",
        "-r",
        help="Report output file",
    ),
) -> None:
    """
    Run full OWASP ZAP scan.
    
    Args:
        target: Target URL to scan
        report_file: Report output file
    """
    typer.echo(f"Running full OWASP ZAP scan on {target}...")
    
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{Path.cwd()}:/zap/wrk",
        "ghcr.io/zaproxy/zaproxy:stable",
        "zap-full-scan.py",
        "-t", target,
        "-r", str(report_file),
    ]
    
    try:
        result = subprocess.run(cmd)
        
        if result.returncode != 0:
            typer.echo("ZAP scan found issues!", err=True)
            sys.exit(1)
        else:
            typer.echo("ZAP scan completed!")
            
    except FileNotFoundError:
        typer.echo(
            "Error: Docker not found. Please install Docker.",
            err=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    app()
