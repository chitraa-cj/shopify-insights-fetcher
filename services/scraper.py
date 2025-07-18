import asyncio
import logging
from typing import List
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import trafilatura
from models import BrandInsights, BrandContext, PolicyInfo, SocialHandles, ContactDetails, ImportantLinks
from services.product_scraper import ProductScraperService
from services.content_scraper import ContentScraperService
from services.social_scraper import SocialScraperService
from services.ai_validator import AIValidatorService
from services.competitor_analyzer import CompetitorAnalyzer
from services.database_service import DatabaseService

logger = logging.getLogger(__name__)

class ShopifyScraperService:
    """Main service for orchestrating Shopify store scraping"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        self.product_scraper = ProductScraperService(self.session)
        self.content_scraper = ContentScraperService(self.session)
        self.social_scraper = SocialScraperService(self.session)
        self.ai_validator = AIValidatorService(self.session)
        self.competitor_analyzer = CompetitorAnalyzer()
        self.database_service = DatabaseService()
    
    async def extract_all_insights(self, url: str) -> BrandInsights:
        """
        Extract all insights from a Shopify store
        
        Args:
            url: The Shopify store URL
            
        Returns:
            BrandInsights: Complete brand insights
        """
        try:
            # Normalize URL
            url = self._normalize_url(url)
            
            # Verify the website is accessible and get HTML content for AI validation
            response = self.session.get(url, timeout=10)
            if response.status_code == 404:
                raise ValueError("Website not found")
            response.raise_for_status()
            
            # Store HTML content for AI validation
            html_content = response.text
            
            # Initialize insights object
            insights = BrandInsights(
                website_url=url,
                brand_context=BrandContext(),
                policies=PolicyInfo(),
                social_handles=SocialHandles(),
                contact_details=ContactDetails(),
                important_links=ImportantLinks()
            )
            
            # Run all extraction tasks concurrently
            tasks = [
                self._extract_products(url, insights, html_content),
                self._extract_brand_context(url, insights, html_content),
                self._extract_policies(url, insights, html_content),
                self._extract_faqs(url, insights, html_content),
                self._extract_social_handles(url, insights, html_content),
                self._extract_contact_details(url, insights, html_content),
                self._extract_important_links(url, insights)
            ]
            
            # Wait for all tasks to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Set total products found
            insights.total_products_found = len(insights.product_catalog)
            
            # Perform comprehensive AI validation
            try:
                insights.ai_validation = await self.ai_validator.comprehensive_validation(url, insights)
                logger.info(f"AI validation completed with confidence score: {insights.ai_validation.confidence_score}")
            except Exception as e:
                logger.error(f"Error in AI validation: {e}")
                insights.errors.append(f"AI validation error: {str(e)}")
            
            # Perform competitor analysis
            try:
                insights.competitor_analysis = await self.competitor_analyzer.analyze_competitors(url, insights)
                logger.info(f"Competitor analysis completed: found {insights.competitor_analysis.competitors_found} competitors")
            except Exception as e:
                logger.error(f"Error in competitor analysis: {e}")
                insights.errors.append(f"Competitor analysis error: {str(e)}")
            
            # Save to database
            try:
                await self.database_service.initialize()
                brand_id = await self.database_service.save_brand_insights(insights)
                if brand_id:
                    logger.info(f"Successfully saved insights to database with ID: {brand_id}")
                else:
                    logger.warning("Failed to save insights to database")
            except Exception as e:
                logger.error(f"Error saving to database: {e}")
                insights.errors.append(f"Database save error: {str(e)}")
            
            return insights
            
        except Exception as e:
            logger.error(f"Error extracting insights: {e}")
            raise
    
    def _normalize_url(self, url: str) -> str:
        """Normalize the URL to ensure it's properly formatted"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Remove trailing slashes
        url = url.rstrip('/')
        
        return url
    
    async def _extract_products(self, url: str, insights: BrandInsights, html_content: str = None):
        """Extract product catalog with currency detection and hero products"""
        try:
            # Extract product catalog with currency detection
            products, currency, currency_symbol = await self.product_scraper.get_product_catalog_with_currency(url, html_content)
            insights.product_catalog = products
            
            # Store currency information
            if currency:
                insights.detected_currency = currency
                insights.currency_symbol = currency_symbol
            
            # Extract hero products from homepage
            insights.hero_products = await self.product_scraper.get_hero_products(url)
            
        except Exception as e:
            logger.error(f"Error extracting products: {e}")
            insights.errors.append(f"Product extraction error: {str(e)}")
    
    async def _extract_brand_context(self, url: str, insights: BrandInsights, html_content: str):
        """Extract brand context and about information with AI validation"""
        try:
            # Extract initial brand context
            brand_context = await self.content_scraper.get_brand_context(url)
            
            # Validate and improve with AI
            insights.brand_context = await self.ai_validator.validate_brand_context(url, brand_context, html_content)
        except Exception as e:
            logger.error(f"Error extracting brand context: {e}")
            insights.errors.append(f"Brand context extraction error: {str(e)}")
    
    async def _extract_policies(self, url: str, insights: BrandInsights, html_content: str):
        """Extract policy information with AI validation"""
        try:
            # Extract initial policies
            policies = await self.content_scraper.get_policies(url)
            
            # Validate and improve with AI
            insights.policies = await self.ai_validator.validate_policies(url, policies, html_content)
        except Exception as e:
            logger.error(f"Error extracting policies: {e}")
            insights.errors.append(f"Policy extraction error: {str(e)}")
    
    async def _extract_faqs(self, url: str, insights: BrandInsights, html_content: str):
        """Extract FAQ information with AI validation"""
        try:
            # Extract initial FAQs
            faqs = await self.content_scraper.get_faqs(url)
            
            # Validate and improve with AI
            insights.faqs = await self.ai_validator.validate_faqs(url, faqs, html_content)
        except Exception as e:
            logger.error(f"Error extracting FAQs: {e}")
            insights.errors.append(f"FAQ extraction error: {str(e)}")
    
    async def _extract_social_handles(self, url: str, insights: BrandInsights, html_content: str):
        """Extract social media handles with AI validation"""
        try:
            # Extract initial social handles
            social_handles = await self.social_scraper.get_social_handles(url)
            
            # Validate and improve with AI
            insights.social_handles = await self.ai_validator.validate_social_handles(url, social_handles, html_content)
        except Exception as e:
            logger.error(f"Error extracting social handles: {e}")
            insights.errors.append(f"Social handles extraction error: {str(e)}")
    
    async def _extract_contact_details(self, url: str, insights: BrandInsights, html_content: str):
        """Extract contact details with AI validation"""
        try:
            # Extract initial contact details
            contact_details = await self.content_scraper.get_contact_details(url)
            
            # Validate and improve with AI
            insights.contact_details = await self.ai_validator.validate_contact_details(url, contact_details, html_content)
        except Exception as e:
            logger.error(f"Error extracting contact details: {e}")
            insights.errors.append(f"Contact details extraction error: {str(e)}")
    
    async def _extract_important_links(self, url: str, insights: BrandInsights):
        """Extract important links"""
        try:
            insights.important_links = await self.content_scraper.get_important_links(url)
        except Exception as e:
            logger.error(f"Error extracting important links: {e}")
            insights.errors.append(f"Important links extraction error: {str(e)}")
