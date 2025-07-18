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
            
            # Verify the website is accessible
            response = self.session.get(url, timeout=10)
            if response.status_code == 404:
                raise ValueError("Website not found")
            response.raise_for_status()
            
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
                self._extract_products(url, insights),
                self._extract_brand_context(url, insights),
                self._extract_policies(url, insights),
                self._extract_faqs(url, insights),
                self._extract_social_handles(url, insights),
                self._extract_contact_details(url, insights),
                self._extract_important_links(url, insights)
            ]
            
            # Wait for all tasks to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Set total products found
            insights.total_products_found = len(insights.product_catalog)
            
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
    
    async def _extract_products(self, url: str, insights: BrandInsights):
        """Extract product catalog and hero products"""
        try:
            # Extract product catalog
            insights.product_catalog = await self.product_scraper.get_product_catalog(url)
            
            # Extract hero products from homepage
            insights.hero_products = await self.product_scraper.get_hero_products(url)
            
        except Exception as e:
            logger.error(f"Error extracting products: {e}")
            insights.errors.append(f"Product extraction error: {str(e)}")
    
    async def _extract_brand_context(self, url: str, insights: BrandInsights):
        """Extract brand context and about information"""
        try:
            insights.brand_context = await self.content_scraper.get_brand_context(url)
        except Exception as e:
            logger.error(f"Error extracting brand context: {e}")
            insights.errors.append(f"Brand context extraction error: {str(e)}")
    
    async def _extract_policies(self, url: str, insights: BrandInsights):
        """Extract policy information"""
        try:
            insights.policies = await self.content_scraper.get_policies(url)
        except Exception as e:
            logger.error(f"Error extracting policies: {e}")
            insights.errors.append(f"Policy extraction error: {str(e)}")
    
    async def _extract_faqs(self, url: str, insights: BrandInsights):
        """Extract FAQ information"""
        try:
            insights.faqs = await self.content_scraper.get_faqs(url)
        except Exception as e:
            logger.error(f"Error extracting FAQs: {e}")
            insights.errors.append(f"FAQ extraction error: {str(e)}")
    
    async def _extract_social_handles(self, url: str, insights: BrandInsights):
        """Extract social media handles"""
        try:
            insights.social_handles = await self.social_scraper.get_social_handles(url)
        except Exception as e:
            logger.error(f"Error extracting social handles: {e}")
            insights.errors.append(f"Social handles extraction error: {str(e)}")
    
    async def _extract_contact_details(self, url: str, insights: BrandInsights):
        """Extract contact details"""
        try:
            insights.contact_details = await self.content_scraper.get_contact_details(url)
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
