import asyncio
import logging
import json
from typing import List, Tuple
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from models import Product
from services.currency_service import CurrencyService

logger = logging.getLogger(__name__)

class ProductScraperService:
    """Service for scraping product information from Shopify stores"""
    
    def __init__(self, session: requests.Session):
        self.session = session
        self.currency_service = CurrencyService()
    
    async def get_product_catalog_with_currency(self, base_url: str, html_content: str = None) -> Tuple[List[Product], str, str]:
        """
        Extract complete product catalog with currency detection
        
        Args:
            base_url: The base URL of the Shopify store
            html_content: HTML content for currency detection
            
        Returns:
            Tuple[List[Product], str, str]: Products list, currency code, currency symbol
        """
        all_products_data = []
        products = []
        page = 1
        limit = 250  # Maximum allowed by Shopify
        
        try:
            # First, collect all raw product data
            while True:
                products_url = f"{base_url}/products.json?limit={limit}&page={page}"
                logger.info(f"Fetching products from: {products_url}")
                
                response = self.session.get(products_url, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                if not data.get('products'):
                    break
                
                all_products_data.extend(data['products'])
                
                # Break if we got fewer products than requested (last page)
                if len(data['products']) < limit:
                    break
                    
                page += 1
            
            logger.info(f"Found {len(all_products_data)} products in catalog")
            
            # Get HTML content if not provided
            if not html_content:
                try:
                    response = self.session.get(base_url, timeout=10)
                    html_content = response.text
                except Exception as e:
                    logger.warning(f"Could not fetch HTML for currency detection: {e}")
                    html_content = ""
            
            # Detect currency and process products
            detected_currency, currency_symbol, processed_products_data = self.currency_service.detect_and_convert_product_prices(
                all_products_data, html_content, base_url
            )
            
            # Convert to Product objects
            for product_data in processed_products_data:
                product = self._parse_product_json(product_data, base_url)
                if product:
                    # Add currency information to product
                    product.currency = detected_currency
                    product.currency_symbol = currency_symbol
                    products.append(product)
            
            return products, detected_currency, currency_symbol
            
        except Exception as e:
            logger.error(f"Error fetching product catalog: {e}")
            return [], "USD", "$"
    
    async def get_product_catalog(self, base_url: str) -> List[Product]:
        """Backward compatibility method for getting products without currency"""
        products, _, _ = await self.get_product_catalog_with_currency(base_url)
        return products
    
    async def get_hero_products(self, base_url: str) -> List[Product]:
        """
        Extract hero products from the homepage
        
        Args:
            base_url: The base URL of the Shopify store
            
        Returns:
            List[Product]: List of hero products
        """
        try:
            response = self.session.get(base_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            hero_products = []
            
            # Look for product links on the homepage
            product_selectors = [
                'a[href*="/products/"]',
                '.product-item a',
                '.product-card a',
                '.featured-product a',
                '.hero-product a'
            ]
            
            product_urls = set()
            
            for selector in product_selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if href and '/products/' in href:
                        full_url = urljoin(base_url, href)
                        product_urls.add(full_url)
            
            # Limit to first 10 hero products to avoid overloading
            for url in list(product_urls)[:10]:
                try:
                    product = await self._get_product_from_url(url, base_url)
                    if product:
                        hero_products.append(product)
                    await asyncio.sleep(0.1)  # Be respectful
                except Exception as e:
                    logger.warning(f"Error fetching hero product from {url}: {e}")
                    continue
            
            logger.info(f"Found {len(hero_products)} hero products")
            return hero_products
            
        except Exception as e:
            logger.error(f"Error fetching hero products: {e}")
            return []
    
    async def _get_product_from_url(self, product_url: str, base_url: str) -> Product:
        """
        Get product information from a product page URL
        
        Args:
            product_url: The full URL to the product page
            base_url: The base URL of the store
            
        Returns:
            Product: Product information or None if failed
        """
        try:
            # Try to get product data from JSON endpoint
            handle = product_url.split('/products/')[-1].split('?')[0]
            json_url = f"{base_url}/products/{handle}.json"
            
            response = self.session.get(json_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'product' in data:
                    return self._parse_product_json(data['product'], base_url)
            
            # Fallback to scraping the HTML page
            response = self.session.get(product_url, timeout=5)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract basic product info from HTML
            title_elem = soup.find('h1') or soup.find('.product-title') or soup.find('[data-product-title]')
            title = title_elem.get_text(strip=True) if title_elem else "Unknown Product"
            
            price_elem = soup.find('.price') or soup.find('[data-price]') or soup.find('.product-price')
            price = price_elem.get_text(strip=True) if price_elem else None
            
            return Product(
                title=title,
                handle=handle,
                price=price,
                url=product_url
            )
            
        except Exception as e:
            logger.warning(f"Error getting product from {product_url}: {e}")
            return None
    
    def _parse_product_json(self, product_data: dict, base_url: str) -> Product:
        """
        Parse product data from Shopify JSON API response
        
        Args:
            product_data: Product data from JSON API
            base_url: Base URL of the store
            
        Returns:
            Product: Parsed product information
        """
        try:
            # Extract images
            images = []
            if product_data.get('images'):
                images = [img.get('src', '') for img in product_data['images']]
            
            # Extract price from variants
            price = None
            compare_at_price = None
            available = False
            
            if product_data.get('variants'):
                variant = product_data['variants'][0]  # Use first variant
                price = variant.get('price')
                compare_at_price = variant.get('compare_at_price')
                available = variant.get('available', False)
            
            # Build product URL
            handle = product_data.get('handle', '')
            product_url = f"{base_url}/products/{handle}" if handle else None
            
            return Product(
                id=str(product_data.get('id', '')),
                title=product_data.get('title', ''),
                handle=handle,
                description=product_data.get('body_html', ''),
                price=price,
                compare_at_price=compare_at_price,
                vendor=product_data.get('vendor', ''),
                product_type=product_data.get('product_type', ''),
                tags=self._parse_tags(product_data.get('tags', [])),
                images=images,
                url=product_url,
                available=available
            )
            
        except Exception as e:
            logger.error(f"Error parsing product JSON: {e}")
            return Product(title="Unknown Product")
    
    def _parse_tags(self, tags_data):
        """Parse tags data which can be either string or list"""
        if isinstance(tags_data, str):
            # Split by comma and clean up
            return [tag.strip() for tag in tags_data.split(',') if tag.strip()]
        elif isinstance(tags_data, list):
            return tags_data
        else:
            return []
