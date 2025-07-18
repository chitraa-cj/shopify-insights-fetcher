from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Product(BaseModel):
    """Model for individual product information"""
    id: Optional[str] = None
    title: str
    handle: Optional[str] = None
    description: Optional[str] = None
    price: Optional[str] = None
    price_usd: Optional[float] = None
    original_price: Optional[float] = None
    formatted_price: Optional[str] = None
    formatted_price_usd: Optional[str] = None
    compare_at_price: Optional[str] = None
    vendor: Optional[str] = None
    product_type: Optional[str] = None
    tags: List[str] = []
    images: List[str] = []
    url: Optional[str] = None
    available: Optional[bool] = None
    currency: Optional[str] = None
    currency_symbol: Optional[str] = None

class FAQ(BaseModel):
    """Model for FAQ items"""
    question: str
    answer: str

class SocialHandles(BaseModel):
    """Model for social media handles"""
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    tiktok: Optional[str] = None
    twitter: Optional[str] = None
    youtube: Optional[str] = None
    linkedin: Optional[str] = None
    pinterest: Optional[str] = None

class ContactDetails(BaseModel):
    """Model for contact information"""
    emails: List[str] = []
    phone_numbers: List[str] = []
    address: Optional[str] = None

class ImportantLinks(BaseModel):
    """Model for important website links"""
    order_tracking: Optional[str] = None
    contact_us: Optional[str] = None
    blogs: Optional[str] = None
    size_guide: Optional[str] = None
    shipping_info: Optional[str] = None
    about_us: Optional[str] = None
    careers: Optional[str] = None

class PolicyInfo(BaseModel):
    """Model for policy information"""
    privacy_policy_url: Optional[str] = None
    privacy_policy_content: Optional[str] = None
    return_policy_url: Optional[str] = None
    return_policy_content: Optional[str] = None
    refund_policy_url: Optional[str] = None
    refund_policy_content: Optional[str] = None
    terms_of_service_url: Optional[str] = None
    terms_of_service_content: Optional[str] = None

class BrandContext(BaseModel):
    """Model for brand context and about information"""
    brand_name: Optional[str] = None
    brand_description: Optional[str] = None
    about_us_content: Optional[str] = None
    mission_statement: Optional[str] = None
    brand_story: Optional[str] = None

class AIValidationResult(BaseModel):
    """Model for AI validation metadata"""
    validated: bool = False
    confidence_score: float = 0.0
    validation_notes: List[str] = []

class CompetitorInfo(BaseModel):
    """Model for individual competitor information"""
    store_url: str
    brand_name: str
    product_count: int
    price_range: str
    social_presence_score: int  # 0-100
    key_features: List[str] = []
    strengths: List[str] = []
    weaknesses: List[str] = []

class CompetitorAnalysis(BaseModel):
    """Model for competitive analysis results"""
    competitors_found: int
    competitor_insights: List[CompetitorInfo] = []
    competitive_analysis: str
    market_positioning: str

class BrandInsights(BaseModel):
    """Main model containing all brand insights"""
    website_url: str
    brand_context: BrandContext
    product_catalog: List[Product] = []
    hero_products: List[Product] = []
    policies: PolicyInfo
    faqs: List[FAQ] = []
    social_handles: SocialHandles
    contact_details: ContactDetails
    important_links: ImportantLinks
    extraction_timestamp: datetime = Field(default_factory=datetime.now)
    total_products_found: int = 0
    extraction_success: bool = True
    errors: List[str] = []
    competitor_analysis: Optional[CompetitorAnalysis] = None
    ai_validation: AIValidationResult = Field(default_factory=AIValidationResult)
    detected_currency: Optional[str] = None
    currency_symbol: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
