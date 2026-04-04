"""
Secrets Detection - git-secrets, truffleHog Integration
Prevents accidental commit of secrets and credentials.
"""
import re
import json
import subprocess
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import hashlib
import logging

logger = logging.getLogger(__name__)


class SecretType(str, Enum):
    """Types of secrets that can be detected."""
    AWS_ACCESS_KEY = "aws_access_key"
    AWS_SECRET_KEY = "aws_secret_key"
    AZURE_KEY = "azure_key"
    GCP_KEY = "gcp_key"
    PRIVATE_KEY = "private_key"
    API_KEY = "api_key"
    DATABASE_URL = "database_url"
    PASSWORD = "password"
    TOKEN = "token"
    JWT = "jwt"
    SLACK_TOKEN = "slack_token"
    GITHUB_TOKEN = "github_token"
    GENERIC_SECRET = "generic_secret"


@dataclass
class SecretFinding:
    """Represents a detected secret."""
    secret_type: SecretType
    file_path: str
    line_number: int
    column_start: int
    column_end: int
    matched_text: str
    confidence: str  # 'high', 'medium', 'low'
    rule_id: str
    remediation: str
    
    def hash(self) -> str:
        """Generate hash for deduplication."""
        data = f"{self.file_path}:{self.line_number}:{self.matched_text}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


class SecretPattern:
    """Pattern for detecting secrets."""
    
    def __init__(self, secret_type: SecretType, pattern: str, 
                 confidence: str = 'high', remediation: str = ""):
        self.secret_type = secret_type
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.confidence = confidence
        self.remediation = remediation
    
    def search(self, content: str, file_path: str) -> List[SecretFinding]:
        """Search for secrets in content."""
        findings = []
        for match in self.pattern.finditer(content):
            # Calculate line number
            line_num = content[:match.start()].count('\n') + 1
            line_start = content.rfind('\n', 0, match.start()) + 1
            
            finding = SecretFinding(
                secret_type=self.secret_type,
                file_path=file_path,
                line_number=line_num,
                column_start=match.start() - line_start,
                column_end=match.end() - line_start,
                matched_text=match.group()[:50] + "..." if len(match.group()) > 50 else match.group(),
                confidence=self.confidence,
                rule_id=f"{self.secret_type.value}_001",
                remediation=self.remediation
            )
            findings.append(finding)
        
        return findings


