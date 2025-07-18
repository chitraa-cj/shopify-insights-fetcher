import re
import logging
from typing import List, Optional
from urllib.parse import urlparse, urljoin

logger = logging.getLogger(__name__)

def validate_url(url: str) -> bool:
    """
    Validate if a URL is properly formatted
    
    Args:
        url: URL to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def normalize_url(url: str) -> str:
    """
    Normalize URL to ensure consistent formatting
    
    Args:
        url: URL to normalize
        
    Returns:
        str: Normalized URL
    """
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Remove trailing slash
    url = url.rstrip('/')
    
    return url

def extract_domain(url: str) -> Optional[str]:
    """
    Extract domain from URL
    
    Args:
        url: URL to extract domain from
        
    Returns:
        str: Domain name or None if invalid
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return None

def clean_text(text: str) -> str:
    """
    Clean and normalize text content
    
    Args:
        text: Text to clean
        
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove non-printable characters
    text = ''.join(char for char in text if char.isprintable() or char.isspace())
    
    return text.strip()

def extract_emails(text: str) -> List[str]:
    """
    Extract email addresses from text
    
    Args:
        text: Text to search for emails
        
    Returns:
        List[str]: List of email addresses found
    """
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    
    # Filter out common false positives
    filtered_emails = []
    for email in emails:
        if not any(exclude in email.lower() for exclude in ['example.com', 'test.com', 'placeholder']):
            filtered_emails.append(email)
    
    return list(set(filtered_emails))  # Remove duplicates

def extract_phone_numbers(text: str) -> List[str]:
    """
    Extract phone numbers from text
    
    Args:
        text: Text to search for phone numbers
        
    Returns:
        List[str]: List of phone numbers found
    """
    # Various phone number patterns
    patterns = [
        r'\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',  # US format
        r'\+?([0-9]{1,3})[-.\s]?([0-9]{3,4})[-.\s]?([0-9]{3,4})[-.\s]?([0-9]{3,4})',  # International
    ]
    
    phone_numbers = []
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if len(match) == 3:  # US format
                phone = f"({match[0]}) {match[1]}-{match[2]}"
            else:  # International format
                phone = "-".join(match)
            
            phone_numbers.append(phone)
    
    return list(set(phone_numbers))  # Remove duplicates

def is_shopify_store(url: str) -> bool:
    """
    Check if a URL is likely a Shopify store
    
    Args:
        url: URL to check
        
    Returns:
        bool: True if likely a Shopify store
    """
    # This is a basic check - in practice, you might want more sophisticated detection
    shopify_indicators = [
        'myshopify.com',
        'shopify',
        '/products.json'  # This endpoint is specific to Shopify
    ]
    
    url_lower = url.lower()
    return any(indicator in url_lower for indicator in shopify_indicators)

def truncate_text(text: str, max_length: int = 1000) -> str:
    """
    Truncate text to a maximum length
    
    Args:
        text: Text to truncate
        max_length: Maximum length allowed
        
    Returns:
        str: Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    truncated = text[:max_length]
    
    # Try to truncate at word boundary
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.8:  # If we can find a space in the last 20%
        truncated = truncated[:last_space]
    
    return truncated + "..."

def safe_get_text(element, default: str = "") -> str:
    """
    Safely get text from a BeautifulSoup element
    
    Args:
        element: BeautifulSoup element
        default: Default value if element is None
        
    Returns:
        str: Text content or default
    """
    if element is None:
        return default
    
    try:
        return clean_text(element.get_text(strip=True))
    except Exception:
        return default
