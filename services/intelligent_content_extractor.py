"""
Intelligent content extractor using AI reasoning to automatically discover and extract
policy content, FAQ sections, and other structured content from complex website layouts.
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import trafilatura
import os

from services.base import BaseExtractor, OperationResult, ExtractionResult, NetworkHandler
from services.interfaces import IPolicyExtractor, IFAQExtractor, IAIValidator

logger = logging.getLogger(__name__)

class IntelligentPolicyExtractor(BaseExtractor):
    """
    Intelligent policy extractor that uses AI reasoning to discover and extract
    policy content from various website structures.
    """
    
    def __init__(self, network_handler: NetworkHandler, ai_validator: Optional[IAIValidator] = None):
        super().__init__(network_handler)
        self.ai_validator = ai_validator
        self.policy_keywords = [
            'privacy policy', 'terms of service', 'refund policy', 'return policy',
            'shipping policy', 'cookie policy', 'data protection', 'legal',
            'terms and conditions', 'privacy notice'
        ]
    
    def extract(self, url: str, **kwargs) -> OperationResult:
        """Extract method to satisfy BaseExtractor interface"""
        html_content = kwargs.get('html_content', '')
        return self.extract_policies(url, html_content)
        self.policy_keywords = {
            'privacy': ['privacy', 'policy', 'data', 'protection', 'gdpr'],
            'terms': ['terms', 'service', 'conditions', 'agreement', 'legal'],
            'return': ['return', 'returns', 'refund', 'exchange'],
            'shipping': ['shipping', 'delivery', 'fulfillment'],
            'cookie': ['cookie', 'cookies', 'tracking']
        }
    
    async def extract_policies(self, url: str, html_content: str) -> OperationResult:
        """Extract comprehensive policy information using AI reasoning"""
        validation_result = self.validate_input(url)
        if not validation_result.is_success:
            return validation_result
        
        if not html_content:
            return OperationResult(
                status=ExtractionResult.INVALID_INPUT,
                error_message="HTML content is required for policy extraction"
            )
        
        try:
            # Step 1: Discover policy links with AI assistance
            policy_links = await self._discover_policy_links_with_ai(url, html_content)
            
            # Step 2: Extract content from discovered links
            policy_content = {}
            for policy_type, links in policy_links.items():
                if links:
                    content = await self._extract_policy_content_from_links(links, url)
                    if content:
                        policy_content[policy_type] = content
            
            # Step 3: If no links found, try to extract from current page
            if not policy_content:
                page_policies = await self._extract_policies_from_current_page(html_content, url)
                policy_content.update(page_policies)
            
            # Step 4: Use AI to enhance and validate extracted content
            if self.ai_validator and policy_content:
                enhanced_content = await self._enhance_policies_with_ai(policy_content, url)
                if enhanced_content:
                    policy_content = enhanced_content
            
            return OperationResult(
                status=ExtractionResult.SUCCESS,
                data=policy_content,
                metadata={
                    'policies_found': len(policy_content),
                    'policy_types': list(policy_content.keys())
                }
            )
            
        except Exception as e:
            return self.handle_extraction_error(e, "Policy extraction failed")
    
    async def _discover_policy_links_with_ai(self, url: str, html_content: str) -> Dict[str, List[str]]:
        """Use AI to intelligently discover policy links"""
        if not self.ai_validator:
            return await self._discover_policy_links_traditional(html_content, url)
        
        try:
            # Prepare HTML structure for AI analysis
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract all links with context
            links_with_context = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                text = link.get_text().strip()
                parent_text = link.parent.get_text().strip() if link.parent else ""
                
                # Get surrounding context
                context = ""
                if link.parent:
                    siblings = link.parent.find_all(['a', 'span', 'div'], limit=5)
                    context = " ".join([s.get_text().strip() for s in siblings])
                
                links_with_context.append({
                    'href': href,
                    'text': text,
                    'parent_text': parent_text[:100],
                    'context': context[:200]
                })
            
            # Use AI to analyze and categorize links
            ai_prompt = f"""
            Analyze these website links and identify which ones lead to policy pages.
            Website: {url}
            
            Links to analyze:
            {links_with_context[:50]}  # Limit to first 50 links
            
            Please categorize these links into policy types:
            - privacy: Privacy policy, data protection, GDPR
            - terms: Terms of service, terms of use, legal conditions
            - return: Return policy, refund policy, exchange policy
            - shipping: Shipping policy, delivery terms
            - cookie: Cookie policy, tracking policy
            
            For each category, provide the most relevant href links.
            Consider context like footer sections, legal pages, policy menus.
            
            Return as JSON format:
            {{
                "privacy": ["link1", "link2"],
                "terms": ["link3"],
                "return": ["link4"],
                "shipping": ["link5"],
                "cookie": ["link6"]
            }}
            
            If no relevant links found for a category, return empty array.
            """
            
            ai_result = await self._query_ai_for_links(ai_prompt)
            if ai_result and isinstance(ai_result, dict):
                # Convert relative URLs to absolute
                policy_links = {}
                for policy_type, links in ai_result.items():
                    absolute_links = []
                    for link in links:
                        if link.startswith('/'):
                            absolute_links.append(urljoin(url, link))
                        elif link.startswith('http'):
                            absolute_links.append(link)
                    policy_links[policy_type] = absolute_links
                
                return policy_links
            
        except Exception as e:
            self.logger.warning(f"AI link discovery failed: {e}")
        
        # Fallback to traditional method
        return await self._discover_policy_links_traditional(html_content, url)
    
    async def _discover_policy_links_traditional(self, html_content: str, base_url: str) -> Dict[str, List[str]]:
        """Traditional method for discovering policy links"""
        soup = BeautifulSoup(html_content, 'html.parser')
        policy_links = {policy_type: [] for policy_type in self.policy_keywords.keys()}
        
        # Look for links in footer, navigation, and throughout the page
        for link in soup.find_all('a', href=True):
            href = link['href']
            link_text = link.get_text().lower().strip()
            
            # Convert relative URLs to absolute
            if href.startswith('/'):
                href = urljoin(base_url, href)
            elif not href.startswith('http'):
                continue
            
            # Check against policy keywords
            for policy_type, keywords in self.policy_keywords.items():
                if any(keyword in href.lower() or keyword in link_text for keyword in keywords):
                    if href not in policy_links[policy_type]:
                        policy_links[policy_type].append(href)
        
        return policy_links
    
    async def _extract_policy_content_from_links(self, links: List[str], base_url: str) -> Optional[str]:
        """Extract content from policy page links"""
        for link in links:
            try:
                response_result = self.network_handler.get(link)
                if response_result.is_success:
                    page_html = response_result.data.text
                    
                    # Extract main content using trafilatura
                    extracted_text = trafilatura.extract(page_html)
                    if extracted_text and len(extracted_text) > 200:
                        return extracted_text
                    
                    # Fallback: extract from specific containers
                    soup = BeautifulSoup(page_html, 'html.parser')
                    content_containers = soup.find_all(['main', 'article', '.content', '.policy-content', '.legal-content'])
                    
                    for container in content_containers:
                        text = container.get_text().strip()
                        if text and len(text) > 200:
                            return text
                            
            except Exception as e:
                self.logger.warning(f"Failed to extract content from {link}: {e}")
                continue
        
        return None
    
    async def _extract_policies_from_current_page(self, html_content: str, url: str) -> Dict[str, str]:
        """Extract policy content directly from current page if available"""
        soup = BeautifulSoup(html_content, 'html.parser')
        policies = {}
        
        # Look for sections that might contain policy information
        policy_sections = soup.find_all(['section', 'div'], class_=re.compile(r'policy|legal|terms|privacy', re.I))
        
        for section in policy_sections:
            text = section.get_text().strip()
            if len(text) > 200:
                # Try to determine policy type from content
                text_lower = text.lower()
                for policy_type, keywords in self.policy_keywords.items():
                    if any(keyword in text_lower for keyword in keywords):
                        if policy_type not in policies:
                            policies[policy_type] = text[:2000]  # Limit length
                        break
        
        return policies
    
    async def _enhance_policies_with_ai(self, policy_content: Dict[str, str], url: str) -> Optional[Dict[str, str]]:
        """Use AI to enhance and clean up extracted policy content"""
        if not policy_content:
            return None
        
        try:
            enhanced_policies = {}
            
            for policy_type, content in policy_content.items():
                if len(content) > 100:  # Only enhance substantial content
                    ai_prompt = f"""
                    Clean and summarize this {policy_type} policy content from {url}.
                    
                    Original content:
                    {content[:3000]}  # Limit content length for AI
                    
                    Please:
                    1. Remove navigation elements, headers, footers
                    2. Extract only the actual policy content
                    3. Organize into clear sections
                    4. Preserve important legal terms and conditions
                    5. Make it readable while keeping all essential information
                    
                    Return the cleaned and organized policy content.
                    """
                    
                    enhanced_content = await self._query_ai_for_content(ai_prompt)
                    if enhanced_content and len(enhanced_content) > 100:
                        enhanced_policies[policy_type] = enhanced_content
                    else:
                        enhanced_policies[policy_type] = content  # Keep original if AI fails
            
            return enhanced_policies if enhanced_policies else policy_content
            
        except Exception as e:
            self.logger.warning(f"AI policy enhancement failed: {e}")
            return policy_content
    
    async def _query_ai_for_links(self, prompt: str) -> Optional[Dict[str, List[str]]]:
        """Query AI for link analysis"""
        if not self.ai_validator:
            return None
        
        try:
            import json
            from google import genai
            import os
            
            if not os.environ.get("GEMINI_API_KEY"):
                return None
            
            client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            if response.text:
                # Try to extract JSON from the response
                response_text = response.text.strip()
                
                # Find JSON content between code blocks or directly
                if '```json' in response_text:
                    json_start = response_text.find('```json') + 7
                    json_end = response_text.find('```', json_start)
                    json_content = response_text[json_start:json_end].strip()
                elif '{' in response_text and '}' in response_text:
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    json_content = response_text[json_start:json_end]
                else:
                    return None
                
                try:
                    result = json.loads(json_content)
                    return result if isinstance(result, dict) else None
                except json.JSONDecodeError:
                    return None
            
            return None
        except Exception as e:
            self.logger.error(f"AI link query failed: {e}")
            return None
    
    async def _query_ai_for_content(self, prompt: str) -> Optional[str]:
        """Query AI for content enhancement"""
        if not self.ai_validator:
            return None
        
        try:
            from google import genai
            import os
            
            if not os.environ.get("GEMINI_API_KEY"):
                return None
            
            client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            return response.text if response.text else None
        except Exception as e:
            self.logger.error(f"AI content query failed: {e}")
            return None

class IntelligentFAQExtractor(BaseExtractor):
    """
    Intelligent FAQ extractor that can navigate complex FAQ structures
    including expandable sections, categorized FAQs, and help centers.
    """
    
    def __init__(self, network_handler: NetworkHandler, ai_validator: Optional[IAIValidator] = None):
        super().__init__(network_handler)
        self.ai_validator = ai_validator
        self.faq_keywords = [
            'faq', 'frequently asked questions', 'help', 'support',
            'questions', 'answers', 'how to', 'guide', 'tutorial',
            'customer service', 'help center'
        ]
    
    def extract(self, url: str, **kwargs) -> OperationResult:
        """Extract method to satisfy BaseExtractor interface"""
        html_content = kwargs.get('html_content', '')
        return self.extract_faqs(url, html_content)
        self.faq_keywords = ['faq', 'help', 'support', 'questions', 'answers', 'knowledge']
    
    async def extract_faqs(self, url: str, html_content: str) -> OperationResult:
        """Extract comprehensive FAQ information using intelligent navigation"""
        validation_result = self.validate_input(url)
        if not validation_result.is_success:
            return validation_result
        
        if not html_content:
            return OperationResult(
                status=ExtractionResult.INVALID_INPUT,
                error_message="HTML content is required for FAQ extraction"
            )
        
        try:
            # Step 1: Discover FAQ sections and pages
            faq_sources = await self._discover_faq_sources(url, html_content)
            
            # Step 2: Extract FAQs from all discovered sources
            all_faqs = []
            for source in faq_sources:
                faqs = await self._extract_faqs_from_source(source)
                all_faqs.extend(faqs)
            
            # Step 3: Use AI to clean and organize FAQs
            if self.ai_validator and all_faqs:
                organized_faqs = await self._organize_faqs_with_ai(all_faqs, url)
                if organized_faqs:
                    all_faqs = organized_faqs
            
            return OperationResult(
                status=ExtractionResult.SUCCESS,
                data=all_faqs,
                metadata={
                    'total_faqs': len(all_faqs),
                    'sources_found': len(faq_sources)
                }
            )
            
        except Exception as e:
            return self.handle_extraction_error(e, "FAQ extraction failed")
    
    async def _discover_faq_sources(self, url: str, html_content: str) -> List[Dict[str, Any]]:
        """Discover all FAQ sources including links and on-page sections"""
        soup = BeautifulSoup(html_content, 'html.parser')
        sources = []
        
        # Check current page for FAQ content
        current_page_faqs = await self._find_faqs_on_current_page(soup, url)
        if current_page_faqs:
            sources.append({
                'type': 'current_page',
                'url': url,
                'content': html_content,
                'faqs': current_page_faqs
            })
        
        # Find FAQ links
        faq_links = await self._find_faq_links(soup, url)
        for link in faq_links:
            sources.append({
                'type': 'external_page',
                'url': link,
                'content': None,
                'faqs': None
            })
        
        # Look for expandable FAQ sections (like ColourPop)
        expandable_sections = await self._find_expandable_faq_sections(soup, url)
        sources.extend(expandable_sections)
        
        return sources
    
    async def _find_faqs_on_current_page(self, soup: BeautifulSoup, url: str) -> List[Dict[str, str]]:
        """Find FAQ content directly on the current page"""
        faqs = []
        
        # Look for various FAQ patterns
        faq_patterns = [
            # Standard Q&A sections
            {'q_selector': '.question', 'a_selector': '.answer'},
            {'q_selector': '.faq-question', 'a_selector': '.faq-answer'},
            {'q_selector': 'dt', 'a_selector': 'dd'},
            {'q_selector': 'h3', 'a_selector': 'p'},
            {'q_selector': '[data-question]', 'a_selector': '[data-answer]'},
        ]
        
        for pattern in faq_patterns:
            questions = soup.select(pattern['q_selector'])
            answers = soup.select(pattern['a_selector'])
            
            # Pair questions with answers
            for i, question in enumerate(questions):
                if i < len(answers):
                    q_text = question.get_text().strip()
                    a_text = answers[i].get_text().strip()
                    
                    # Filter out navigation and irrelevant content
                    if (len(q_text) > 10 and len(a_text) > 10 and 
                        not self._is_navigation_content(q_text) and
                        not self._is_navigation_content(a_text)):
                        faqs.append({
                            'question': q_text,
                            'answer': a_text,
                            'source': url
                        })
        
        return faqs
    
    async def _find_faq_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Find links to FAQ pages"""
        faq_links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            link_text = link.get_text().lower().strip()
            
            # Check if link looks like FAQ
            if any(keyword in href.lower() or keyword in link_text for keyword in self.faq_keywords):
                # Convert to absolute URL
                if href.startswith('/'):
                    href = urljoin(base_url, href)
                elif href.startswith('http'):
                    pass  # Already absolute
                else:
                    continue
                
                if href not in faq_links:
                    faq_links.append(href)
        
        return faq_links
    
    async def _find_expandable_faq_sections(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Find expandable FAQ sections that need JavaScript interaction"""
        sections = []
        
        # Look for accordion-style FAQ sections
        accordion_patterns = [
            '.accordion',
            '.faq-accordion',
            '.collapsible',
            '[data-toggle="collapse"]',
            '.expandable'
        ]
        
        for pattern in accordion_patterns:
            elements = soup.select(pattern)
            for element in elements:
                # Check if this looks like FAQ content
                text = element.get_text().lower()
                if any(keyword in text for keyword in self.faq_keywords):
                    sections.append({
                        'type': 'expandable_section',
                        'url': base_url,
                        'element_selector': pattern,
                        'content': element,
                        'faqs': None
                    })
        
        return sections
    
    async def _extract_faqs_from_source(self, source: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract FAQs from a specific source"""
        if source['type'] == 'current_page' and source.get('faqs'):
            return source['faqs']
        
        elif source['type'] == 'external_page':
            return await self._extract_faqs_from_external_page(source['url'])
        
        elif source['type'] == 'expandable_section':
            return await self._extract_faqs_from_expandable_section(source)
        
        return []
    
    async def _extract_faqs_from_external_page(self, url: str) -> List[Dict[str, str]]:
        """Extract FAQs from external FAQ page"""
        try:
            response_result = self.network_handler.get(url)
            if not response_result.is_success:
                return []
            
            soup = BeautifulSoup(response_result.data.text, 'html.parser')
            return await self._find_faqs_on_current_page(soup, url)
            
        except Exception as e:
            self.logger.warning(f"Failed to extract FAQs from {url}: {e}")
            return []
    
    async def _extract_faqs_from_expandable_section(self, source: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract FAQs from expandable sections (limited without JavaScript execution)"""
        faqs = []
        element = source.get('content')
        
        if element:
            # Look for hidden content that might be expanded
            hidden_content = element.find_all(['div', 'section'], class_=re.compile(r'hidden|collapse|content', re.I))
            
            for content in hidden_content:
                text = content.get_text().strip()
                if len(text) > 50:  # Substantial content
                    # Try to identify question-answer pairs
                    lines = text.split('\n')
                    current_question = None
                    current_answer = []
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Heuristic: questions often end with ? or are shorter
                        if (line.endswith('?') or len(line) < 100) and current_answer:
                            # Save previous Q&A
                            if current_question:
                                faqs.append({
                                    'question': current_question,
                                    'answer': ' '.join(current_answer),
                                    'source': source['url']
                                })
                            current_question = line
                            current_answer = []
                        else:
                            if current_question:
                                current_answer.append(line)
                            elif not current_question and line.endswith('?'):
                                current_question = line
                    
                    # Save last Q&A
                    if current_question and current_answer:
                        faqs.append({
                            'question': current_question,
                            'answer': ' '.join(current_answer),
                            'source': source['url']
                        })
        
        return faqs
    
    async def _organize_faqs_with_ai(self, faqs: List[Dict[str, str]], url: str) -> Optional[List[Dict[str, str]]]:
        """Use AI to organize and clean up extracted FAQs"""
        if not self.ai_validator or not faqs:
            return faqs
        
        try:
            # Group similar FAQs and remove duplicates
            organized_faqs = []
            seen_questions = set()
            
            for faq in faqs:
                question = faq['question'].strip()
                question_lower = question.lower()
                
                # Simple deduplication
                if question_lower not in seen_questions:
                    seen_questions.add(question_lower)
                    
                    # Clean up the FAQ
                    if len(faq['answer']) > 50:  # Only keep substantial answers
                        organized_faqs.append({
                            'question': question,
                            'answer': faq['answer'].strip(),
                            'source': faq.get('source', url)
                        })
            
            return organized_faqs
            
        except Exception as e:
            self.logger.warning(f"AI FAQ organization failed: {e}")
            return faqs
    
    def _is_navigation_content(self, text: str) -> bool:
        """Check if text looks like navigation content rather than FAQ content"""
        navigation_indicators = [
            'home', 'about', 'contact', 'menu', 'cart', 'account', 
            'login', 'register', 'search', 'category', 'shop',
            'follow us', 'subscribe', 'newsletter'
        ]
        
        text_lower = text.lower().strip()
        
        # Too short to be meaningful FAQ content
        if len(text_lower) < 10:
            return True
        
        # Contains navigation keywords
        if any(keyword in text_lower for keyword in navigation_indicators):
            return True
        
        # Looks like a navigation item (short, no punctuation)
        if len(text_lower) < 30 and not any(char in text_lower for char in '.?!'):
            return True
        
        return False

# Integration with existing AI validator
class EnhancedAIValidator:
    """Enhanced AI validator with intelligent content extraction capabilities"""
    
    def __init__(self, base_ai_validator: Optional[IAIValidator] = None):
        self.base_validator = base_ai_validator
        self.logger = logging.getLogger(__name__)
    
    async def extract_structured_content(self, url: str, html_content: str, content_type: str) -> OperationResult:
        """Use AI to extract structured content with reasoning"""
        if not self.base_validator:
            return OperationResult(
                status=ExtractionResult.FAILURE,
                error_message="AI validator not available"
            )
        
        try:
            if content_type == "policies":
                extractor = IntelligentPolicyExtractor(None, self.base_validator)
                return await extractor.extract_policies(url, html_content)
            
            elif content_type == "faqs":
                extractor = IntelligentFAQExtractor(None, self.base_validator)
                return await extractor.extract_faqs(url, html_content)
            
            else:
                return OperationResult(
                    status=ExtractionResult.INVALID_INPUT,
                    error_message=f"Unsupported content type: {content_type}"
                )
                
        except Exception as e:
            return OperationResult(
                status=ExtractionResult.FAILURE,
                error_message=f"Enhanced AI extraction failed: {str(e)}"
            )