class SecretsDetector:
    """Detects secrets in code and configuration files."""
    
    # Built-in secret patterns
    PATTERNS = [
        # AWS
        SecretPattern(
            SecretType.AWS_ACCESS_KEY,
            r'AKIA[0-9A-Z]{16}',
            'high',
            "Remove AWS access key and use IAM roles or environment variables"
        ),
        SecretPattern(
            SecretType.AWS_SECRET_KEY,
            r'[0-9a-zA-Z/+]{40}',
            'medium',
            "Potential AWS secret key - verify and remove if confirmed"
        ),
        
        # Azure
        SecretPattern(
            SecretType.AZURE_KEY,
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            'medium',
            "Potential Azure key - verify and use Azure Key Vault"
        ),
        
        # GCP
        SecretPattern(
            SecretType.GCP_KEY,
            r'AIza[0-9A-Za-z_-]{35}',
            'high',
            "Remove GCP API key and use service accounts"
        ),
        
        # Private Keys
        SecretPattern(
            SecretType.PRIVATE_KEY,
            r'-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----',
            'high',
            "Remove private key and use secure key management"
        ),
        
        # Generic API Keys
        SecretPattern(
            SecretType.API_KEY,
            r'(?:api[_-]?key|apikey)[\s]*[=:][\s]*["\']?[a-zA-Z0-9_\-]{16,}["\']?',
            'medium',
            "Move API key to environment variable or secret manager"
        ),
        
        # Database URLs
        SecretPattern(
            SecretType.DATABASE_URL,
            r'(?:postgres|mysql|mongodb)://[^:]+:[^@]+@[^/]+',
            'high',
            "Remove database credentials from URL, use connection string from environment"
        ),
        
        # Passwords
        SecretPattern(
            SecretType.PASSWORD,
            r'(?:password|passwd|pwd)[\s]*[=:][\s]*["\'][^"\']{8,}["\']',
            'high',
            "Remove hardcoded password, use environment variable or secret manager"
        ),
        
        # Tokens
        SecretPattern(
            SecretType.TOKEN,
            r'(?:token|auth_token)[\s]*[=:][\s]*["\']?[a-zA-Z0-9_\-]{20,}["\']?',
            'medium',
            "Move token to environment variable or secret manager"
        ),
        
        # JWT
        SecretPattern(
            SecretType.JWT,
            r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*',
            'high',
            "Remove JWT from code, obtain dynamically"
        ),
        
        # Slack
        SecretPattern(
            SecretType.SLACK_TOKEN,
            r'xox[baprs]-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*',
            'high',
            "Remove Slack token and use OAuth"
        ),
        
        # GitHub
        SecretPattern(
            SecretType.GITHUB_TOKEN,
            r'gh[pousr]_[A-Za-z0-9_]{36,}',
            'high',
            "Remove GitHub token and use GitHub Apps or environment variable"
        ),
    ]
    
    # Files to skip
    SKIP_PATHS = [
        r'\.git/',
        r'node_modules/',
        r'__pycache__/',
        r'\.venv/',
        r'venv/',
        r'\.pytest_cache/',
        r'\.mypy_cache/',
        r'dist/',
        r'build/',
        r'\.idea/',
        r'\.vscode/',
        r'\.coverage',
        r'.*\.min\.js$',
        r'.*\.lock$',
    ]
    
    # Extensions to scan
    SCAN_EXTENSIONS = [
        '.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.yaml', '.yml',
        '.env', '.sh', '.bash', '.zsh', '.ps1', '.cfg', '.conf',
        '.ini', '.toml', '.xml', '.sql', '.md', '.txt', '.rst'
    ]
    
    def __init__(self, custom_patterns: Optional[List[SecretPattern]] = None):
        self.patterns = self.PATTERNS + (custom_patterns or [])
        self.skip_patterns = [re.compile(p) for p in self.SKIP_PATHS]
    
    def scan_file(self, file_path: str) -> List[SecretFinding]:
        """Scan a single file for secrets."""
        findings = []
        
        # Check if file should be skipped
        if self._should_skip(file_path):
            return findings
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            for pattern in self.patterns:
                findings.extend(pattern.search(content, file_path))
        
        except Exception as e:
            logger.warning(f"Could not scan {file_path}: {e}")
        
        return findings
    
    def scan_directory(self, directory: str, recursive: bool = True) -> List[SecretFinding]:
        """Scan a directory for secrets."""
        findings = []
        path = Path(directory)
        
        if recursive:
            files = path.rglob('*')
        else:
            files = path.iterdir()
        
        for file_path in files:
            if file_path.is_file():
                findings.extend(self.scan_file(str(file_path)))
        
        return findings
    
    def scan_string(self, content: str, source: str = "<string>") -> List[SecretFinding]:
        """Scan a string for secrets."""
        findings = []
        
        for pattern in self.patterns:
            findings.extend(pattern.search(content, source))
        
        return findings
    
    def _should_skip(self, file_path: str) -> bool:
        """Check if file should be skipped."""
        # Check skip patterns
        for pattern in self.skip_patterns:
            if pattern.search(file_path):
                return True
        
        # Check extension
        if not any(file_path.endswith(ext) for ext in self.SCAN_EXTENSIONS):
            return True
        
        return False
    
    def generate_report(self, findings: List[SecretFinding]) -> Dict[str, Any]:
        """Generate scan report."""
        by_type = {}
        by_file = {}
        
        for finding in findings:
            # Group by type
            st = finding.secret_type.value
            if st not in by_type:
                by_type[st] = []
            by_type[st].append(finding)
            
            # Group by file
            if finding.file_path not in by_file:
                by_file[finding.file_path] = []
            by_file[finding.file_path].append(finding)
        
        return {
            'total_findings': len(findings),
            'high_confidence': len([f for f in findings if f.confidence == 'high']),
            'medium_confidence': len([f for f in findings if f.confidence == 'medium']),
            'low_confidence': len([f for f in findings if f.confidence == 'low']),
            'by_type': {k: len(v) for k, v in by_type.items()},
            'by_file': {k: len(v) for k, v in by_file.items()},
            'findings': [self._finding_to_dict(f) for f in findings]
        }
    
    def _finding_to_dict(self, finding: SecretFinding) -> Dict[str, Any]:
        """Convert finding to dictionary."""
        return {
            'type': finding.secret_type.value,
            'file': finding.file_path,
            'line': finding.line_number,
            'column': f"{finding.column_start}-{finding.column_end}",
            'matched': finding.matched_text,
            'confidence': finding.confidence,
            'rule_id': finding.rule_id,
            'remediation': finding.remediation,
            'hash': finding.hash()
        }


