"""
Security Scanning

Bandit, Semgrep, and ESLint security scanning for generated code.
"""
import os
import json
import tempfile
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    """Severity levels for security issues."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class SecurityIssue:
    """Represents a security issue found in code."""
    tool: str
    rule_id: str
    message: str
    severity: Severity
    line: int
    column: int
    file: str
    code_snippet: str
    remediation: str


@dataclass
class SecurityScanResult:
    """Result of security scanning."""
    success: bool
    passed: bool
    issues: List[SecurityIssue]
    summary: Dict[str, int]  # severity counts
    scan_time_ms: float


class BanditScanner:
    """Python security scanner using Bandit."""
    
    SEVERITY_MAP = {
        "CRITICAL": Severity.CRITICAL,
        "HIGH": Severity.HIGH,
        "MEDIUM": Severity.MEDIUM,
        "LOW": Severity.LOW
    }
    
    def scan(self, code: str, filename: str = "generated.py") -> SecurityScanResult:
        """Scan Python code with Bandit."""
        import time
        start_time = time.time()
        
        issues = []
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Run bandit
            result = subprocess.run(
                ["bandit", "-f", "json", "-o", "/dev/stdout", temp_file],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Parse JSON output
            try:
                bandit_output = json.loads(result.stdout)
                
                for finding in bandit_output.get("results", []):
                    issue = SecurityIssue(
                        tool="bandit",
                        rule_id=finding.get("test_id", "UNKNOWN"),
                        message=finding.get("issue_text", ""),
                        severity=self.SEVERITY_MAP.get(
                            finding.get("issue_severity", "LOW"), 
                            Severity.LOW
                        ),
                        line=finding.get("line_number", 0),
                        column=0,
                        file=filename,
                        code_snippet=finding.get("code", ""),
                        remediation=self._get_remediation(finding.get("test_id", ""))
                    )
                    issues.append(issue)
            
            except json.JSONDecodeError:
                logger.warning("Failed to parse Bandit output")
        
        except subprocess.TimeoutExpired:
            logger.error("Bandit scan timed out")
        except Exception as e:
            logger.error(f"Bandit scan error: {e}")
        
        finally:
            try:
                os.unlink(temp_file)
            except:
                pass
        
        scan_time = (time.time() - start_time) * 1000
        summary = self._summarize_issues(issues)
        
        return SecurityScanResult(
            success=True,
            passed=len([i for i in issues if i.severity in [Severity.CRITICAL, Severity.HIGH]]) == 0,
            issues=issues,
            summary=summary,
            scan_time_ms=scan_time
        )
    
    def _get_remediation(self, rule_id: str) -> str:
        """Get remediation advice for a rule."""
        remediations = {
            "B102": "Use subprocess.run with shell=False",
            "B301": "Avoid pickle, use json instead",
            "B307": "Avoid eval(), use ast.literal_eval for safe evaluation",
            "B608": "Use parameterized queries to prevent SQL injection",
            "B105": "Don't hardcode passwords, use environment variables",
            "B311": "Use secrets module for cryptographic operations"
        }
        return remediations.get(rule_id, "Review and fix the security issue")
    
    def _summarize_issues(self, issues: List[SecurityIssue]) -> Dict[str, int]:
        """Summarize issues by severity."""
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for issue in issues:
            summary[issue.severity.value] += 1
        return summary


class SemgrepScanner:
    """Multi-language security scanner using Semgrep."""
    
    SEVERITY_MAP = {
        "ERROR": Severity.CRITICAL,
        "WARNING": Severity.HIGH,
        "INFO": Severity.MEDIUM
    }
    
    def scan(
        self, 
        code: str, 
        language: str,
        filename: str = "generated"
    ) -> SecurityScanResult:
        """Scan code with Semgrep."""
        import time
        start_time = time.time()
        
        issues = []
        
        # Map language to file extension
        ext_map = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts"
        }
        ext = ext_map.get(language, ".py")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Run semgrep
            result = subprocess.run(
                [
                    "semgrep", 
                    "--config=auto",
                    "--json",
                    "--quiet",
                    temp_file
                ],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # Parse JSON output
            try:
                semgrep_output = json.loads(result.stdout)
                
                for finding in semgrep_output.get("results", []):
                    issue = SecurityIssue(
                        tool="semgrep",
                        rule_id=finding.get("check_id", "UNKNOWN").split(".")[-1],
                        message=finding.get("extra", {}).get("message", ""),
                        severity=self.SEVERITY_MAP.get(
                            finding.get("extra", {}).get("severity", "INFO"),
                            Severity.LOW
                        ),
                        line=finding.get("start", {}).get("line", 0),
                        column=finding.get("start", {}).get("col", 0),
                        file=filename,
                        code_snippet=finding.get("extra", {}).get("lines", ""),
                        remediation="Review Semgrep documentation for this rule"
                    )
                    issues.append(issue)
            
            except json.JSONDecodeError:
                logger.warning("Failed to parse Semgrep output")
        
        except subprocess.TimeoutExpired:
            logger.error("Semgrep scan timed out")
        except Exception as e:
            logger.error(f"Semgrep scan error: {e}")
        
        finally:
            try:
                os.unlink(temp_file)
            except:
                pass
        
        scan_time = (time.time() - start_time) * 1000
        summary = self._summarize_issues(issues)
        
        return SecurityScanResult(
            success=True,
            passed=len([i for i in issues if i.severity in [Severity.CRITICAL, Severity.HIGH]]) == 0,
            issues=issues,
            summary=summary,
            scan_time_ms=scan_time
        )
    
    def _summarize_issues(self, issues: List[SecurityIssue]) -> Dict[str, int]:
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for issue in issues:
            summary[issue.severity.value] += 1
        return summary


class ESLintScanner:
    """JavaScript/TypeScript security scanner using ESLint."""
    
    def scan(
        self, 
        code: str, 
        language: str = "typescript",
        filename: str = "generated.tsx"
    ) -> SecurityScanResult:
        """Scan JS/TS code with ESLint security rules."""
        import time
        start_time = time.time()
        
        issues = []
        
        # Only scan JS/TS
        if language not in ["javascript", "typescript"]:
            return SecurityScanResult(
                success=True,
                passed=True,
                issues=[],
                summary={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
                scan_time_ms=0
            )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tsx', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Run ESLint with security plugin
            result = subprocess.run(
                [
                    "eslint",
                    "--format", "json",
                    "--plugin", "security",
                    "--rule", "security/detect-eval-with-expression: error",
                    "--rule", "security/detect-non-literal-fs-filename: error",
                    "--rule", "security/detect-unsafe-regex: error",
                    temp_file
                ],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Parse JSON output
            try:
                eslint_output = json.loads(result.stdout)
                
                for file_result in eslint_output:
                    for message in file_result.get("messages", []):
                        if message.get("ruleId", "").startswith("security/"):
                            issue = SecurityIssue(
                                tool="eslint-security",
                                rule_id=message.get("ruleId", "UNKNOWN"),
                                message=message.get("message", ""),
                                severity=Severity.HIGH if message.get("severity") == 2 else Severity.MEDIUM,
                                line=message.get("line", 0),
                                column=message.get("column", 0),
                                file=filename,
                                code_snippet="",
                                remediation="Fix the security issue identified"
                            )
                            issues.append(issue)
            
            except json.JSONDecodeError:
                logger.warning("Failed to parse ESLint output")
        
        except subprocess.TimeoutExpired:
            logger.error("ESLint scan timed out")
        except Exception as e:
            logger.error(f"ESLint scan error: {e}")
        
        finally:
            try:
                os.unlink(temp_file)
            except:
                pass
        
        scan_time = (time.time() - start_time) * 1000
        summary = self._summarize_issues(issues)
        
        return SecurityScanResult(
            success=True,
            passed=len([i for i in issues if i.severity in [Severity.CRITICAL, Severity.HIGH]]) == 0,
            issues=issues,
            summary=summary,
            scan_time_ms=scan_time
        )
    
    def _summarize_issues(self, issues: List[SecurityIssue]) -> Dict[str, int]:
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for issue in issues:
            summary[issue.severity.value] += 1
        return summary


class SecurityScanner:
    """Unified security scanner using multiple tools."""
    
    def __init__(self):
        self.bandit = BanditScanner()
        self.semgrep = SemgrepScanner()
        self.eslint = ESLintScanner()
    
    def scan(
        self,
        code: str,
        language: str = "python",
        filename: Optional[str] = None
    ) -> SecurityScanResult:
        """
        Run comprehensive security scan.
        
        Args:
            code: Code to scan
            language: Programming language
            filename: Optional filename for reporting
        
        Returns:
            Combined security scan result
        """
        all_issues = []
        total_time = 0
        
        # Python scanning
        if language == "python":
            bandit_result = self.bandit.scan(code, filename or "generated.py")
            all_issues.extend(bandit_result.issues)
            total_time += bandit_result.scan_time_ms
            
            semgrep_result = self.semgrep.scan(code, "python", filename or "generated.py")
            all_issues.extend(semgrep_result.issues)
            total_time += semgrep_result.scan_time_ms
        
        # JS/TS scanning
        elif language in ["javascript", "typescript"]:
            semgrep_result = self.semgrep.scan(code, language, filename or "generated.tsx")
            all_issues.extend(semgrep_result.issues)
            total_time += semgrep_result.scan_time_ms
            
            eslint_result = self.eslint.scan(code, language, filename or "generated.tsx")
            all_issues.extend(eslint_result.issues)
            total_time += eslint_result.scan_time_ms
        
        # Summarize all issues
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for issue in all_issues:
            summary[issue.severity.value] += 1
        
        # Determine if passed (no critical or high issues)
        passed = summary["critical"] == 0 and summary["high"] == 0
        
        return SecurityScanResult(
            success=True,
            passed=passed,
            issues=all_issues,
            summary=summary,
            scan_time_ms=total_time
        )
    
    def scan_file(self, file_path: str) -> SecurityScanResult:
        """Scan a file for security issues."""
        with open(file_path, 'r') as f:
            code = f.read()
        
        # Detect language from extension
        ext = os.path.splitext(file_path)[1]
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript"
        }
        language = lang_map.get(ext, "python")
        
        return self.scan(code, language, file_path)
