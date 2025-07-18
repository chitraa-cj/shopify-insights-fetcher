"""
Base classes and interfaces for the Shopify scraper services.
Implements SOLID principles with proper abstractions and error handling.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import logging
import requests
from urllib.parse import urlparse, urljoin
import time

logger = logging.getLogger(__name__)

class ExtractionResult(Enum):
    """Enumeration for extraction operation results"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    INVALID_INPUT = "invalid_input"
    RATE_LIMITED = "rate_limited"

@dataclass
class OperationResult:
    """Generic result container for all operations"""
    status: ExtractionResult
    data: Any = None
    error_message: Optional[str] = None
    warnings: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def is_success(self) -> bool:
        return self.status == ExtractionResult.SUCCESS
    
    @property
    def is_partial_success(self) -> bool:
        return self.status == ExtractionResult.PARTIAL_SUCCESS
    
    @property
    def has_data(self) -> bool:
        return self.data is not None

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

class ExtractionError(Exception):
    """Custom exception for extraction errors"""
    pass

class NetworkError(Exception):
    """Custom exception for network-related errors"""
    pass

class URLValidator:
    """Utility class for URL validation and normalization"""
    
    ALLOWED_SCHEMES = {'http', 'https'}
    SHOPIFY_INDICATORS = ['.myshopify.com', 'shopify', 'shop.', 'store.']
    
    @staticmethod
    def validate_url(url: str) -> OperationResult:
        """Validate and normalize a URL"""
        try:
            if not url or not isinstance(url, str):
                return OperationResult(
                    status=ExtractionResult.INVALID_INPUT,
                    error_message="URL cannot be empty or None"
                )
            
            url = url.strip()
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            parsed = urlparse(url)
            
            if parsed.scheme not in URLValidator.ALLOWED_SCHEMES:
                return OperationResult(
                    status=ExtractionResult.INVALID_INPUT,
                    error_message=f"Invalid URL scheme: {parsed.scheme}"
                )
            
            if not parsed.netloc:
                return OperationResult(
                    status=ExtractionResult.INVALID_INPUT,
                    error_message="Invalid URL: no domain found"
                )
            
            # Check if URL looks like a Shopify store
            is_shopify = any(indicator in url.lower() for indicator in URLValidator.SHOPIFY_INDICATORS)
            
            return OperationResult(
                status=ExtractionResult.SUCCESS,
                data=url,
                metadata={
                    'is_likely_shopify': is_shopify,
                    'domain': parsed.netloc,
                    'normalized_url': url
                }
            )
            
        except Exception as e:
            return OperationResult(
                status=ExtractionResult.FAILURE,
                error_message=f"URL validation failed: {str(e)}"
            )