class GitSecretsIntegration:
    """Integration with git-secrets tool."""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
    
    def install_hooks(self) -> bool:
        """Install git-secrets hooks in the repository."""
        try:
            subprocess.run(
                ['git-secrets', '--install', '-f'],
                cwd=self.repo_path,
                check=True,
                capture_output=True
            )
            logger.info("git-secrets hooks installed")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install git-secrets: {e}")
            return False
        except FileNotFoundError:
            logger.error("git-secrets not installed")
            return False
    
    def register_aws_patterns(self) -> bool:
        """Register AWS secret patterns."""
        try:
            subprocess.run(
                ['git-secrets', '--register-aws'],
                cwd=self.repo_path,
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
    
    def scan_history(self) -> List[Dict[str, Any]]:
        """Scan git history for secrets."""
        try:
            result = subprocess.run(
                ['git-secrets', '--scan-history'],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            # Parse output
            findings = []
            for line in result.stderr.split('\n'):
                if 'git-secrets' in line:
                    findings.append({'message': line})
            
            return findings
        except subprocess.CalledProcessError as e:
            logger.error(f"History scan failed: {e}")
            return []


class TruffleHogIntegration:
    """Integration with truffleHog tool."""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
    
    def scan(self, since_commit: Optional[str] = None,
             branch: str = "main") -> List[Dict[str, Any]]:
        """Run truffleHog scan."""
        try:
            cmd = ['trufflehog', 'git', self.repo_path, '--json']
            
            if since_commit:
                cmd.extend(['--since-commit', since_commit])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            findings = []
            for line in result.stdout.split('\n'):
                if line.strip():
                    try:
                        finding = json.loads(line)
                        findings.append(finding)
                    except json.JSONDecodeError:
                        pass
            
            return findings
        
        except FileNotFoundError:
            logger.error("truffleHog not installed")
            return []
        except Exception as e:
            logger.error(f"TruffleHog scan failed: {e}")
            return []


class PreCommitHook:
    """Pre-commit hook for secrets detection."""
    
    def __init__(self, detector: SecretsDetector):
        self.detector = detector
    
    def run(self, staged_files: List[str]) -> Tuple[bool, List[SecretFinding]]:
        """Run pre-commit check on staged files."""
        findings = []
        
        for file_path in staged_files:
            findings.extend(self.detector.scan_file(file_path))
        
        # Fail if high confidence findings
        high_confidence = [f for f in findings if f.confidence == 'high']
        
        if high_confidence:
            print("\n🚫 SECRETS DETECTED - Commit blocked!\n")
            for finding in high_confidence:
                print(f"  {finding.file_path}:{finding.line_number}")
                print(f"    Type: {finding.secret_type.value}")
                print(f"    Remediation: {finding.remediation}\n")
            return False, findings
        
        return True, findings


# CLI entry point
def main():
    """CLI for secrets detection."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Detect secrets in code')
    parser.add_argument('path', help='Path to scan')
    parser.add_argument('--recursive', '-r', action='store_true', help='Scan recursively')
    parser.add_argument('--format', '-f', choices=['json', 'text'], default='text',
                       help='Output format')
    
    args = parser.parse_args()
    
    detector = SecretsDetector()
    
    if Path(args.path).is_file():
        findings = detector.scan_file(args.path)
    else:
        findings = detector.scan_directory(args.path, args.recursive)
    
    report = detector.generate_report(findings)
    
    if args.format == 'json':
        print(json.dumps(report, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"Secrets Scan Report")
        print(f"{'='*60}")
        print(f"Total findings: {report['total_findings']}")
        print(f"High confidence: {report['high_confidence']}")
        print(f"Medium confidence: {report['medium_confidence']}")
        print(f"Low confidence: {report['low_confidence']}")
        
        if findings:
            print(f"\n{'-'*60}")
            print("Findings:")
            print(f"{'-'*60}")
            for finding in findings:
                print(f"\n[{finding.confidence.upper()}] {finding.secret_type.value}")
                print(f"  File: {finding.file_path}:{finding.line_number}")
                print(f"  Remediation: {finding.remediation}")


if __name__ == '__main__':
    main()
