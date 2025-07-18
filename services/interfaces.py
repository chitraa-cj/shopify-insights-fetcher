"""
Interface definitions following the Interface Segregation Principle.
Each interface defines a specific set of related capabilities.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from models import (
    Product, BrandContext, PolicyInfo, FAQ, SocialHandles, 
    ContactDetails, ImportantLinks, CompetitorAnalysis, AIValidationResult
)
from services.base import OperationResult

class IProductExtractor(ABC):
    """Interface for product extraction capabilities"""
    
    @abstractmethod
    async def extract_products(self, url: str, max_products: Optional[int] = None) -> OperationResult:
        """Extract products from a store"""
        pass
    
    @abstractmethod
    async def extract_hero_products(self, url: str, html_content: str) -> OperationResult:
        """Extract featured/hero products from homepage"""
        pass

class IBrandContextExtractor(ABC):
    """Interface for brand context extraction"""
    
    @abstractmethod
    async def extract_brand_context(self, url: str, html_content: str) -> OperationResult:
        """Extract brand information and context"""
        pass

class IPolicyExtractor(ABC):
    """Interface for policy extraction"""
    
    @abstractmethod
    async def extract_policies(self, url: str, html_content: str) -> OperationResult:
        """Extract policy information and content"""
        pass

class IFAQExtractor(ABC):
    """Interface for FAQ extraction"""
    
    @abstractmethod
    async def extract_faqs(self, url: str, html_content: str) -> OperationResult:
        """Extract frequently asked questions"""
        pass

class ISocialMediaExtractor(ABC):
    """Interface for social media extraction"""
    
    @abstractmethod
    async def extract_social_handles(self, url: str, html_content: str) -> OperationResult:
        """Extract social media handles"""
        pass

class IContactExtractor(ABC):
    """Interface for contact information extraction"""
    
    @abstractmethod
    async def extract_contact_details(self, url: str, html_content: str) -> OperationResult:
        """Extract contact information"""
        pass

class ICurrencyDetector(ABC):
    """Interface for currency detection and conversion"""
    
    @abstractmethod
    async def detect_currency(self, url: str, html_content: str) -> OperationResult:
        """Detect the store's primary currency"""
        pass
    
    @abstractmethod
    async def convert_price(self, amount: float, from_currency: str, to_currency: str = "USD") -> OperationResult:
        """Convert price between currencies"""
        pass

class IContentValidator(ABC):
    """Interface for content validation"""
    
    @abstractmethod
    async def validate_content(self, content: Any, content_type: str, context: Dict[str, Any]) -> OperationResult:
        """Validate extracted content"""
        pass

class IAIValidator(ABC):
    """Interface for AI-powered validation"""
    
    @abstractmethod
    async def validate_with_ai(self, data: Any, validation_rules: Dict[str, Any]) -> OperationResult:
        """Validate data using AI"""
        pass
    
    @abstractmethod
    async def enhance_content(self, content: Any, enhancement_type: str) -> OperationResult:
        """Enhance content using AI"""
        pass

class ICompetitorAnalyzer(ABC):
    """Interface for competitor analysis"""
    
    @abstractmethod
    async def analyze_competitors(self, store_url: str, brand_context: BrandContext) -> OperationResult:
        """Analyze competitors for the given store"""
        pass

class IDataPersistence(ABC):
    """Interface for data persistence operations"""
    
    @abstractmethod
    async def save_insights(self, insights: Any) -> OperationResult:
        """Save brand insights to storage"""
        pass
    
    @abstractmethod
    async def get_insights(self, identifier: str) -> OperationResult:
        """Retrieve brand insights from storage"""
        pass
    
    @abstractmethod
    async def list_all_brands(self) -> OperationResult:
        """List all stored brands"""
        pass

class IHealthChecker(ABC):
    """Interface for health checking capabilities"""
    
    @abstractmethod
    async def check_health(self) -> OperationResult:
        """Check service health"""
        pass
    
    @abstractmethod
    async def check_dependencies(self) -> OperationResult:
        """Check health of dependencies"""
        pass

class IMetricsCollector(ABC):
    """Interface for metrics collection"""
    
    @abstractmethod
    async def record_extraction_time(self, operation: str, duration: float):
        """Record time taken for an operation"""
        pass
    
    @abstractmethod
    async def record_success_rate(self, operation: str, success: bool):
        """Record success/failure of an operation"""
        pass
    
    @abstractmethod
    async def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics"""
        pass

class INotificationService(ABC):
    """Interface for notification services"""
    
    @abstractmethod
    async def notify_extraction_complete(self, url: str, success: bool, details: Dict[str, Any]):
        """Notify when extraction is complete"""
        pass
    
    @abstractmethod
    async def notify_error(self, error: Exception, context: Dict[str, Any]):
        """Notify when an error occurs"""
        pass

class ICacheService(ABC):
    """Interface for caching services"""
    
    @abstractmethod
    async def get(self, key: str) -> OperationResult:
        """Get value from cache"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> OperationResult:
        """Set value in cache"""
        pass
    
    @abstractmethod
    async def invalidate(self, key: str) -> OperationResult:
        """Invalidate cache entry"""
        pass
    
    @abstractmethod
    async def clear_all(self) -> OperationResult:
        """Clear all cache entries"""
        pass

class IEmailExtractor(ABC):
    """Specialized interface for email extraction"""
    
    @abstractmethod
    async def extract_emails_from_text(self, text: str) -> List[str]:
        """Extract email addresses from text"""
        pass
    
    @abstractmethod
    async def validate_email(self, email: str) -> bool:
        """Validate email address format"""
        pass

class IPhoneExtractor(ABC):
    """Specialized interface for phone number extraction"""
    
    @abstractmethod
    async def extract_phones_from_text(self, text: str, country_hint: Optional[str] = None) -> List[str]:
        """Extract phone numbers from text"""
        pass
    
    @abstractmethod
    async def format_phone(self, phone: str, country_code: Optional[str] = None) -> str:
        """Format phone number consistently"""
        pass

class IURLExtractor(ABC):
    """Specialized interface for URL extraction"""
    
    @abstractmethod
    async def extract_social_urls(self, html_content: str, base_url: str) -> Dict[str, List[str]]:
        """Extract social media URLs"""
        pass
    
    @abstractmethod
    async def extract_policy_urls(self, html_content: str, base_url: str) -> Dict[str, str]:
        """Extract policy page URLs"""
        pass