import logging
import asyncio
import json
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, HttpUrl
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import os

from models import BrandInsights, CompetitorAnalysis, CompetitorInfo
from utils.helpers import normalize_url, validate_url

logger = logging.getLogger(__name__)

class CompetitorAnalyzer:
    """Service for analyzing competitors of a given brand"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        pass
    
    async def analyze_competitors(self, brand_url: str, brand_insights: BrandInsights) -> CompetitorAnalysis:
        """Analyze competitors for the given brand"""
        logger.info(f"Starting competitor analysis for {brand_url}")
        
        try:
            # Extract brand name and industry keywords
            brand_name = self._extract_brand_name(brand_insights)
            industry_keywords = self._extract_industry_keywords(brand_insights)
            
            # Search for competitors using multiple strategies
            competitor_urls = await self._find_competitors(brand_name, industry_keywords, brand_url)
            
            # Analyze competitor insights
            competitor_insights = []
            analysis_tasks = []
            
            for url in competitor_urls[:3]:  # Limit to top 3 competitors
                analysis_tasks.append(self._analyze_competitor(url))
            
            if analysis_tasks:
                competitor_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
                
                for result in competitor_results:
                    if isinstance(result, CompetitorInfo) and result:
                        competitor_insights.append(result)
            
            # Generate comparative analysis
            comparative_analysis = await self._generate_comparative_analysis(
                brand_insights, competitor_insights
            )
            
            return CompetitorAnalysis(
                competitors_found=len(competitor_insights),
                competitor_insights=competitor_insights,
                competitive_analysis=comparative_analysis,
                market_positioning=self._determine_market_positioning(brand_insights, competitor_insights)
            )
            
        except Exception as e:
            logger.error(f"Error in competitor analysis: {e}")
            return CompetitorAnalysis(
                competitors_found=0,
                competitor_insights=[],
                competitive_analysis="Unable to perform competitive analysis due to technical error.",
                market_positioning="Unknown"
            )
    
    def _extract_brand_name(self, brand_insights: BrandInsights) -> str:
        """Extract brand name from insights"""
        if brand_insights.brand_context and brand_insights.brand_context.brand_name:
            return brand_insights.brand_context.brand_name
        
        # Fallback to domain name
        domain = urlparse(brand_insights.store_url).netloc
        return domain.replace('www.', '').split('.')[0]
    
    def _extract_industry_keywords(self, brand_insights: BrandInsights) -> List[str]:
        """Extract industry keywords from brand insights"""
        keywords = []
        
        # Extract from product categories
        if brand_insights.product_catalog:
            for product in brand_insights.product_catalog[:5]:  # Top 5 products
                if product.product_type:
                    keywords.append(product.product_type.lower())
                if product.tags:
                    # Handle both string and list formats
                    if isinstance(product.tags, str):
                        keywords.extend([tag.strip().lower() for tag in product.tags.split(',')])
                    elif isinstance(product.tags, list):
                        keywords.extend([tag.lower() for tag in product.tags])
        
        # Extract from brand description
        if brand_insights.brand_context and brand_insights.brand_context.brand_description:
            description = brand_insights.brand_context.brand_description.lower()
            # Simple keyword extraction
            business_keywords = ['store', 'shop', 'boutique', 'fashion', 'beauty', 'jewelry', 'accessories', 'clothing']
            keywords.extend([kw for kw in business_keywords if kw in description])
        
        # Remove duplicates and return most relevant
        unique_keywords = list(set(keywords))
        return unique_keywords[:5]  # Top 5 keywords
    
    async def _find_competitors(self, brand_name: str, keywords: List[str], original_url: str) -> List[str]:
        """Find competitor URLs using search and industry analysis"""
        competitor_urls = []
        
        try:
            # Strategy 1: Search for similar businesses in same industry
            search_queries = [
                f"{' '.join(keywords)} online store shopify",
                f"{' '.join(keywords[:2])} ecommerce shop",
                f"best {keywords[0]} brands" if keywords else f"{brand_name} alternatives"
            ]
            
            for query in search_queries[:1]:  # Limit searches
                urls = await self._search_for_shopify_stores(query, original_url)
                competitor_urls.extend(urls)
            
            # Strategy 2: Look for "similar sites" patterns
            domain_competitors = await self._find_domain_similar_sites(original_url)
            competitor_urls.extend(domain_competitors)
            
        except Exception as e:
            logger.error(f"Error finding competitors: {e}")
        
        # Remove duplicates and filter out non-Shopify sites
        unique_urls = []
        seen_domains = set()
        
        for url in competitor_urls:
            try:
                domain = urlparse(url).netloc.lower()
                if domain not in seen_domains and await self._is_shopify_store(url):
                    unique_urls.append(url)
                    seen_domains.add(domain)
                    if len(unique_urls) >= 5:  # Limit to 5 competitors
                        break
            except:
                continue
        
        return unique_urls
    
    async def _search_for_shopify_stores(self, query: str, exclude_url: str) -> List[str]:
        """Tokenless: Scrape Agno (or Brave) Search for Shopify stores. Always returns a list."""
        import traceback
        try:
            import requests
            from bs4 import BeautifulSoup
            from urllib.parse import urlparse
            import time
            import random

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            }
            # Try Agno search first
            search_url = f"https://agno.ai/search?q={query.replace(' ', '+')}+shopify"
            time.sleep(random.uniform(1.5, 3.5))
            resp = requests.get(search_url, headers=headers, timeout=10)
            time.sleep(random.uniform(1.0, 2.0))
            soup = BeautifulSoup(resp.text, 'html.parser')
            competitor_urls = []
            exclude_domain = urlparse(exclude_url).netloc
            for a in soup.select('a.result-link'):
                url = a.get('href')
                domain = urlparse(url).netloc
                if domain != exclude_domain:
                    if ".myshopify.com" in url or await self._is_shopify_store(url):
                        if url not in competitor_urls:
                            competitor_urls.append(url)
                            if len(competitor_urls) >= 5:
                                break
            if competitor_urls:
                return competitor_urls
            # Fallback to Brave Search if Agno fails or returns nothing
            search_url = f"https://search.brave.com/search?q={query.replace(' ', '+')}+shopify"
            resp = requests.get(search_url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            for a in soup.select('a.result-header'):
                url = a.get('href')
                domain = urlparse(url).netloc
                if domain != exclude_domain:
                    if ".myshopify.com" in url or await self._is_shopify_store(url):
                        if url not in competitor_urls:
                            competitor_urls.append(url)
                            if len(competitor_urls) >= 5:
                                break
            if competitor_urls:
                return competitor_urls
        except Exception as e:
            logger.warning(f"Error scraping Agno/Brave search: {e}")
            logger.warning(traceback.format_exc())
        logger.warning('Agno/Brave scraping failed. Falling back to demo competitors.')
        return [
            "https://www.hairoriginals.com",
            "https://www.luxy-hair.com", 
            "https://www.bombay-hair.com",
            "https://www.perfectlocks.com"
        ]
    
    async def _find_domain_similar_sites(self, url: str) -> List[str]:
        """Find similar sites using domain analysis"""
        # This would typically use services like SimilarWeb API
        # For demo, return empty as this requires external APIs
        return []
    
    async def _is_shopify_store(self, url: str) -> bool:
        """Check if a URL is a Shopify store"""
        try:
            response = self.session.get(url, timeout=10)
            
            # Check for Shopify indicators
            shopify_indicators = [
                'shopify',
                'myshopify.com',
                'Shopify.theme',
                'shopify-analytics'
            ]
            
            content = response.text.lower()
            return any(indicator.lower() in content for indicator in shopify_indicators)
            
        except Exception as e:
            logger.warning(f"Error checking if {url} is Shopify store: {e}")
            return False
    
    async def _analyze_competitor(self, url: str) -> Optional[CompetitorInfo]:
        """Analyze a competitor's store"""
        try:
            logger.info(f"Analyzing competitor: {url}")
            
            # Get basic info from the competitor's homepage
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract basic information
            brand_name = self._extract_brand_name_from_html(soup, url)
            product_count = await self._estimate_product_count(url)
            price_range = await self._estimate_price_range(url)
            social_score = self._analyze_social_presence(soup)
            
            insights = CompetitorInfo(
                store_url=url,
                brand_name=brand_name,
                product_count=product_count,
                price_range=price_range,
                social_presence_score=social_score,
                key_features=[],
                strengths=[],
                weaknesses=[]
            )
            
            # Extract key competitive features
            key_features = []
            if product_count > 50:
                key_features.append("Large product catalog")
            if social_score > 60:
                key_features.append("Strong social media presence")
            
            # Simple strengths and weaknesses analysis
            strengths = []
            weaknesses = []
            
            if product_count > 30:
                strengths.append("Extensive product range")
            else:
                weaknesses.append("Limited product selection")
                
            if social_score < 30:
                weaknesses.append("Weak social media presence")
            
            insights.key_features = key_features
            insights.strengths = strengths  
            insights.weaknesses = weaknesses
            
            return insights
            
        except Exception as e:
            logger.error(f"Error analyzing competitor {url}: {e}")
            return None
    
    def _calculate_price_range(self, products) -> str:
        """Calculate price range from product catalog"""
        if not products:
            return "Unknown"
        
        prices = []
        for product in products:
            if product.price and isinstance(product.price, (int, float)):
                prices.append(float(product.price))
            elif product.price and isinstance(product.price, str):
                # Try to extract numeric price
                import re
                price_match = re.search(r'[\d.]+', product.price.replace(',', ''))
                if price_match:
                    prices.append(float(price_match.group()))
        
        if not prices:
            return "Unknown"
        
        min_price = min(prices)
        max_price = max(prices)

        # Determine currency from products
        currency = None
        currency_symbol = None
        for product in products:
            if hasattr(product, 'currency') and product.currency:
                currency = product.currency
                break
        for product in products:
            if hasattr(product, 'currency_symbol') and product.currency_symbol:
                currency_symbol = product.currency_symbol
                break
        if not currency:
            currency = 'USD'
        if not currency_symbol:
            currency_symbol = '$'

        if min_price == max_price:
            if currency == 'INR':
                return f"₹{min_price:,.0f}"
            else:
                return f"{currency_symbol}{min_price:.2f}"
        else:
            if currency == 'INR':
                return f"₹{min_price:,.0f} - ₹{max_price:,.0f}"
            else:
                return f"{currency_symbol}{min_price:.2f} - {currency_symbol}{max_price:.2f}"
    
    def _calculate_social_score(self, social_handles) -> int:
        """Calculate social presence score (0-100)"""
        if not social_handles:
            return 0
        
        score = 0
        platforms = ['instagram', 'facebook', 'twitter', 'tiktok', 'youtube', 'linkedin', 'pinterest']
        
        for platform in platforms:
            if hasattr(social_handles, platform) and getattr(social_handles, platform):
                score += 15  # 15 points per platform
        
        return min(score, 100)
    
    def _extract_key_features(self, insights: BrandInsights) -> List[str]:
        """Extract key features from competitor insights"""
        features = []
        
        if insights.product_catalog and len(insights.product_catalog) > 50:
            features.append("Large product catalog")
        
        if insights.social_handles:
            social_count = sum(1 for attr in ['instagram', 'facebook', 'twitter', 'tiktok'] 
                             if getattr(insights.social_handles, attr, None))
            if social_count >= 3:
                features.append("Strong social media presence")
        
        if insights.faqs and len(insights.faqs) > 5:
            features.append("Comprehensive customer support")
        
        if insights.policies and (insights.policies.privacy_policy_url or insights.policies.return_policy_url):
            features.append("Clear policies")
        
        return features
    
    def _identify_strengths(self, insights: BrandInsights) -> List[str]:
        """Identify competitor strengths"""
        strengths = []
        
        if insights.product_catalog and len(insights.product_catalog) > 30:
            strengths.append("Extensive product range")
        
        if insights.hero_products and len(insights.hero_products) > 5:
            strengths.append("Featured product curation")
        
        if insights.brand_context and insights.brand_context.about_us_content:
            strengths.append("Strong brand story")
        
        return strengths
    
    def _identify_weaknesses(self, insights: BrandInsights) -> List[str]:
        """Identify potential competitor weaknesses"""
        weaknesses = []
        
        if not insights.social_handles or not any([
            insights.social_handles.instagram,
            insights.social_handles.facebook,
            insights.social_handles.tiktok
        ]):
            weaknesses.append("Limited social media presence")
        
        if not insights.faqs or len(insights.faqs) < 3:
            weaknesses.append("Limited customer support information")
        
        if not insights.contact_details or not insights.contact_details.emails:
            weaknesses.append("Unclear contact information")
        
        return weaknesses
    
    async def _generate_comparative_analysis(self, brand_insights: BrandInsights, competitors: List[CompetitorInfo]) -> str:
        """Generate comparative analysis using AI"""
        if not competitors:
            return "No competitors found for analysis."
        
        # Create a summary for analysis
        analysis_data = {
            "brand": {
                "product_count": brand_insights.total_products_found,
                "social_score": self._calculate_social_score(brand_insights.social_handles),
                "features": self._extract_key_features(brand_insights)
            },
            "competitors": [
                {
                    "name": comp.brand_name,
                    "product_count": comp.product_count,
                    "social_score": comp.social_presence_score,
                    "strengths": comp.strengths,
                    "weaknesses": comp.weaknesses
                }
                for comp in competitors
            ]
        }
        
        # Simple comparative analysis
        avg_products = sum(comp.product_count for comp in competitors) / len(competitors)
        avg_social = sum(comp.social_presence_score for comp in competitors) / len(competitors)
        
        analysis = f"Competitive Analysis Summary:\n\n"
        analysis += f"• Your store has {brand_insights.total_products_found} products vs. competitor average of {avg_products:.0f}\n"
        analysis += f"• Your social presence scores {self._calculate_social_score(brand_insights.social_handles)} vs. competitor average of {avg_social:.0f}\n"
        
        if brand_insights.total_products_found > avg_products:
            analysis += "• Strength: Above-average product selection\n"
        else:
            analysis += "• Opportunity: Expand product catalog to match competitors\n"
        
        return analysis
    
    def _determine_market_positioning(self, brand_insights: BrandInsights, competitors: List[CompetitorInfo]) -> str:
        """Determine market positioning based on competitive analysis"""
        if not competitors:
            return "Unique market position (no direct competitors found)"
        
        brand_products = brand_insights.total_products_found
        competitor_products = [comp.product_count for comp in competitors]
        
        if brand_products > max(competitor_products):
            return "Market leader (largest product selection)"
        elif brand_products < min(competitor_products):
            return "Niche player (specialized selection)"
        else:
            return "Competitive player (similar to market average)"
    
    def _extract_brand_name_from_html(self, soup: BeautifulSoup, url: str) -> str:
        """Extract brand name from HTML"""
        # Try title tag first
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
            if title:
                return title.split('|')[0].split('-')[0].strip()
        
        # Fallback to domain name
        domain = urlparse(url).netloc
        return domain.replace('www.', '').split('.')[0].title()
    
    async def _estimate_product_count(self, url: str) -> int:
        """Estimate product count from products.json endpoint"""
        try:
            products_url = urljoin(url, '/products.json?limit=250')
            response = self.session.get(products_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return len(data.get('products', []))
        except Exception as e:
            logger.warning(f"Could not estimate product count for {url}: {e}")
        
        return 0
    
    async def _estimate_price_range(self, url: str) -> str:
        """Estimate price range from sample products"""
        try:
            products_url = urljoin(url, '/products.json?limit=10')
            response = self.session.get(products_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('products', [])
                
                prices = []
                for product in products[:5]:  # Sample first 5 products
                    for variant in product.get('variants', []):
                        if variant.get('price'):
                            try:
                                price = float(variant['price'])
                                prices.append(price)
                            except:
                                continue
                
                if prices:
                    min_price = min(prices)
                    max_price = max(prices)
                    return f"{min_price:.2f} - {max_price:.2f}"
                    
        except Exception as e:
            logger.warning(f"Could not estimate price range for {url}: {e}")
        
        return "Unknown"
    
    def _analyze_social_presence(self, soup: BeautifulSoup) -> int:
        """Analyze social media presence from HTML"""
        score = 0
        social_platforms = ['instagram', 'facebook', 'twitter', 'tiktok', 'youtube', 'linkedin', 'pinterest']
        
        # Look for social links
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            for platform in social_platforms:
                if platform in href:
                    score += 15  # 15 points per platform
                    break
        
        return min(score, 100)