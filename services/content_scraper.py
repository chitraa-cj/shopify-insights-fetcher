import asyncio
import logging
import re
from typing import List
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import trafilatura
from models import BrandContext, PolicyInfo, FAQ, ContactDetails, ImportantLinks

logger = logging.getLogger(__name__)

class ContentScraperService:
    """Service for scraping content and text information from Shopify stores"""
    
    def __init__(self, session: requests.Session):
        self.session = session
    
    async def get_brand_context(self, base_url: str) -> BrandContext:
        """
        Extract brand context and about information
        
        Args:
            base_url: The base URL of the Shopify store
            
        Returns:
            BrandContext: Brand information
        """
        brand_context = BrandContext()
        
        try:
            # Get homepage content
            response = self.session.get(base_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract brand name from title or header
            title_tag = soup.find('title')
            if title_tag:
                brand_context.brand_name = title_tag.get_text(strip=True).split('|')[0].split('-')[0].strip()
            
            # Look for about us page
            about_links = self._find_links_by_keywords(soup, ['about', 'about-us', 'our-story', 'who-we-are'])
            
            for link in about_links[:3]:  # Check first 3 potential about pages
                try:
                    about_url = urljoin(base_url, link)
                    about_content = await self._get_clean_text_content(about_url)
                    if about_content and len(about_content) > 100:
                        if not brand_context.about_us_content:
                            brand_context.about_us_content = about_content[:2000]  # Limit length
                        break
                except Exception as e:
                    logger.warning(f"Error fetching about content from {about_url}: {e}")
                    continue
            
            # Extract brand description from meta tags
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                brand_context.brand_description = meta_desc.get('content', '')
            
            # Look for brand story in homepage content
            homepage_text = trafilatura.extract(response.text)
            if homepage_text:
                # Look for mission/story keywords
                text_lower = homepage_text.lower()
                if any(keyword in text_lower for keyword in ['mission', 'story', 'founded', 'believe']):
                    brand_context.brand_story = homepage_text[:1000]  # First 1000 chars
            
            return brand_context
            
        except Exception as e:
            logger.error(f"Error extracting brand context: {e}")
            return brand_context
    
    async def get_policies(self, base_url: str) -> PolicyInfo:
        """
        Extract policy information
        
        Args:
            base_url: The base URL of the Shopify store
            
        Returns:
            PolicyInfo: Policy information
        """
        policies = PolicyInfo()
        
        try:
            response = self.session.get(base_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Policy mappings
            policy_mappings = {
                'privacy': ['privacy-policy', 'privacy', 'policies/privacy-policy'],
                'return': ['return-policy', 'returns', 'policies/return-policy'],
                'refund': ['refund-policy', 'refunds', 'policies/refund-policy'],
                'terms': ['terms-of-service', 'terms', 'policies/terms-of-service']
            }
            
            # Find policy links
            all_links = soup.find_all('a', href=True)
            
            for policy_type, keywords in policy_mappings.items():
                for link in all_links:
                    href = link.get('href', '').lower()
                    link_text = link.get_text(strip=True).lower()
                    
                    # Check if link matches policy keywords
                    if any(keyword in href for keyword in keywords) or \
                       any(keyword.replace('-', ' ') in link_text for keyword in keywords):
                        
                        try:
                            policy_url = urljoin(base_url, link['href'])
                            policy_content = await self._get_clean_text_content(policy_url)
                            
                            if policy_type == 'privacy':
                                policies.privacy_policy_url = policy_url
                                policies.privacy_policy_content = policy_content[:3000] if policy_content else None
                            elif policy_type == 'return':
                                policies.return_policy_url = policy_url
                                policies.return_policy_content = policy_content[:3000] if policy_content else None
                            elif policy_type == 'refund':
                                policies.refund_policy_url = policy_url
                                policies.refund_policy_content = policy_content[:3000] if policy_content else None
                            elif policy_type == 'terms':
                                policies.terms_of_service_url = policy_url
                                policies.terms_of_service_content = policy_content[:3000] if policy_content else None
                            
                            break  # Found policy for this type
                            
                        except Exception as e:
                            logger.warning(f"Error fetching {policy_type} policy: {e}")
                            continue
            
            return policies
            
        except Exception as e:
            logger.error(f"Error extracting policies: {e}")
            return policies
    
    async def get_faqs(self, base_url: str) -> List[FAQ]:
        """
        Extract FAQ information
        
        Args:
            base_url: The base URL of the Shopify store
            
        Returns:
            List[FAQ]: List of FAQ items
        """
        faqs = []
        
        try:
            response = self.session.get(base_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find FAQ links
            faq_links = self._find_links_by_keywords(soup, ['faq', 'faqs', 'frequently-asked', 'help', 'support'])
            
            for faq_link in faq_links[:3]:  # Check first 3 FAQ pages
                try:
                    faq_url = urljoin(base_url, faq_link)
                    faq_response = self.session.get(faq_url, timeout=10)
                    faq_response.raise_for_status()
                    
                    faq_soup = BeautifulSoup(faq_response.text, 'html.parser')
                    page_faqs = self._extract_faqs_from_page(faq_soup)
                    faqs.extend(page_faqs)
                    
                    if len(faqs) >= 20:  # Limit to prevent too many FAQs
                        break
                        
                except Exception as e:
                    logger.warning(f"Error fetching FAQ from {faq_url}: {e}")
                    continue
            
            # Also check homepage for FAQs
            homepage_faqs = self._extract_faqs_from_page(soup)
            faqs.extend(homepage_faqs)
            
            # Remove duplicates and limit
            unique_faqs = []
            seen_questions = set()
            
            for faq in faqs:
                if faq.question.lower() not in seen_questions:
                    unique_faqs.append(faq)
                    seen_questions.add(faq.question.lower())
                    
                if len(unique_faqs) >= 15:  # Limit to 15 FAQs
                    break
            
            return unique_faqs
            
        except Exception as e:
            logger.error(f"Error extracting FAQs: {e}")
            return []
    
    async def get_contact_details(self, base_url: str) -> ContactDetails:
        """
        Extract contact details
        
        Args:
            base_url: The base URL of the Shopify store
            
        Returns:
            ContactDetails: Contact information
        """
        contact_details = ContactDetails()
        
        try:
            # Check multiple pages for contact info
            pages_to_check = [
                base_url,
                urljoin(base_url, '/pages/contact'),
                urljoin(base_url, '/pages/contact-us'),
                urljoin(base_url, '/contact'),
                urljoin(base_url, '/contact-us')
            ]
            
            all_text = ""
            
            for page_url in pages_to_check:
                try:
                    response = self.session.get(page_url, timeout=5)
                    if response.status_code == 200:
                        text_content = trafilatura.extract(response.text)
                        if text_content:
                            all_text += " " + text_content
                except Exception:
                    continue
            
            # Extract emails
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, all_text)
            contact_details.emails = list(set(emails))  # Remove duplicates
            
            # Extract phone numbers
            phone_pattern = r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
            phones = re.findall(phone_pattern, all_text)
            contact_details.phone_numbers = [f"({phone[0]}) {phone[1]}-{phone[2]}" for phone in phones]
            
            # Look for address
            address_keywords = ['address', 'location', 'visit us', 'headquarters']
            for keyword in address_keywords:
                if keyword in all_text.lower():
                    # Extract text around the keyword
                    start_idx = all_text.lower().find(keyword)
                    address_text = all_text[start_idx:start_idx+200]
                    if len(address_text) > 20:
                        contact_details.address = address_text.strip()
                        break
            
            return contact_details
            
        except Exception as e:
            logger.error(f"Error extracting contact details: {e}")
            return contact_details
    
    async def get_important_links(self, base_url: str) -> ImportantLinks:
        """
        Extract important links
        
        Args:
            base_url: The base URL of the Shopify store
            
        Returns:
            ImportantLinks: Important website links
        """
        important_links = ImportantLinks()
        
        try:
            response = self.session.get(base_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            all_links = soup.find_all('a', href=True)
            
            link_mappings = {
                'order_tracking': ['track', 'tracking', 'order-status'],
                'contact_us': ['contact', 'contact-us'],
                'blogs': ['blog', 'blogs', 'news', 'journal'],
                'size_guide': ['size-guide', 'sizing', 'size-chart'],
                'shipping_info': ['shipping', 'delivery', 'shipping-info'],
                'about_us': ['about', 'about-us', 'our-story'],
                'careers': ['careers', 'jobs', 'work-with-us']
            }
            
            for attr_name, keywords in link_mappings.items():
                for link in all_links:
                    href = link.get('href', '').lower()
                    link_text = link.get_text(strip=True).lower()
                    
                    if any(keyword in href or keyword in link_text for keyword in keywords):
                        full_url = urljoin(base_url, link['href'])
                        setattr(important_links, attr_name, full_url)
                        break
            
            return important_links
            
        except Exception as e:
            logger.error(f"Error extracting important links: {e}")
            return important_links
    
    def _find_links_by_keywords(self, soup: BeautifulSoup, keywords: List[str]) -> List[str]:
        """Find links that match given keywords"""
        links = []
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href', '').lower()
            link_text = link.get_text(strip=True).lower()
            
            if any(keyword in href or keyword in link_text for keyword in keywords):
                links.append(link['href'])
        
        return links
    
    async def _get_clean_text_content(self, url: str) -> str:
        """Get clean text content from a URL using trafilatura"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            text_content = trafilatura.extract(response.text)
            return text_content if text_content else ""
            
        except Exception as e:
            logger.warning(f"Error getting clean text from {url}: {e}")
            return ""
    
    def _extract_faqs_from_page(self, soup: BeautifulSoup) -> List[FAQ]:
        """Extract FAQ items from a page"""
        faqs = []
        
        # Look for common FAQ structures
        faq_selectors = [
            '.faq-item',
            '.faq-question',
            '.accordion-item',
            '.collapsible',
            'details',
            '[data-faq]'
        ]
        
        for selector in faq_selectors:
            faq_elements = soup.select(selector)
            
            for element in faq_elements:
                try:
                    # Try to find question and answer
                    question = None
                    answer = None
                    
                    # Different patterns for questions and answers
                    if element.name == 'details':
                        summary = element.find('summary')
                        question = summary.get_text(strip=True) if summary else None
                        answer = element.get_text(strip=True).replace(question or '', '').strip()
                    else:
                        # Look for question in various ways
                        question_elem = (element.find('.question') or 
                                       element.find('.faq-question') or
                                       element.find('h3') or
                                       element.find('h4') or
                                       element.find('.title'))
                        
                        if question_elem:
                            question = question_elem.get_text(strip=True)
                            
                            # Look for answer
                            answer_elem = (element.find('.answer') or
                                         element.find('.faq-answer') or
                                         element.find('.content'))
                            
                            if answer_elem:
                                answer = answer_elem.get_text(strip=True)
                            else:
                                # Get remaining text as answer
                                answer = element.get_text(strip=True).replace(question, '').strip()
                    
                    if question and answer and len(question) > 5 and len(answer) > 5:
                        faqs.append(FAQ(question=question[:200], answer=answer[:500]))
                        
                except Exception as e:
                    logger.warning(f"Error parsing FAQ element: {e}")
                    continue
        
        return faqs
