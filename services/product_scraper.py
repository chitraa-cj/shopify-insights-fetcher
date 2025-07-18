import asyncio
import logging
import json
from typing import List
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from models import Product

logger = logging.getLogger(__name__)

class ProductScraperService:
    """Service for scraping product information from Shopify stores"""
    
    def __init__(self, session: requests.Session):
        self.session = session
    
    async def get_product_catalog(self, base_url: str) -> List[Product]:
        """
        Extract complete product catalog from /products.json
        
        Args:
            base_url: The base URL of the Shopify store
            
        Returns:
            List[Product]: List of all products
        """
        products = []
        page = 1
        limit = 250  # Maximum allowed by Shopify
        
        try:
            while True:
                products_url = f"{base_url}/products.json?limit={limit}&page={page}"
                logger.info(f"Fetching products from: {products_url}")
                
                response = self.session.get(products_url, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                if not data.get('products'):
                    break
                
                for product_data in data['products']:
                    product = self._parse_product_json(product_data, base_url)
                    products.append(product)
                
                # If we got fewer products than the limit, we've reached the end
                if len(data['products']) < limit:
                    break
                
                page += 1
                
                # Add a small delay to be respectful
                await asyncio.sleep(0.1)
            
            logger.info(f"Found {len(products)} products in catalog")
            return products
            
        except Exception as e:
            logger.error(f"Error fetching product catalog: {e}")
            return []
    
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
                tags=product_data.get('tags', []),
                images=images,
                url=product_url,
                available=available
            )
            
        except Exception as e:
            logger.error(f"Error parsing product JSON: {e}")
            return Product(title="Unknown Product")
