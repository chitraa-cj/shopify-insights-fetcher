"""
Concrete implementations of extractors following SOLID principles.
Each extractor has a single responsibility and proper error handling.
"""

import re
import json
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import trafilatura

from models import Product, BrandContext, PolicyInfo, FAQ, SocialHandles, ContactDetails, ImportantLinks
from services.base import BaseExtractor, OperationResult, ExtractionResult, ValidationError, ExtractionError
from services.interfaces import (
    IProductExtractor, IBrandContextExtractor, IPolicyExtractor, IFAQExtractor,
    ISocialMediaExtractor, IContactExtractor, IEmailExtractor, IPhoneExtractor, IURLExtractor
)

class EmailExtractor(IEmailExtractor):
    """Utility class for email extraction with validation"""
    
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        re.IGNORECASE
    )
    
    EXCLUDED_DOMAINS = {
        'example.com', 'test.com', 'sample.com', 'placeholder.com',
        'yoursite.com', 'yourdomain.com', 'domain.com'
    }
    
    async def extract_emails_from_text(self, text: str) -> List[str]:
        """Extract valid email addresses from text"""
        if not text:
            return []
        
        emails = self.EMAIL_PATTERN.findall(text)
        validated_emails = []
        
        for email in emails:
            if await self.validate_email(email):
                validated_emails.append(email.lower())
        
        return list(set(validated_emails))  # Remove duplicates
    
    async def validate_email(self, email: str) -> bool:
        """Validate email address format and domain"""
        if not email or '@' not in email:
            return False
        
        domain = email.split('@')[1].lower()
        return domain not in self.EXCLUDED_DOMAINS

class PhoneExtractor(IPhoneExtractor):
    """Utility class for phone number extraction with formatting"""
    
    PHONE_PATTERNS = [
        re.compile(r'\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'),  # US format
        re.compile(r'\+?([0-9]{1,4})[-.\s]?([0-9]{1,4})[-.\s]?([0-9]{1,4})[-.\s]?([0-9]{1,4})'),  # International
        re.compile(r'\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})')  # Simple US
    ]
    
    async def extract_phones_from_text(self, text: str, country_hint: Optional[str] = None) -> List[str]:
        """Extract phone numbers from text"""
        if not text:
            return []
        
        phones = []
        for pattern in self.PHONE_PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    phone = ''.join(match)
                else:
                    phone = match
                
                # Basic validation - must have at least 10 digits
                digits_only = re.sub(r'\D', '', phone)
                if len(digits_only) >= 10:
                    formatted = await self.format_phone(phone, country_hint)
                    if formatted:
                        phones.append(formatted)
        
        return list(set(phones))
    
    async def format_phone(self, phone: str, country_code: Optional[str] = None) -> str:
        """Format phone number consistently"""
        digits = re.sub(r'\D', '', phone)
        
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits.startswith('1'):
            return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        elif len(digits) > 11:
            return f"+{digits}"
        
        return phone

class URLExtractor(IURLExtractor):
    """Utility class for URL extraction and categorization"""
    
    SOCIAL_DOMAINS = {
        'instagram.com': 'instagram',
        'facebook.com': 'facebook',
        'twitter.com': 'twitter',
        'x.com': 'twitter',
        'tiktok.com': 'tiktok',
        'youtube.com': 'youtube',
        'linkedin.com': 'linkedin',
        'pinterest.com': 'pinterest',
        'snapchat.com': 'snapchat'
    }
    
    POLICY_KEYWORDS = {
        'privacy': ['privacy', 'policy'],
        'terms': ['terms', 'service', 'conditions'],
        'return': ['return', 'returns'],
        'refund': ['refund', 'refunds'],
        'shipping': ['shipping', 'delivery']
    }
    
    async def extract_social_urls(self, html_content: str, base_url: str) -> Dict[str, List[str]]:
        """Extract social media URLs categorized by platform"""
        if not html_content:
            return {}
        
        social_urls = {platform: [] for platform in self.SOCIAL_DOMAINS.values()}
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all links
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Convert relative URLs to absolute
                if href.startswith('/'):
                    href = urljoin(base_url, href)
                
                # Check if URL belongs to a social platform
                parsed_url = urlparse(href)
                domain = parsed_url.netloc.lower()
                
                for social_domain, platform in self.SOCIAL_DOMAINS.items():
                    if social_domain in domain:
                        social_urls[platform].append(href)
                        break
            
            # Remove duplicates
            for platform in social_urls:
                social_urls[platform] = list(set(social_urls[platform]))
            
            return social_urls
            
        except Exception as e:
            raise ExtractionError(f"Failed to extract social URLs: {str(e)}")
    
    async def extract_policy_urls(self, html_content: str, base_url: str) -> Dict[str, str]:
        """Extract policy page URLs"""
        if not html_content:
            return {}
        
        policy_urls = {}
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            for link in soup.find_all('a', href=True):
                href = link['href'].lower()
                link_text = link.get_text().lower().strip()
                
                # Convert relative URLs to absolute
                if href.startswith('/'):
                    href = urljoin(base_url, href)
                
                # Check for policy keywords
                for policy_type, keywords in self.POLICY_KEYWORDS.items():
                    if any(keyword in href or keyword in link_text for keyword in keywords):
                        if policy_type not in policy_urls:  # Take first match
                            policy_urls[policy_type] = href
            
            return policy_urls
            
        except Exception as e:
            raise ExtractionError(f"Failed to extract policy URLs: {str(e)}")