class RateLimiter:
    """Simple rate limiting implementation"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def can_proceed(self) -> bool:
        """Check if a request can proceed based on rate limits"""
        now = time.time()
        # Remove old requests outside the time window
        self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
        
        if len(self.requests) >= self.max_requests:
            return False
        
        self.requests.append(now)
        return True
    
    def get_reset_time(self) -> float:
        """Get time until rate limit resets"""
        if not self.requests:
            return 0
        
        oldest_request = min(self.requests)
        return max(0, self.time_window - (time.time() - oldest_request))

class NetworkHandler:
    """Handles all network operations with proper error handling and retries"""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3, backoff_factor: float = 0.3):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.rate_limiter = RateLimiter()
    
    def get(self, url: str, **kwargs) -> OperationResult:
        """Make a GET request with proper error handling and retries"""
        if not self.rate_limiter.can_proceed():
            reset_time = self.rate_limiter.get_reset_time()
            return OperationResult(
                status=ExtractionResult.RATE_LIMITED,
                error_message=f"Rate limit exceeded. Try again in {reset_time:.1f} seconds"
            )
        
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    **kwargs
                )
                
                if response.status_code == 404:
                    return OperationResult(
                        status=ExtractionResult.INVALID_INPUT,
                        error_message="Website not found (404)"
                    )
                elif response.status_code == 403:
                    return OperationResult(
                        status=ExtractionResult.FAILURE,
                        error_message="Access forbidden (403) - website may be blocking requests"
                    )
                elif response.status_code == 429:
                    return OperationResult(
                        status=ExtractionResult.RATE_LIMITED,
                        error_message="Too many requests (429) - rate limited by server"
                    )
                elif response.status_code >= 500:
                    if attempt < self.max_retries:
                        wait_time = self.backoff_factor * (2 ** attempt)
                        logger.warning(f"Server error {response.status_code}, retrying in {wait_time}s")
                        time.sleep(wait_time)
                        continue
                    else:
                        return OperationResult(
                            status=ExtractionResult.FAILURE,
                            error_message=f"Server error ({response.status_code})"
                        )
                
                response.raise_for_status()
                
                return OperationResult(
                    status=ExtractionResult.SUCCESS,
                    data=response,
                    metadata={
                        'status_code': response.status_code,
                        'content_type': response.headers.get('content-type', ''),
                        'content_length': len(response.content),
                        'url': response.url
                    }
                )
                
            except requests.exceptions.Timeout:
                if attempt < self.max_retries:
                    wait_time = self.backoff_factor * (2 ** attempt)
                    logger.warning(f"Request timeout, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    return OperationResult(
                        status=ExtractionResult.TIMEOUT,
                        error_message="Request timed out after multiple retries"
                    )
            
            except requests.exceptions.ConnectionError as e:
                if attempt < self.max_retries:
                    wait_time = self.backoff_factor * (2 ** attempt)
                    logger.warning(f"Connection error, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    return OperationResult(
                        status=ExtractionResult.FAILURE,
                        error_message=f"Connection error: {str(e)}"
                    )
            
            except Exception as e:
                return OperationResult(
                    status=ExtractionResult.FAILURE,
                    error_message=f"Unexpected error: {str(e)}"
                )
        
        return OperationResult(
            status=ExtractionResult.FAILURE,
            error_message="Max retries exceeded"
        )
    
    def close(self):
        """Close the session"""
        self.session.close()

class BaseExtractor(ABC):
    """Abstract base class for all extractors"""
    
    def __init__(self, network_handler: NetworkHandler):
        self.network_handler = network_handler
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def extract(self, url: str, **kwargs) -> OperationResult:
        """Extract data from the given URL"""
        pass
    
    def validate_input(self, url: str, **kwargs) -> OperationResult:
        """Validate input parameters"""
        url_result = URLValidator.validate_url(url)
        if not url_result.is_success:
            return url_result
        
        return OperationResult(status=ExtractionResult.SUCCESS, data=url_result.data)
    
    def handle_extraction_error(self, error: Exception, context: str = "") -> OperationResult:
        """Centralized error handling for extraction operations"""
        error_msg = f"{context}: {str(error)}" if context else str(error)
        self.logger.error(error_msg)
        
        if isinstance(error, ValidationError):
            return OperationResult(
                status=ExtractionResult.INVALID_INPUT,
                error_message=error_msg
            )
        elif isinstance(error, NetworkError):
            return OperationResult(
                status=ExtractionResult.FAILURE,
                error_message=error_msg
            )
        else:
            return OperationResult(
                status=ExtractionResult.FAILURE,
                error_message=error_msg
            )

class BaseService(ABC):
    """Abstract base class for all services"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.network_handler = NetworkHandler()
        self._initialized = False
    
    async def initialize(self) -> OperationResult:
        """Initialize the service"""
        try:
            await self._initialize_internal()
            self._initialized = True
            self.logger.info(f"{self.__class__.__name__} initialized successfully")
            return OperationResult(status=ExtractionResult.SUCCESS)
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.__class__.__name__}: {e}")
            return OperationResult(
                status=ExtractionResult.FAILURE,
                error_message=f"Initialization failed: {str(e)}"
            )
    
    @abstractmethod
    async def _initialize_internal(self):
        """Internal initialization logic - to be implemented by subclasses"""
        pass
    
    def ensure_initialized(self):
        """Ensure the service is initialized"""
        if not self._initialized:
            raise RuntimeError(f"{self.__class__.__name__} not initialized. Call initialize() first.")
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if hasattr(self, 'network_handler'):
                self.network_handler.close()
            await self._cleanup_internal()
            self.logger.info(f"{self.__class__.__name__} cleaned up successfully")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    async def _cleanup_internal(self):
        """Internal cleanup logic - can be overridden by subclasses"""
        pass

class ConfigurationManager:
    """Manages application configuration with validation"""
    
    DEFAULT_CONFIG = {
        'timeout': 30,
        'max_retries': 3,
        'rate_limit_requests': 10,
        'rate_limit_window': 60,
        'max_products_per_page': 250,
        'max_pages': 10,
        'ai_enabled': True,
        'database_enabled': True
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = self.DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration values"""
        required_keys = ['timeout', 'max_retries', 'rate_limit_requests']
        for key in required_keys:
            if key not in self.config:
                raise ValidationError(f"Missing required configuration: {key}")
            
            if not isinstance(self.config[key], int) or self.config[key] <= 0:
                raise ValidationError(f"Invalid configuration value for {key}: must be positive integer")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def update(self, updates: Dict[str, Any]):
        """Update configuration"""
        self.config.update(updates)
        self._validate_config()