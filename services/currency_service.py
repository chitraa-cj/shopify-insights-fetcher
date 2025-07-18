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
            '$': 'USD',
            '₹': 'INR', 
            '€': 'EUR',
            '£': 'GBP',
            '¥': 'JPY',
            '₽': 'RUB',
            'C$': 'CAD',
            'A$': 'AUD',
            'kr': 'SEK',
            'zł': 'PLN',
            'R$': 'BRL',
            '₩': 'KRW',
            '¢': 'USD',  # cents
            'Rs': 'INR',
            'INR': 'INR',
            'USD': 'USD',
            'EUR': 'EUR',
            'GBP': 'GBP'
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
        """Detect currency from HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Check domain-based currency detection first (more reliable)
            domain_currency = self._detect_currency_by_domain(url)
            if domain_currency:
                return domain_currency
            
            # Check meta tags for currency
            meta_currency = soup.find('meta', {'name': 'currency'})
            if meta_currency and meta_currency.get('content'):
                currency_code = meta_currency['content'].upper()
                if currency_code in self.currency_symbols.values():
                    symbol = self._get_symbol_for_code(currency_code)
                    return currency_code, symbol
            
            # Enhanced currency detection in text content
            text_content = html_content.lower()
            
            # Look for specific currency patterns with priority
            currency_patterns = [
                ('INR', '₹', ['inr', '₹', 'rupee', 'rs.', 'rs ', 'indian rupee', '&#8377;']),
                ('GBP', '£', ['gbp', '£', 'pound', 'british pound', '&#163;']),
                ('EUR', '€', ['eur', '€', 'euro', '&#8364;']),
                ('CAD', 'C$', ['cad', 'canadian dollar', 'ca$', 'c$']),
                ('AUD', 'A$', ['aud', 'australian dollar', 'au$', 'a$']),
                ('USD', '$', ['usd', '$', 'dollar', 'us dollar'])
            ]
            
            for code, symbol, patterns in currency_patterns:
                if any(pattern in text_content for pattern in patterns):
                    logger.info(f"Detected currency from HTML for {url}: {code} ({symbol})")
                    return code, symbol
            
            # Check for currency in price elements as fallback
            price_elements = soup.find_all(['span', 'div', 'p'], class_=re.compile(r'price|cost|amount'))
            for element in price_elements[:10]:  # Check first 10 price elements
                text = element.get_text()
                for symbol, code in self.currency_symbols.items():
                    if symbol in text:
                        return code, symbol
            
        except Exception as e:
            logger.error(f"Error detecting currency from HTML: {e}")
        
        return 'USD', '$'  # Default fallback
    
    def _detect_currency_by_domain(self, url: str) -> Optional[Tuple[str, str]]:
        """Detect currency based on domain/country"""
        domain_mappings = {
            '.in': ('INR', '₹'),
            '.uk': ('GBP', '£'),
            '.de': ('EUR', '€'),
            '.fr': ('EUR', '€'),
            '.ca': ('CAD', 'C$'),
            '.au': ('AUD', 'A$'),
            '.jp': ('JPY', '¥'),
            '.kr': ('KRW', '₩'),
            '.br': ('BRL', 'R$'),
            '.ru': ('RUB', '₽'),
        }
        
        for domain_suffix, (code, symbol) in domain_mappings.items():
            if domain_suffix in url.lower():
                return code, symbol
        
        return None
    
    def _get_symbol_for_code(self, currency_code: str) -> str:
        """Get currency symbol for a currency code"""
        code_to_symbol = {v: k for k, v in self.currency_symbols.items()}
        return code_to_symbol.get(currency_code, currency_code)
    
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
        # Detect the store's currency
        detected_currency, currency_symbol = self.detect_currency_from_products(products_data)
        
        # If not detected from products, try HTML
        if detected_currency == 'USD' and currency_symbol == '$':
            detected_currency, currency_symbol = self.detect_currency_from_html(html_content, url)
        
        logger.info(f"Detected currency for {url}: {detected_currency} ({currency_symbol})")
        
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