class ProductExtractor(BaseExtractor, IProductExtractor):
    """Extracts product information from Shopify stores"""
    
    def __init__(self, network_handler, currency_detector=None):
        super().__init__(network_handler)
        self.currency_detector = currency_detector
        self.max_pages = 10
        self.products_per_page = 250
    
    async def extract_products(self, url: str, max_products: Optional[int] = None) -> OperationResult:
        """Extract products from Shopify products.json endpoint"""
        validation_result = self.validate_input(url)
        if not validation_result.is_success:
            return validation_result
        
        normalized_url = validation_result.data
        products = []
        errors = []
        
        try:
            page = 1
            total_fetched = 0
            
            while page <= self.max_pages:
                if max_products and total_fetched >= max_products:
                    break
                
                products_url = f"{normalized_url.rstrip('/')}/products.json"
                params = {'limit': self.products_per_page, 'page': page}
                
                response_result = self.network_handler.get(products_url, params=params)
                
                if not response_result.is_success:
                    if page == 1:  # Critical failure on first page
                        return OperationResult(
                            status=ExtractionResult.FAILURE,
                            error_message=f"Failed to fetch products: {response_result.error_message}"
                        )
                    else:  # Partial failure on subsequent pages
                        errors.append(f"Failed to fetch page {page}: {response_result.error_message}")
                        break
                
                try:
                    data = response_result.data.json()
                    page_products = data.get('products', [])
                    
                    if not page_products:
                        break  # No more products
                    
                    # Process products with error handling for each item
                    for product_data in page_products:
                        if max_products and total_fetched >= max_products:
                            break
                        
                        try:
                            product = await self._process_product_data(product_data, normalized_url)
                            if product:
                                products.append(product)
                                total_fetched += 1
                        except Exception as e:
                            errors.append(f"Failed to process product {product_data.get('id', 'unknown')}: {str(e)}")
                    
                    page += 1
                    
                except json.JSONDecodeError as e:
                    errors.append(f"Invalid JSON response on page {page}: {str(e)}")
                    break
                except Exception as e:
                    errors.append(f"Error processing page {page}: {str(e)}")
                    break
            
            # Determine result status
            if not products and errors:
                status = ExtractionResult.FAILURE
            elif errors:
                status = ExtractionResult.PARTIAL_SUCCESS
            else:
                status = ExtractionResult.SUCCESS
            
            return OperationResult(
                status=status,
                data=products,
                warnings=errors,
                metadata={
                    'total_products': len(products),
                    'pages_fetched': page - 1,
                    'errors_count': len(errors)
                }
            )
            
        except Exception as e:
            return self.handle_extraction_error(e, "Product extraction failed")
    
    async def extract_hero_products(self, url: str, html_content: str) -> OperationResult:
        """Extract featured/hero products from homepage"""
        if not html_content:
            return OperationResult(
                status=ExtractionResult.INVALID_INPUT,
                error_message="HTML content is required for hero product extraction"
            )
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            hero_products = []
            
            # Common selectors for hero/featured products
            hero_selectors = [
                '[data-product-id]',
                '.product-item',
                '.featured-product',
                '.hero-product',
                '[data-product]',
                '.product-card'
            ]
            
            for selector in hero_selectors:
                elements = soup.select(selector)
                if elements:
                    for element in elements[:10]:  # Limit to 10 hero products
                        try:
                            product = await self._extract_product_from_element(element, url)
                            if product:
                                hero_products.append(product)
                        except Exception as e:
                            self.logger.warning(f"Failed to extract hero product: {e}")
                    break  # Use first successful selector
            
            return OperationResult(
                status=ExtractionResult.SUCCESS if hero_products else ExtractionResult.PARTIAL_SUCCESS,
                data=hero_products,
                metadata={'hero_products_count': len(hero_products)}
            )
            
        except Exception as e:
            return self.handle_extraction_error(e, "Hero product extraction failed")
    
    async def _process_product_data(self, product_data: Dict[str, Any], base_url: str) -> Optional[Product]:
        """Process individual product data with error handling"""
        try:
            variants = product_data.get('variants', [])
            if not variants:
                return None
            
            # Get first variant for pricing
            first_variant = variants[0]
            price = float(first_variant.get('price', 0))
            
            # Extract images
            images = []
            if product_data.get('images'):
                images = [img.get('src', '') for img in product_data['images'] if img.get('src')]
            
            # Currency detection
            currency_info = await self._detect_product_currency(price, base_url)
            
            product = Product(
                title=product_data.get('title', '').strip(),
                price=price,
                vendor=product_data.get('vendor', '').strip(),
                product_type=product_data.get('product_type', '').strip(),
                images=images,
                url=f"{base_url.rstrip('/')}/products/{product_data.get('handle', '')}",
                availability=any(v.get('available', False) for v in variants),
                variants_count=len(variants),
                original_price=currency_info.get('original_price', price),
                currency=currency_info.get('currency', 'USD'),
                currency_symbol=currency_info.get('currency_symbol', '$'),
                price_usd=currency_info.get('price_usd', price),
                formatted_price=currency_info.get('formatted_price', f"${price}")
            )
            
            return product
            
        except Exception as e:
            self.logger.error(f"Error processing product data: {e}")
            return None
    
    async def _extract_product_from_element(self, element, base_url: str) -> Optional[Product]:
        """Extract product information from HTML element"""
        try:
            title_elem = element.find(['h1', 'h2', 'h3', 'h4', '.product-title', '[data-product-title]'])
            title = title_elem.get_text().strip() if title_elem else "Unknown Product"
            
            price_elem = element.find(['.price', '.product-price', '[data-price]'])
            price = 0.0
            if price_elem:
                price_text = re.sub(r'[^\d.,]', '', price_elem.get_text())
                try:
                    price = float(price_text.replace(',', ''))
                except ValueError:
                    pass
            
            img_elem = element.find('img')
            images = [img_elem['src']] if img_elem and img_elem.get('src') else []
            
            link_elem = element.find('a', href=True)
            product_url = urljoin(base_url, link_elem['href']) if link_elem else ""
            
            currency_info = await self._detect_product_currency(price, base_url)
            
            return Product(
                title=title,
                price=price,
                images=images,
                url=product_url,
                availability=True,  # Assume available if shown on homepage
                variants_count=1,
                original_price=currency_info.get('original_price', price),
                currency=currency_info.get('currency', 'USD'),
                currency_symbol=currency_info.get('currency_symbol', '$'),
                price_usd=currency_info.get('price_usd', price),
                formatted_price=currency_info.get('formatted_price', f"${price}")
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting product from element: {e}")
            return None
    
    async def _detect_product_currency(self, price: float, base_url: str) -> Dict[str, Any]:
        """Detect currency for product pricing"""
        default_currency = {
            'original_price': price,
            'currency': 'USD',
            'currency_symbol': '$',
            'price_usd': price,
            'formatted_price': f"${price:.2f}"
        }
        
        if self.currency_detector:
            try:
                # This would integrate with the currency detection service
                # For now, return default
                return default_currency
            except Exception:
                return default_currency
        
        return default_currency
    
    def extract(self, url: str, **kwargs) -> OperationResult:
        """Implementation of abstract method - delegates to async method"""
        return asyncio.create_task(self.extract_products(url, **kwargs))

class BrandContextExtractor(BaseExtractor, IBrandContextExtractor):
    """Extracts brand context and information"""
    
    async def extract_brand_context(self, url: str, html_content: str) -> OperationResult:
        """Extract brand information from homepage"""
        validation_result = self.validate_input(url)
        if not validation_result.is_success:
            return validation_result
        
        if not html_content:
            return OperationResult(
                status=ExtractionResult.INVALID_INPUT,
                error_message="HTML content is required for brand context extraction"
            )
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract brand name
            brand_name = await self._extract_brand_name(soup, url)
            
            # Extract brand description
            brand_description = await self._extract_brand_description(soup)
            
            # Extract about us content
            about_us_content = await self._extract_about_us_content(soup, url)
            
            brand_context = BrandContext(
                brand_name=brand_name,
                brand_description=brand_description,
                about_us_content=about_us_content
            )
            
            return OperationResult(
                status=ExtractionResult.SUCCESS,
                data=brand_context,
                metadata={
                    'has_brand_name': bool(brand_name),
                    'has_description': bool(brand_description),
                    'has_about_us': bool(about_us_content)
                }
            )
            
        except Exception as e:
            return self.handle_extraction_error(e, "Brand context extraction failed")
    
    async def _extract_brand_name(self, soup: BeautifulSoup, url: str) -> str:
        """Extract brand name using multiple strategies"""
        # Strategy 1: Page title
        title_elem = soup.find('title')
        if title_elem:
            title = title_elem.get_text().strip()
            # Clean common suffixes
            for suffix in [' - Shopify Store', ' | Shopify', ' Store', ' Shop']:
                if title.endswith(suffix):
                    title = title[:-len(suffix)].strip()
            if title and len(title) < 100:  # Reasonable brand name length
                return title
        
        # Strategy 2: Logo alt text
        logo_elem = soup.find('img', {'alt': re.compile(r'logo', re.I)})
        if logo_elem and logo_elem.get('alt'):
            alt_text = logo_elem['alt'].strip()
            if alt_text and len(alt_text) < 50:
                return alt_text
        
        # Strategy 3: Site name meta tag
        site_name = soup.find('meta', {'property': 'og:site_name'})
        if site_name and site_name.get('content'):
            return site_name['content'].strip()
        
        # Strategy 4: Extract from URL
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        if domain:
            # Remove common prefixes/suffixes
            domain = domain.replace('www.', '').replace('.myshopify.com', '').replace('.com', '')
            return domain.replace('-', ' ').replace('_', ' ').title()
        
        return ""
    
    async def _extract_brand_description(self, soup: BeautifulSoup) -> str:
        """Extract brand description from meta tags and content"""
        # Strategy 1: Meta description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            description = meta_desc['content'].strip()
            if description and len(description) > 20:
                return description
        
        # Strategy 2: OG description
        og_desc = soup.find('meta', {'property': 'og:description'})
        if og_desc and og_desc.get('content'):
            description = og_desc['content'].strip()
            if description and len(description) > 20:
                return description
        
        # Strategy 3: First paragraph in main content
        main_content = soup.find(['main', '.main-content', '.content', '.hero-content'])
        if main_content:
            first_p = main_content.find('p')
            if first_p:
                text = first_p.get_text().strip()
                if text and 50 < len(text) < 500:
                    return text
        
        return ""
    
    async def _extract_about_us_content(self, soup: BeautifulSoup, base_url: str) -> str:
        """Extract about us content from about page or homepage"""
        # Strategy 1: Find about us link and fetch content
        about_links = soup.find_all('a', href=True)
        for link in about_links:
            href = link['href'].lower()
            text = link.get_text().lower()
            
            if any(keyword in href or keyword in text for keyword in ['about', 'story', 'who-we-are']):
                about_url = urljoin(base_url, link['href'])
                try:
                    response_result = self.network_handler.get(about_url)
                    if response_result.is_success:
                        about_html = response_result.data.text
                        extracted_text = trafilatura.extract(about_html)
                        if extracted_text and len(extracted_text) > 100:
                            return extracted_text[:1000]  # Limit length
                except Exception:
                    continue
        
        # Strategy 2: Extract from homepage content sections
        content_sections = soup.find_all(['section', 'div'], class_=re.compile(r'about|story|intro', re.I))
        for section in content_sections:
            text = section.get_text().strip()
            if text and 100 < len(text) < 1000:
                return text
        
        return ""
    
    def extract(self, url: str, **kwargs) -> OperationResult:
        """Implementation of abstract method"""
        html_content = kwargs.get('html_content', '')
        return asyncio.create_task(self.extract_brand_context(url, html_content))

# Additional extractors would follow the same pattern...
# ContactExtractor, PolicyExtractor, FAQExtractor, SocialMediaExtractor
# Each implementing their respective interfaces with comprehensive error handling