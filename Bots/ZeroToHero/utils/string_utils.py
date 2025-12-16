"""
String utility functions used across the bot.
Centralizes string sanitization and formatting.
"""


def sanitize_string(s):
    """
    Removes null bytes and strips whitespace from strings.
    
    Args:
        s: Input string or other type
        
    Returns:
        Sanitized string, or original value if not a string
    """
    if isinstance(s, str):
        return s.replace('\0', '').strip()
    return s


def sanitize_dict_strings(data):
    """
    Recursively sanitizes all strings in a dictionary.
    
    Args:
        data: Dictionary or nested structure
        
    Returns:
        Sanitized copy of the data
    """
    if isinstance(data, dict):
        return {k: sanitize_dict_strings(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_dict_strings(item) for item in data]
    elif isinstance(data, str):
        return sanitize_string(data)
    else:
        return data