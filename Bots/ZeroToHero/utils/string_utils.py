"""
String utilities for Zero To Hero bot.
"""
import re


def sanitize_string(text: str) -> str:
    """
    Sanitize a string for safe storage and display.
    
    Removes or escapes potentially problematic characters while
    preserving normal text, numbers, and common punctuation.
    
    Args:
        text: Input string to sanitize
        
    Returns:
        Sanitized string safe for JSON storage and UI display
    """
    if not text:
        return ""
    
    # Convert to string if needed
    text = str(text)
    
    # Remove null bytes and other control characters (except newlines/tabs)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length.
    
    Args:
        text: Input string
        max_length: Maximum length including suffix
        suffix: String to append when truncated
        
    Returns:
        Truncated string with suffix if it was shortened
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def is_valid_build_code(code: str) -> bool:
    """
    Check if a string looks like a valid GW build template code.
    
    Build codes are base64-encoded strings that typically:
    - Start with 'O' (for skills template)
    - Are 20+ characters long
    - Contain only alphanumeric characters and +/=
    
    Args:
        code: Potential build code string
        
    Returns:
        True if it looks like a valid build code
    """
    if not code or len(code) < 10:
        return False
    
    if code == "Any":
        return True
    
    # Check for valid base64-ish characters
    valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
    return all(c in valid_chars for c in code)
