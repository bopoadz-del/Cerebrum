"""
Data Loss Prevention (DLP) Scanning
Enterprise-grade data protection and content inspection
"""
import re
import hashlib
import logging
from typing import Optional, List, Dict, Any, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class SensitivityLevel(Enum):
    """Data sensitivity levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    CRITICAL = "critical"


class DLPAction(Enum):
    """DLP policy actions"""
    ALLOW = "allow"
    LOG = "log"
    WARN = "warn"
    BLOCK = "block"
    QUARANTINE = "quarantine"
    ENCRYPT = "encrypt"
    REDACT = "redact"


@dataclass
class DLPPattern:
    """DLP detection pattern"""
    id: str
    name: str
    description: str
    pattern: str
    sensitivity: SensitivityLevel
    confidence_threshold: float = 0.8
    context_keywords: List[str] = field(default_factory=list)
    false_positive_patterns: List[str] = field(default_factory=list)


@dataclass
class DLPMatch:
    """DLP pattern match result"""
    pattern_id: str
    pattern_name: str
    matched_text: str
    position: tuple  # (start, end)
    confidence: float
    context: str
    recommended_action: DLPAction


@dataclass
class DLPScanResult:
    """DLP scan result"""
    content_hash: str
    scan_timestamp: str
    sensitivity_level: SensitivityLevel
    matches: List[DLPMatch] = field(default_factory=list)
    actions_taken: List[DLPAction] = field(default_factory=list)
    redacted_content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DLPPatternLibrary:
    """Library of DLP detection patterns"""
    
    PATTERNS = {
        # PII Patterns
        'PII_SSN': DLPPattern(
            id='PII_SSN',
            name='US Social Security Number',
            description='US Social Security Number format',
            pattern=r'\b(?!000|666|9\d{2})\d{3}-?(?!00)\d{2}-?(?!0000)\d{4}\b',
            sensitivity=SensitivityLevel.RESTRICTED,
            context_keywords=['ssn', 'social security', 'tax id'],
            false_positive_patterns=[r'\d{3}-\d{2}-\d{4}\s*(?:years?|months?|days?)']
        ),
        
        'PII_CREDIT_CARD': DLPPattern(
            id='PII_CREDIT_CARD',
            name='Credit Card Number',
            description='Credit card number with Luhn validation',
            pattern=r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b',
            sensitivity=SensitivityLevel.CRITICAL,
            context_keywords=['credit card', 'card number', 'ccv', 'cvv', 'expiration']
        ),
        
        'PII_EMAIL': DLPPattern(
            id='PII_EMAIL',
            name='Email Address',
            description='Email address pattern',
            pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            sensitivity=SensitivityLevel.INTERNAL,
            context_keywords=['email', 'contact', 'mail to']
        ),
        
        'PII_PHONE': DLPPattern(
            id='PII_PHONE',
            name='Phone Number',
            description='Phone number pattern',
            pattern=r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
            sensitivity=SensitivityLevel.INTERNAL,
            context_keywords=['phone', 'mobile', 'cell', 'contact']
        ),
        
        # Financial Patterns
        'FIN_BANK_ACCOUNT': DLPPattern(
            id='FIN_BANK_ACCOUNT',
            name='Bank Account Number',
            description='Bank account number pattern',
            pattern=r'\b\d{8,17}\b',
            sensitivity=SensitivityLevel.CONFIDENTIAL,
            context_keywords=['account', 'bank', 'routing', 'iban', 'swift']
        ),
        
        'FIN_ROUTING': DLPPattern(
            id='FIN_ROUTING',
            name='Routing Number',
            description='US bank routing number',
            pattern=r'\b[0-9]{9}\b',
            sensitivity=SensitivityLevel.CONFIDENTIAL,
            context_keywords=['routing', 'aba', 'bank code']
        ),
        
        # Healthcare Patterns
        'HIPAA_MRN': DLPPattern(
            id='HIPAA_MRN',
            name='Medical Record Number',
            description='Medical record number pattern',
            pattern=r'\bMRN[:\s]*([A-Z0-9]{6,12})\b',
            sensitivity=SensitivityLevel.RESTRICTED,
            context_keywords=['mrn', 'medical record', 'patient id']
        ),
        
        # API Keys and Secrets
        'SECRET_API_KEY': DLPPattern(
            id='SECRET_API_KEY',
            name='API Key',
            description='Potential API key pattern',
            pattern=r'\b(?:api[_-]?key|apikey)[:\s]*["\']?[a-zA-Z0-9]{32,}["\']?\b',
            sensitivity=SensitivityLevel.CRITICAL,
            context_keywords=['api', 'key', 'token', 'secret']
        ),
        
        'SECRET_PRIVATE_KEY': DLPPattern(
            id='SECRET_PRIVATE_KEY',
            name='Private Key',
            description='Private key pattern',
            pattern=r'-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----',
            sensitivity=SensitivityLevel.CRITICAL,
            context_keywords=['private key', 'pem', 'ssh']
        ),
        
        'SECRET_PASSWORD': DLPPattern(
            id='SECRET_PASSWORD',
            name='Password',
            description='Password in code or config',
            pattern=r'(?:password|passwd|pwd)[:\s]*["\'][^"\']{8,}["\']',
            sensitivity=SensitivityLevel.CRITICAL,
            context_keywords=['password', 'passwd', 'pwd', 'credential']
        ),
        
        # Intellectual Property
        'IP_SOURCE_CODE': DLPPattern(
            id='IP_SOURCE_CODE',
            name='Source Code',
            description='Source code patterns',
            pattern=r'(?:function|def|class|import|package)\s+\w+',
            sensitivity=SensitivityLevel.CONFIDENTIAL,
            context_keywords=['code', 'source', 'proprietary']
        ),
    }
    
    @classmethod
    def get_pattern(cls, pattern_id: str) -> Optional[DLPPattern]:
        """Get pattern by ID"""
        return cls.PATTERNS.get(pattern_id)
    
    @classmethod
    def get_patterns_by_sensitivity(cls, 
                                    level: SensitivityLevel) -> List[DLPPattern]:
        """Get patterns by sensitivity level"""
        return [p for p in cls.PATTERNS.values() 
                if p.sensitivity == level]
    
    @classmethod
    def add_custom_pattern(cls, pattern: DLPPattern):
        """Add custom pattern to library"""
        cls.PATTERNS[pattern.id] = pattern


class DLPScanner:
    """DLP content scanner"""
    
    def __init__(self):
        self._patterns: Dict[str, DLPPattern] = DLPPatternLibrary.PATTERNS.copy()
        self._custom_patterns: Dict[str, DLPPattern] = {}
        self._scan_history: List[DLPScanResult] = []
    
    def add_pattern(self, pattern: DLPPattern):
        """Add custom detection pattern"""
        self._custom_patterns[pattern.id] = pattern
        self._patterns[pattern.id] = pattern
    
    def scan_text(self, content: str, 
                  patterns: List[str] = None,
                  min_confidence: float = 0.5) -> DLPScanResult:
        """Scan text content for sensitive data"""
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        # Determine patterns to use
        if patterns:
            pattern_list = [self._patterns.get(p) for p in patterns 
                          if p in self._patterns]
        else:
            pattern_list = list(self._patterns.values())
        
        matches = []
        max_sensitivity = SensitivityLevel.PUBLIC
        
        for pattern in pattern_list:
            if not pattern:
                continue
            
            pattern_matches = self._find_pattern_matches(
                content, pattern, min_confidence)
            matches.extend(pattern_matches)
            
            # Track highest sensitivity
            if pattern_matches:
                sensitivity_order = [
                    SensitivityLevel.PUBLIC,
                    SensitivityLevel.INTERNAL,
                    SensitivityLevel.CONFIDENTIAL,
                    SensitivityLevel.RESTRICTED,
                    SensitivityLevel.CRITICAL
                ]
                if sensitivity_order.index(pattern.sensitivity) > \
                   sensitivity_order.index(max_sensitivity):
                    max_sensitivity = pattern.sensitivity
        
        result = DLPScanResult(
            content_hash=content_hash,
            scan_timestamp=__import__('datetime').datetime.utcnow().isoformat(),
            sensitivity_level=max_sensitivity,
            matches=matches
        )
        
        self._scan_history.append(result)
        return result
    
    def _find_pattern_matches(self, content: str, 
                              pattern: DLPPattern,
                              min_confidence: float) -> List[DLPMatch]:
        """Find all matches for a pattern"""
        matches = []
        
        try:
            for match in re.finditer(pattern.pattern, content, re.IGNORECASE):
                matched_text = match.group(0)
                
                # Calculate confidence
                confidence = self._calculate_confidence(
                    content, match, pattern)
                
                if confidence < min_confidence:
                    continue
                
                # Check for false positives
                if self._is_false_positive(matched_text, pattern):
                    continue
                
                # Get context
                context_start = max(0, match.start() - 50)
                context_end = min(len(content), match.end() + 50)
                context = content[context_start:context_end]
                
                # Determine action
                action = self._determine_action(pattern.sensitivity, confidence)
                
                matches.append(DLPMatch(
                    pattern_id=pattern.id,
                    pattern_name=pattern.name,
                    matched_text=matched_text,
                    position=(match.start(), match.end()),
                    confidence=confidence,
                    context=context,
                    recommended_action=action
                ))
        
        except re.error as e:
            logger.error(f"Regex error in pattern {pattern.id}: {e}")
        
        return matches
    
    def _calculate_confidence(self, content: str, 
                              match: re.Match,
                              pattern: DLPPattern) -> float:
        """Calculate confidence score for a match"""
        confidence = 0.5
        
        # Check context keywords
        context_start = max(0, match.start() - 100)
        context_end = min(len(content), match.end() + 100)
        context = content[context_start:context_end].lower()
        
        keyword_matches = sum(1 for kw in pattern.context_keywords 
                             if kw.lower() in context)
        confidence += keyword_matches * 0.1
        
        # Validate format (e.g., Luhn check for credit cards)
        if pattern.id == 'PII_CREDIT_CARD':
            if self._luhn_check(match.group(0).replace('-', '').replace(' ', '')):
                confidence += 0.3
            else:
                confidence -= 0.3
        
        return min(1.0, confidence)
    
    def _is_false_positive(self, matched_text: str, 
                           pattern: DLPPattern) -> bool:
        """Check if match is a false positive"""
        for fp_pattern in pattern.false_positive_patterns:
            if re.search(fp_pattern, matched_text, re.IGNORECASE):
                return True
        return False
    
    def _luhn_check(self, card_number: str) -> bool:
        """Validate credit card number with Luhn algorithm"""
        try:
            digits = [int(d) for d in card_number if d.isdigit()]
            if len(digits) < 13:
                return False
            
            odd_sum = sum(digits[-1::-2])
            even_sum = sum([sum(divmod(2 * d, 10)) for d in digits[-2::-2]])
            return (odd_sum + even_sum) % 10 == 0
        except:
            return False
    
    def _determine_action(self, sensitivity: SensitivityLevel,
                          confidence: float) -> DLPAction:
        """Determine recommended action based on sensitivity and confidence"""
        if sensitivity == SensitivityLevel.CRITICAL and confidence > 0.9:
            return DLPAction.BLOCK
        elif sensitivity == SensitivityLevel.RESTRICTED and confidence > 0.8:
            return DLPAction.QUARANTINE
        elif sensitivity == SensitivityLevel.CONFIDENTIAL and confidence > 0.7:
            return DLPAction.ENCRYPT
        elif confidence > 0.6:
            return DLPAction.WARN
        else:
            return DLPAction.LOG
    
    def redact_content(self, content: str, 
                       result: DLPScanResult,
                       replacement: str = '[REDACTED]') -> str:
        """Redact sensitive content based on scan results"""
        redacted = content
        
        # Sort matches by position (reverse) to avoid offset issues
        sorted_matches = sorted(result.matches, 
                               key=lambda m: m.position[0], 
                               reverse=True)
        
        for match in sorted_matches:
            start, end = match.position
            redacted = redacted[:start] + replacement + redacted[end:]
        
        return redacted
    
    def scan_file(self, file_path: str, 
                  file_content: bytes = None) -> DLPScanResult:
        """Scan file for sensitive data"""
        if file_content is None:
            with open(file_path, 'rb') as f:
                file_content = f.read()
        
        # Try to decode as text
        try:
            content = file_content.decode('utf-8')
        except UnicodeDecodeError:
            # Binary file - check for embedded text patterns
            content = self._extract_text_from_binary(file_content)
        
        result = self.scan_text(content)
        result.metadata['file_path'] = file_path
        result.metadata['file_size'] = len(file_content)
        
        return result
    
    def _extract_text_from_binary(self, data: bytes) -> str:
        """Extract readable text from binary data"""
        # Simple extraction - look for printable ASCII
        text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | 
                              set(range(0x20, 0x100)) - {0x7f})
        
        result = ''
        for byte in data:
            if byte in text_chars:
                result += chr(byte)
            else:
                result += ' '
        
        return result


class DLPPolicy:
    """DLP policy definition"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.rules: List[Dict] = []
    
    def add_rule(self, pattern_ids: List[str],
                 sensitivity: SensitivityLevel,
                 action: DLPAction,
                 conditions: Dict = None):
        """Add policy rule"""
        self.rules.append({
            'patterns': pattern_ids,
            'sensitivity': sensitivity,
            'action': action,
            'conditions': conditions or {}
        })
    
    def evaluate(self, scan_result: DLPScanResult) -> List[DLPAction]:
        """Evaluate scan result against policy"""
        actions = []
        
        for rule in self.rules:
            # Check if rule matches
            rule_patterns = set(rule['patterns'])
            match_patterns = set(m.pattern_id for m in scan_result.matches)
            
            if rule_patterns & match_patterns:
                # Check sensitivity
                if scan_result.sensitivity_level.value == rule['sensitivity'].value:
                    actions.append(rule['action'])
        
        return actions


