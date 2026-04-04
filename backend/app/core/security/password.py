"""
Password Hashing and Verification

Provides secure password hashing using bcrypt with configurable
salt rounds and optional pepper for additional security.
"""

import bcrypt

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class PasswordError(Exception):
    """Password-related error."""
    pass


class PasswordValidationError(PasswordError):
    """Password validation error."""
    pass


class PasswordManager:
    """
    Password hashing and verification manager.
    
    Uses bcrypt with configurable salt rounds and optional
    pepper for additional security layer.
    
    Attributes:
        salt_rounds: Number of bcrypt salt rounds (default: 12)
        pepper: Optional pepper string from environment
    """
    
    # Minimum password requirements
    MIN_LENGTH = 8
    MAX_LENGTH = 128
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    
    def __init__(self, salt_rounds: int = 12) -> None:
        """
        Initialize password manager.
        
        Args:
            salt_rounds: Number of bcrypt salt rounds
        """
        self.salt_rounds = salt_rounds
        self.pepper = settings.PASSWORD_PEPPER or ""
    
    def _apply_pepper(self, password: str) -> str:
        """
        Apply pepper to password.
        
        Args:
            password: Plain text password
            
        Returns:
            Password with pepper applied
        """
        if self.pepper:
            return f"{password}{self.pepper}"
        return password
    
    def hash(self, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Bcrypt hashed password
        """
        # Apply pepper before hashing
        peppered = self._apply_pepper(password)
        
        # Generate salt and hash
        salt = bcrypt.gensalt(rounds=self.salt_rounds)
        hashed = bcrypt.hashpw(peppered.encode("utf-8"), salt)
        
        return hashed.decode("utf-8")
    
    def verify(self, password: str, hashed: str) -> bool:
        """
        Verify a password against a hash.
        
        Args:
            password: Plain text password
            hashed: Bcrypt hashed password
            
        Returns:
            True if password matches
        """
        try:
            peppered = self._apply_pepper(password)
            return bcrypt.checkpw(
                peppered.encode("utf-8"),
                hashed.encode("utf-8"),
            )
        except Exception as e:
            logger.warning("Password verification failed", error=str(e))
            return False
    
    def validate(self, password: str) -> tuple[bool, list[str]]:
        """
        Validate password against security requirements.
        
        Args:
            password: Plain text password
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Check length
        if len(password) < self.MIN_LENGTH:
            errors.append(f"Password must be at least {self.MIN_LENGTH} characters")
        
        if len(password) > self.MAX_LENGTH:
            errors.append(f"Password must not exceed {self.MAX_LENGTH} characters")
        
        # Check character requirements
        if self.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if self.REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if self.REQUIRE_DIGIT and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        if self.REQUIRE_SPECIAL:
            special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            if not any(c in special_chars for c in password):
                errors.append("Password must contain at least one special character")
        
        # Check for common passwords (simplified)
        common_passwords = {
            "password", "123456", "qwerty", "admin", "letmein",
            "welcome", "monkey", "1234567890", "abc123", "football",
        }
        if password.lower() in common_passwords:
            errors.append("Password is too common")
        
        return len(errors) == 0, errors
    
    def needs_rehash(self, hashed: str) -> bool:
        """
        Check if password needs to be rehashed.
        
        Used when salt rounds are increased to upgrade old hashes.
        
        Args:
            hashed: Existing bcrypt hash
            
        Returns:
            True if password should be rehashed
        """
        # Extract salt rounds from hash
        try:
            # Bcrypt hash format: $2b$<rounds>$<salt><hash>
            parts = hashed.split("$")
            if len(parts) >= 3:
                hash_rounds = int(parts[2])
                return hash_rounds < self.salt_rounds
        except (ValueError, IndexError):
            pass
        
        return True
    
    def generate_password(self, length: int = 16) -> str:
        """
        Generate a secure random password.
        
        Args:
            length: Password length
            
        Returns:
            Generated password
        """
        import secrets
        import string
        
        # Ensure we have at least one of each required character type
        password = [
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.digits),
            secrets.choice("!@#$%^&*()_+-=[]{}|;:,.<>?"),
        ]
        
        # Fill the rest with random characters
        all_chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
        password.extend(secrets.choice(all_chars) for _ in range(length - 4))
        
        # Shuffle the password
        secrets.SystemRandom().shuffle(password)
        
        return "".join(password)


# Global password manager instance
password_manager = PasswordManager()


def hash_password(password: str) -> str:
    """Hash password convenience function."""
    return password_manager.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify password convenience function."""
    return password_manager.verify(password, hashed)


def validate_password(password: str) -> tuple[bool, list[str]]:
    """Validate password convenience function."""
    return password_manager.validate(password)
