import logging
import re
import requests
from typing import Optional, Dict, Tuple
from bs4 import BeautifulSoup
import json

logger = logging.getLogger(__name__)

class CurrencyService:
    """Service for detecting and converting currencies"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Currency symbols and codes mapping
        self.currency_symbols = {
            'USD': '$',
            'INR': '₹', 
            'EUR': '€',
            'GBP': '£',
            'JPY': '¥',
            'RUB': '₽',
            'CAD': 'C$',
            'AUD': 'A$',
            'SEK': 'kr',
            'PLN': 'zł',
            'BRL': 'R$',
            'KRW': '₩'
        }
        
        # Exchange rates cache (in production, use a real API)
        self.exchange_rates = {
            'INR': {'USD': 0.012, 'EUR': 0.011, 'GBP': 0.0095},
            'USD': {'INR': 83.25, 'EUR': 0.92, 'GBP': 0.79},
            'EUR': {'USD': 1.09, 'INR': 90.85, 'GBP': 0.86},
            'GBP': {'USD': 1.27, 'INR': 105.50, 'EUR': 1.16}
        }
    
    def detect_currency_from_products(self, products_data: list) -> Tuple[str, str]:
        """Detect currency from product pricing data"""
        if not products_data:
            return 'USD', '$'
        
        # Look at first few products for currency indicators
        for product in products_data[:5]:
            variants = product.get('variants', [])
            for variant in variants:
                price_str = str(variant.get('price', ''))
                if price_str:
                    # Check for currency symbols in price
                    for symbol, code in self.currency_symbols.items():
                        if symbol in price_str or symbol in str(variant.get('compare_at_price', '')):
                            return code, symbol
        
        return 'USD', '$'  # Default fallback
    
    def detect_currency_from_html(self, html_content: str, url: str) -> Tuple[str, str]:
        """Detect currency from HTML content with address-based classification"""
        try:
            # Step 1: Check domain-based currency detection first (highest priority)
            domain_currency = self._detect_currency_by_domain(url)
            if domain_currency:
                return domain_currency
            
            # Step 2: Address-based detection from content
            address_currency = self._detect_currency_from_address(html_content)
            if address_currency != 'USD':
                logger.info(f"Address-based currency detection: {address_currency}")
                return address_currency, self._get_symbol_for_code(address_currency)
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Step 3: Check meta tags for currency
            meta_currency = soup.find('meta', {'name': 'currency'})
            if meta_currency and meta_currency.get('content'):
                currency_code = meta_currency['content'].upper()
                if currency_code in self.currency_symbols:
                    symbol = self._get_symbol_for_code(currency_code)
                    return currency_code, symbol
            
            # Step 4: Enhanced currency detection in text content with INR priority
            text_content = html_content.lower()
            
            # Look for specific currency patterns with priority for INR
            currency_patterns = [
                ('INR', '₹', ['inr', '₹', 'rupee', 'rs.', 'rs ', 'indian rupee', '&#8377;', 'rupees']),
                ('GBP', '£', ['gbp', '£', 'pound', 'british pound', '&#163;']),
                ('EUR', '€', ['eur', '€', 'euro', '&#8364;']),
                ('CAD', 'C$', ['cad', 'canadian dollar', 'ca$', 'c$']),
                ('AUD', 'A$', ['aud', 'australian dollar', 'au$', 'a$']),
                ('USD', '$', ['usd', '$', 'dollar', 'us dollar'])  # USD has lowest priority
            ]
            
            for code, symbol, patterns in currency_patterns:
                if any(pattern in text_content for pattern in patterns):
                    logger.info(f"Detected currency from HTML content for {url}: {code} ({symbol})")
                    return code, symbol
            
            # Step 5: Check for currency in price elements as fallback
            price_elements = soup.find_all(['span', 'div', 'p'], class_=re.compile(r'price|cost|amount'))
            for element in price_elements[:10]:  # Check first 10 price elements
                text = element.get_text()
                for currency_code, symbol in self.currency_symbols.items():
                    if symbol in text:
                        return currency_code, symbol
            
            # Step 6: Default to INR for Indian-looking sites, USD otherwise
            if any(indicator in url.lower() for indicator in ['.in', 'india', 'mumbai', 'delhi']):
                logger.info(f"Defaulting to INR for Indian-looking site: {url}")
                return 'INR', '₹'
            
        except Exception as e:
            logger.error(f"Error detecting currency from HTML: {e}")
        
        return 'USD', '$'  # Final fallback
    
    def _detect_currency_by_domain(self, url: str) -> Optional[Tuple[str, str]]:
        """Detect currency based on domain/country with priority for Indian domains"""
        domain_mappings = {
            '.in': ('INR', '₹'),
            '.co.in': ('INR', '₹'),
            '.uk': ('GBP', '£'),
            '.co.uk': ('GBP', '£'),
            '.de': ('EUR', '€'),
            '.fr': ('EUR', '€'),
            '.ca': ('CAD', 'C$'),
            '.au': ('AUD', 'A$'),
            '.com.au': ('AUD', 'A$'),
            '.jp': ('JPY', '¥'),
            '.kr': ('KRW', '₩'),
            '.br': ('BRL', 'R$'),
            '.ru': ('RUB', '₽'),
        }
        
        url_lower = url.lower()
        
        # Check for Indian domains first (highest priority)
        if '.in' in url_lower or 'india' in url_lower:
            logger.info(f"Detected Indian domain for {url}, defaulting to INR")
            return 'INR', '₹'
        
        # Check other domain patterns
        for domain_suffix, (code, symbol) in domain_mappings.items():
            if domain_suffix in url_lower:
                logger.info(f"Detected domain currency for {url}: {code}")
                return code, symbol
        
        return None
    
    def _detect_currency_from_address(self, html_content: str) -> str:
        """Detect currency from address information in HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for address information in footer, contact sections, etc.
            address_sections = soup.find_all(['address', 'footer', 'div'], 
                                           class_=re.compile(r'address|contact|footer|location', re.I))
            
            address_text = ' '.join([section.get_text().lower() for section in address_sections])
            
            # Address-based currency patterns with priority for India
            address_patterns = {
                'india': 'INR',
                'mumbai': 'INR', 'delhi': 'INR', 'bangalore': 'INR', 'chennai': 'INR',
                'hyderabad': 'INR', 'pune': 'INR', 'kolkata': 'INR', 'gurgaon': 'INR',
                'noida': 'INR', 'ahmedabad': 'INR', 'jaipur': 'INR',
                'united kingdom': 'GBP', 'uk': 'GBP', 'london': 'GBP',
                'canada': 'CAD', 'toronto': 'CAD', 'vancouver': 'CAD',
                'australia': 'AUD', 'sydney': 'AUD', 'melbourne': 'AUD',
                'japan': 'JPY', 'tokyo': 'JPY', 'osaka': 'JPY'
            }
            
            for location, currency in address_patterns.items():
                if location in address_text:
                    logger.info(f"Address-based currency detection found: {location} -> {currency}")
                    return currency
            
            return 'USD'  # Default fallback
            
        except Exception as e:
            logger.warning(f"Error in address-based currency detection: {e}")
            return 'USD'
    
    def _get_symbol_for_code(self, currency_code: str) -> str:
        """Get currency symbol for a currency code"""
        return self.currency_symbols.get(currency_code, currency_code)
    
    def convert_price(self, amount: float, from_currency: str, to_currency: str = 'USD') -> Dict:
        """Convert price from one currency to another"""
        if from_currency == to_currency:
            return {
                'original_amount': amount,
                'original_currency': from_currency,
                'converted_amount': amount,
                'converted_currency': to_currency,
                'exchange_rate': 1.0
            }
        
        try:
            # Get exchange rate
            if from_currency in self.exchange_rates and to_currency in self.exchange_rates[from_currency]:
                rate = self.exchange_rates[from_currency][to_currency]
                converted_amount = round(amount * rate, 2)
                
                return {
                    'original_amount': amount,
                    'original_currency': from_currency,
                    'converted_amount': converted_amount,
                    'converted_currency': to_currency,
                    'exchange_rate': rate
                }
            
        except Exception as e:
            logger.error(f"Error converting currency: {e}")
        
        # Return original if conversion fails
        return {
            'original_amount': amount,
            'original_currency': from_currency,
            'converted_amount': amount,
            'converted_currency': from_currency,
            'exchange_rate': 1.0
        }
    
    def format_price_with_currency(self, amount: float, currency_code: str) -> str:
        """Format price with appropriate currency symbol"""
        symbol = self._get_symbol_for_code(currency_code)
        
        if currency_code == 'INR':
            # Indian numbering system
            if amount >= 100000:
                return f"₹{amount/100000:.1f}L"  # Lakhs
            elif amount >= 1000:
                return f"₹{amount/1000:.1f}K"  # Thousands
            else:
                return f"₹{amount:.0f}"
        elif currency_code in ['USD', 'CAD', 'AUD']:
            return f"{symbol}{amount:.2f}"
        elif currency_code == 'EUR':
            return f"{amount:.2f}€"
        elif currency_code == 'GBP':
            return f"£{amount:.2f}"
        elif currency_code == 'JPY':
            return f"¥{amount:.0f}"
        else:
            return f"{symbol}{amount:.2f}"
    
    def detect_and_convert_product_prices(self, products_data: list, html_content: str, url: str) -> Tuple[str, str, list]:
        """Detect currency and return formatted product data with conversions"""
        # First priority: HTML and domain-based detection (more reliable)
        detected_currency, currency_symbol = self.detect_currency_from_html(html_content, url)
        
        # Second priority: Product data detection (only if HTML detection returns USD)
        if detected_currency == 'USD' and currency_symbol == '$':
            product_currency, product_symbol = self.detect_currency_from_products(products_data)
            if product_currency != 'USD':
                detected_currency, currency_symbol = product_currency, product_symbol
        
        # Final fallback: Default to INR for Indian sites
        if detected_currency == 'USD' and ('.in' in url.lower() or 'india' in url.lower()):
            detected_currency, currency_symbol = 'INR', '₹'
            logger.info(f"Defaulting to INR for Indian site: {url}")
        
        logger.info(f"Final detected currency for {url}: {detected_currency} ({currency_symbol})")
        
        # Process products with currency conversion
        processed_products = []
        for product in products_data:
            processed_product = product.copy()
            variants = product.get('variants', [])
            
            if variants:
                for variant in variants:
                    price = variant.get('price')
                    if price:
                        try:
                            price_float = float(price)
                            # Convert to USD for standardization
                            conversion = self.convert_price(price_float, detected_currency, 'USD')
                            variant['original_price'] = price_float
                            variant['original_currency'] = detected_currency
                            variant['price_usd'] = conversion['converted_amount']
                            variant['formatted_price'] = self.format_price_with_currency(price_float, detected_currency)
                            variant['formatted_price_usd'] = self.format_price_with_currency(conversion['converted_amount'], 'USD')
                        except (ValueError, TypeError):
                            logger.warning(f"Could not convert price: {price}")
            
            processed_products.append(processed_product)
        
        return detected_currency, currency_symbol, processed_products