class DLPManager:
    """Main DLP management class"""
    
    def __init__(self):
        self.scanner = DLPScanner()
        self.policies: Dict[str, DLPPolicy] = {}
        self._blocked_hashes: Set[str] = set()
        self._quarantine: List[Dict] = []
    
    def create_policy(self, name: str, description: str = "") -> DLPPolicy:
        """Create new DLP policy"""
        policy = DLPPolicy(name, description)
        self.policies[name] = policy
        return policy
    
    def scan_and_enforce(self, content: str, 
                         policy_name: str = None) -> DLPScanResult:
        """Scan content and enforce policies"""
        # Scan content
        result = self.scanner.scan_text(content)
        
        # Apply policy if specified
        if policy_name and policy_name in self.policies:
            policy = self.policies[policy_name]
            actions = policy.evaluate(result)
            result.actions_taken = actions
            
            # Execute actions
            for action in actions:
                self._execute_action(action, content, result)
        
        return result
    
    def _execute_action(self, action: DLPAction, 
                        content: str,
                        result: DLPScanResult):
        """Execute DLP action"""
        if action == DLPAction.REDACT:
            result.redacted_content = self.scanner.redact_content(content, result)
        
        elif action == DLPAction.BLOCK:
            self._blocked_hashes.add(result.content_hash)
        
        elif action == DLPAction.QUARANTINE:
            self._quarantine.append({
                'hash': result.content_hash,
                'timestamp': __import__('datetime').datetime.utcnow().isoformat(),
                'matches': [m.pattern_name for m in result.matches]
            })
        
        logger.info(f"DLP action executed: {action.value}")
    
    def is_blocked(self, content_hash: str) -> bool:
        """Check if content is blocked"""
        return content_hash in self._blocked_hashes


# Global DLP manager
dlp_manager = DLPManager()