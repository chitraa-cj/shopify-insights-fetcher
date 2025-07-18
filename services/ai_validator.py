import json
import logging
import os
from typing import Dict, List, Optional, Any
import asyncio

from google import genai
from google.genai import types
from pydantic import BaseModel
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin

from models import BrandContext, PolicyInfo, FAQ, SocialHandles, ContactDetails, ImportantLinks, AIValidationResult

logger = logging.getLogger(__name__)

class ContentValidation(BaseModel):
    """Model for AI content validation results"""
    is_valid: bool
    confidence: float
    issues: List[str] = []
    suggestions: List[str] = []
    improved_content: Optional[str] = None

class AIValidatorService:
    """Service for AI-powered content validation using Gemini"""
    
    def __init__(self, session: requests.Session):
        self.session = session
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.client = None
        self.ai_available = False
        
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                self.ai_available = True
                logger.info("Gemini AI validation enabled")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self.ai_available = False
        else:
            logger.warning("GEMINI_API_KEY not provided - AI validation features disabled")
            self.ai_available = False
    
    async def validate_brand_context(self, url: str, brand_context: BrandContext, html_content: str) -> BrandContext:
        """Validate and improve brand context using AI"""
        if not self.ai_available:
            logger.info("AI validation skipped - Gemini API key not available")
            return brand_context
        
        try:
            # Analyze the extracted brand context
            validation_prompt = f"""
            Analyze the following brand context extracted from a Shopify store:
            
            Website URL: {url}
            Brand Name: {brand_context.brand_name or 'Not found'}
            Brand Description: {brand_context.brand_description or 'Not found'}
            About Us Content: {brand_context.about_us_content or 'Not found'}
            
            Please evaluate if this information accurately represents the brand. 
            Look for missing or incorrect information. Rate confidence from 0-1.
            
            Respond with JSON in this format:
            {{
                "is_valid": boolean,
                "confidence": number,
                "issues": ["list of issues found"],
                "suggestions": ["list of improvement suggestions"]
            }}
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=validation_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ContentValidation,
                ),
            )
            
            if response.text:
                validation_result = ContentValidation(**json.loads(response.text))
                
                # If validation shows issues, try to extract better content from HTML
                if not validation_result.is_valid or validation_result.confidence < 0.7:
                    logger.info(f"Brand context validation failed for {url}, attempting HTML analysis")
                    improved_context = await self._extract_brand_from_html(url, html_content)
                    if improved_context:
                        return improved_context
            
            return brand_context
            
        except Exception as e:
            logger.error(f"Error validating brand context: {e}")
            return brand_context
    
    async def validate_social_handles(self, url: str, social_handles: SocialHandles, html_content: str) -> SocialHandles:
        """Validate and improve social media handles using AI"""
        if not self.ai_available:
            logger.info("AI validation skipped - Gemini API key not available")
            return social_handles
        
        try:
            # Create a summary of found social handles
            handles_summary = {
                "instagram": social_handles.instagram,
                "facebook": social_handles.facebook,
                "twitter": social_handles.twitter,
                "tiktok": social_handles.tiktok,
                "youtube": social_handles.youtube,
                "linkedin": social_handles.linkedin,
                "pinterest": social_handles.pinterest
            }
            
            validation_prompt = f"""
            Analyze social media handles extracted from {url}:
            {json.dumps(handles_summary, indent=2)}
            
            Evaluate if these handles are valid and complete. Look for:
            1. Missing popular social platforms
            2. Invalid handle formats
            3. Handles that don't match the brand
            
            Rate confidence from 0-1 and provide suggestions.
            
            Respond with JSON in this format:
            {{
                "is_valid": boolean,
                "confidence": number,
                "issues": ["list of issues"],
                "suggestions": ["improvement suggestions"]
            }}
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=validation_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ContentValidation,
                ),
            )
            
            if response.text:
                validation_result = ContentValidation(**json.loads(response.text))
                
                if not validation_result.is_valid or validation_result.confidence < 0.7:
                    logger.info(f"Social handles validation failed for {url}, attempting HTML analysis")
                    improved_handles = await self._extract_socials_from_html(url, html_content)
                    if improved_handles:
                        return improved_handles
            
            return social_handles
            
        except Exception as e:
            logger.error(f"Error validating social handles: {e}")
            return social_handles
    
    async def validate_contact_details(self, url: str, contact_details: ContactDetails, html_content: str) -> ContactDetails:
        """Validate and improve contact details using AI"""
        if not self.ai_available:
            logger.info("AI validation skipped - Gemini API key not available")
            return contact_details
        
        try:
            contact_summary = {
                "emails": contact_details.emails,
                "phone_numbers": contact_details.phone_numbers,
                "address": contact_details.address
            }
            
            validation_prompt = f"""
            Analyze contact details extracted from {url}:
            {json.dumps(contact_summary, indent=2)}
            
            Evaluate if these contact details are complete and valid:
            1. Are email formats correct?
            2. Are phone numbers in proper format?
            3. Is the address complete?
            4. Are there missing contact methods?
            
            Rate confidence from 0-1.
            
            Respond with JSON in this format:
            {{
                "is_valid": boolean,
                "confidence": number,
                "issues": ["list of issues"],
                "suggestions": ["improvement suggestions"]
            }}
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=validation_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ContentValidation,
                ),
            )
            
            if response.text:
                validation_result = ContentValidation(**json.loads(response.text))
                
                if not validation_result.is_valid or validation_result.confidence < 0.7:
                    logger.info(f"Contact details validation failed for {url}, attempting HTML analysis")
                    improved_contact = await self._extract_contact_from_html(url, html_content)
                    if improved_contact:
                        return improved_contact
            
            return contact_details
            
        except Exception as e:
            logger.error(f"Error validating contact details: {e}")
            return contact_details
    
    async def validate_faqs(self, url: str, faqs: List[FAQ], html_content: str) -> List[FAQ]:
        """Validate and improve FAQs using AI"""
        if not self.ai_available or not faqs:
            if not self.ai_available:
                logger.info("AI validation skipped - Gemini API key not available")
            return faqs
        
        try:
            faqs_summary = [{"question": faq.question, "answer": faq.answer} for faq in faqs[:5]]
            
            validation_prompt = f"""
            Analyze FAQs extracted from {url}:
            {json.dumps(faqs_summary, indent=2)}
            
            Evaluate the quality of these FAQs:
            1. Are questions and answers clearly matched?
            2. Do answers provide useful information?
            3. Are there obvious formatting issues?
            4. Are important FAQs missing?
            
            Rate confidence from 0-1.
            
            Respond with JSON in this format:
            {{
                "is_valid": boolean,
                "confidence": number,
                "issues": ["list of issues"],
                "suggestions": ["improvement suggestions"]
            }}
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=validation_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ContentValidation,
                ),
            )
            
            if response.text:
                validation_result = ContentValidation(**json.loads(response.text))
                
                if not validation_result.is_valid or validation_result.confidence < 0.7:
                    logger.info(f"FAQs validation failed for {url}, attempting HTML analysis")
                    improved_faqs = await self._extract_faqs_from_html(url, html_content)
                    if improved_faqs:
                        return improved_faqs
            
            return faqs
            
        except Exception as e:
            logger.error(f"Error validating FAQs: {e}")
            return faqs
    
    async def validate_policies(self, url: str, policies: PolicyInfo, html_content: str) -> PolicyInfo:
        """Validate and improve policy information using AI"""
        if not self.ai_available:
            logger.info("AI validation skipped - Gemini API key not available")
            return policies
        
        try:
            policies_summary = {
                "privacy_policy": {"url": policies.privacy_policy_url, "has_content": bool(policies.privacy_policy_content)},
                "return_policy": {"url": policies.return_policy_url, "has_content": bool(policies.return_policy_content)},
                "refund_policy": {"url": policies.refund_policy_url, "has_content": bool(policies.refund_policy_content)},
                "terms_of_service": {"url": policies.terms_of_service_url, "has_content": bool(policies.terms_of_service_content)}
            }
            
            validation_prompt = f"""
            Analyze policy information extracted from {url}:
            {json.dumps(policies_summary, indent=2)}
            
            Evaluate if these policies are complete and accessible:
            1. Are all essential policies present (privacy, return/refund, terms)?
            2. Do the URLs lead to actual policy content?
            3. Are there missing important policies for e-commerce?
            
            Rate confidence from 0-1.
            
            Respond with JSON in this format:
            {{
                "is_valid": boolean,
                "confidence": number,
                "issues": ["list of issues"],
                "suggestions": ["improvement suggestions"]
            }}
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=validation_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ContentValidation,
                ),
            )
            
            if response.text:
                validation_result = ContentValidation(**json.loads(response.text))
                
                if not validation_result.is_valid or validation_result.confidence < 0.7:
                    logger.info(f"Policy validation failed for {url}, attempting HTML analysis")
                    improved_policies = await self._extract_policies_from_html(url, html_content)
                    if improved_policies:
                        return improved_policies
            
            return policies
            
        except Exception as e:
            logger.error(f"Error validating policies: {e}")
            return policies
    
    async def comprehensive_validation(self, url: str, insights) -> AIValidationResult:
        """Perform comprehensive AI validation of all extracted insights"""
        if not self.ai_available:
            logger.info("AI comprehensive validation skipped - Gemini API key not available")
            return AIValidationResult(
                validated=False,
                confidence_score=0.5,  # Neutral score when AI unavailable
                validation_notes=["AI validation unavailable - Gemini API key not provided"]
            )
        
        try:
            # Create a summary of all extracted data
            insights_summary = {
                "brand_name": insights.brand_context.brand_name,
                "total_products": insights.total_products_found,
                "hero_products_count": len(insights.hero_products),
                "faqs_count": len(insights.faqs),
                "social_platforms_found": sum(1 for platform in ['instagram', 'facebook', 'twitter', 'tiktok', 'youtube', 'linkedin', 'pinterest'] 
                                            if getattr(insights.social_handles, platform)),
                "contact_methods": {
                    "emails": len(insights.contact_details.emails),
                    "phones": len(insights.contact_details.phone_numbers),
                    "has_address": bool(insights.contact_details.address)
                },
                "policies_found": sum(1 for policy in ['privacy_policy_url', 'return_policy_url', 'refund_policy_url', 'terms_of_service_url'] 
                                    if getattr(insights.policies, policy)),
                "extraction_errors": len(insights.errors)
            }
            
            validation_prompt = f"""
            Perform a comprehensive quality assessment of data extracted from Shopify store {url}:
            
            {json.dumps(insights_summary, indent=2)}
            
            Evaluate the overall quality and completeness:
            1. Is the brand information comprehensive?
            2. Are product counts reasonable for a Shopify store?
            3. Is social media presence adequately captured?
            4. Are essential e-commerce policies present?
            5. Is contact information sufficient for customer support?
            6. Are there any major gaps in the extracted data?
            
            Rate overall extraction quality from 0-1 and provide specific feedback.
            
            Respond with JSON in this format:
            {{
                "overall_quality": number,
                "completeness_score": number,
                "areas_of_concern": ["list of concerns"],
                "recommendations": ["specific improvement recommendations"],
                "data_gaps": ["missing data that should be present"]
            }}
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=validation_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            
            if response.text:
                validation_data = json.loads(response.text)
                
                # Compile validation notes
                validation_notes = []
                validation_notes.extend(validation_data.get('areas_of_concern', []))
                validation_notes.extend(validation_data.get('recommendations', []))
                validation_notes.extend(validation_data.get('data_gaps', []))
                
                return AIValidationResult(
                    validated=True,
                    confidence_score=validation_data.get('overall_quality', 0.0),
                    validation_notes=validation_notes
                )
            
        except Exception as e:
            logger.error(f"Error in comprehensive validation: {e}")
        
        return AIValidationResult()
    
    async def _extract_policies_from_html(self, url: str, html_content: str) -> Optional[PolicyInfo]:
        """Use AI to extract policy information and content from HTML structure"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove navigation elements for cleaner analysis
            for element in soup(['nav', 'header', 'footer', 'menu', 'aside']):
                element.extract()
            
            # Look for policy-related links with better filtering
            policy_links = []
            for link in soup.find_all('a', href=True):
                href = link['href'].lower()
                text = link.get_text().lower().strip()
                
                # Filter out obvious non-policy links
                if any(skip in text for skip in ['shop', 'product', 'collection', 'cart', 'account login']):
                    continue
                    
                if any(keyword in href or keyword in text for keyword in ['policy', 'terms', 'privacy', 'return', 'refund']):
                    policy_links.append({"url": urljoin(url, link['href']), "text": text})
            
            if not policy_links:
                return None
            
            # Use AI to categorize policy URLs
            extraction_prompt = f"""
            Extract and categorize policy URLs from these links found on {url}:
            {json.dumps(policy_links, indent=2)}
            
            Categorize them into policy types:
            - Privacy Policy (data protection, privacy practices)
            - Return Policy (returns, exchanges, refunds)
            - Terms of Service (terms of use, user agreements)
            
            Respond with JSON in this format:
            {{
                "privacy_policy_url": "full URL or null",
                "return_policy_url": "full URL or null",
                "terms_of_service_url": "full URL or null"
            }}
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=extraction_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            
            if response.text:
                policy_data = json.loads(response.text)
                policy_info = PolicyInfo()
                
                # Extract actual content from policy URLs
                for policy_type, policy_url in policy_data.items():
                    if policy_url and policy_url != "null":
                        try:
                            policy_response = self.session.get(policy_url, timeout=10)
                            if policy_response.status_code == 200:
                                policy_soup = BeautifulSoup(policy_response.text, 'html.parser')
                                
                                # Remove navigation from policy page
                                for element in policy_soup(['nav', 'header', 'footer', 'menu']):
                                    element.extract()
                                
                                # Extract main content
                                content = policy_soup.get_text()[:3000]  # Limit content size
                                content = ' '.join(content.split())  # Clean whitespace
                                
                                if policy_type == "privacy_policy_url":
                                    policy_info.privacy_policy_url = policy_url
                                    policy_info.privacy_policy_content = content
                                elif policy_type == "return_policy_url":
                                    policy_info.return_policy_url = policy_url
                                    policy_info.return_policy_content = content
                                elif policy_type == "terms_of_service_url":
                                    policy_info.terms_of_service_url = policy_url
                                    policy_info.terms_of_service_content = content
                                    
                        except Exception as e:
                            logger.warning(f"Could not fetch content from {policy_url}: {e}")
                            # Still save the URL even if content fetch fails
                            if policy_type == "privacy_policy_url":
                                policy_info.privacy_policy_url = policy_url
                            elif policy_type == "return_policy_url":
                                policy_info.return_policy_url = policy_url
                            elif policy_type == "terms_of_service_url":
                                policy_info.terms_of_service_url = policy_url
                
                return policy_info
            
        except Exception as e:
            logger.error(f"Error extracting policies from HTML: {e}")
        
        return None
    
    async def _extract_brand_from_html(self, url: str, html_content: str) -> Optional[BrandContext]:
        """Use AI to extract brand context from HTML structure"""
        try:
            # Clean and limit HTML content for AI analysis
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
            
            # Get text content with some structure
            text_content = soup.get_text()[:5000]  # Limit to first 5000 chars
            
            extraction_prompt = f"""
            Analyze this HTML content from {url} and extract brand information:
            
            {text_content}
            
            Extract the following brand information:
            1. Brand/Company name
            2. Brand description or tagline
            3. About us information
            4. Mission statement or brand story
            
            Focus on finding the most relevant and authentic brand information.
            
            Respond with JSON in this format:
            {{
                "brand_name": "extracted brand name",
                "brand_description": "brief brand description",
                "about_us_content": "about us content if found",
                "brand_story": "brand story or mission if found"
            }}
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=extraction_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            
            if response.text:
                brand_data = json.loads(response.text)
                return BrandContext(
                    brand_name=brand_data.get('brand_name'),
                    brand_description=brand_data.get('brand_description'),
                    about_us_content=brand_data.get('about_us_content'),
                    brand_story=brand_data.get('brand_story')
                )
            
        except Exception as e:
            logger.error(f"Error extracting brand from HTML: {e}")
        
        return None
    
    async def _extract_socials_from_html(self, url: str, html_content: str) -> Optional[SocialHandles]:
        """Use AI to extract social media handles from HTML"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for social links
            social_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if any(platform in href.lower() for platform in ['instagram', 'facebook', 'twitter', 'tiktok', 'youtube', 'linkedin', 'pinterest']):
                    social_links.append(href)
            
            if not social_links:
                return None
            
            extraction_prompt = f"""
            Extract social media handles from these links found on {url}:
            {json.dumps(social_links, indent=2)}
            
            For each platform, extract the username/handle:
            
            Respond with JSON in this format:
            {{
                "instagram": "@username or null",
                "facebook": "@username or null",
                "twitter": "@username or null",
                "tiktok": "@username or null",
                "youtube": "@username or null",
                "linkedin": "@username or null",
                "pinterest": "@username or null"
            }}
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=extraction_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            
            if response.text:
                social_data = json.loads(response.text)
                return SocialHandles(**social_data)
            
        except Exception as e:
            logger.error(f"Error extracting socials from HTML: {e}")
        
        return None
    
    async def _extract_contact_from_html(self, url: str, html_content: str) -> Optional[ContactDetails]:
        """Use AI to extract contact details from HTML"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text()[:3000]
            
            extraction_prompt = f"""
            Extract contact information from this content from {url}:
            
            {text_content}
            
            Look for:
            1. Email addresses
            2. Phone numbers
            3. Physical addresses
            
            Respond with JSON in this format:
            {{
                "emails": ["list of email addresses"],
                "phone_numbers": ["list of phone numbers"],
                "address": "physical address if found"
            }}
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=extraction_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            
            if response.text:
                contact_data = json.loads(response.text)
                return ContactDetails(
                    emails=contact_data.get('emails', []),
                    phone_numbers=contact_data.get('phone_numbers', []),
                    address=contact_data.get('address')
                )
            
        except Exception as e:
            logger.error(f"Error extracting contact from HTML: {e}")
        
        return None
    
    async def _extract_faqs_from_html(self, url: str, html_content: str) -> Optional[List[FAQ]]:
        """Use AI to extract FAQs from HTML structure with better targeting"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove navigation, header, footer, and menu elements completely
            for element in soup(['nav', 'header', 'footer', 'menu', 'aside']):
                element.extract()
            
            # Remove elements with navigation/menu classes
            nav_selectors = [
                '[class*="nav"]', '[class*="menu"]', '[class*="header"]', 
                '[class*="footer"]', '[class*="sidebar"]', '[id*="nav"]',
                '[id*="menu"]', '[class*="breadcrumb"]'
            ]
            for selector in nav_selectors:
                for element in soup.select(selector):
                    element.extract()
            
            # Look for FAQ-specific sections with priority order
            faq_sections = []
            
            # Priority 1: Dedicated FAQ sections
            faq_selectors = [
                '.faq', '.faqs', '.frequently-asked-questions',
                '#faq', '#faqs', '#frequently-asked-questions',
                '[class*="faq"]', '[id*="faq"]',
                '.questions', '.help-center', '.support-center',
                '.customer-support', '.help-section'
            ]
            
            for selector in faq_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text().strip()
                    if len(text) > 100:  # Ensure substantial content
                        faq_sections.append(text[:2000])  # Increase limit for FAQs
            
            # Priority 2: Look for FAQ pages linked from main page
            if not faq_sections:
                faq_links = []
                for link in soup.find_all('a', href=True):
                    href = link['href'].lower()
                    text = link.get_text().lower()
                    if any(keyword in href or keyword in text for keyword in ['faq', 'help', 'support', 'question']):
                        faq_links.append(urljoin(url, link['href']))
                
                # Try to fetch content from FAQ links
                for faq_url in faq_links[:2]:  # Limit to 2 FAQ pages
                    try:
                        response = self.session.get(faq_url, timeout=10)
                        if response.status_code == 200:
                            faq_soup = BeautifulSoup(response.text, 'html.parser')
                            # Remove navigation from FAQ page too
                            for element in faq_soup(['nav', 'header', 'footer', 'menu']):
                                element.extract()
                            faq_content = faq_soup.get_text()[:3000]
                            if len(faq_content) > 200:
                                faq_sections.append(faq_content)
                    except Exception as e:
                        logger.warning(f"Could not fetch FAQ page {faq_url}: {e}")
                        continue
            
            # Priority 3: Search for question patterns in main content
            if not faq_sections:
                main_content = soup.get_text()[:5000]
                # Look for question patterns
                import re
                question_pattern = r'[A-Z][^.!?]*\?'
                questions = re.findall(question_pattern, main_content)
                if len(questions) >= 3:  # At least 3 questions found
                    faq_sections = [main_content]
            
            extraction_prompt = f"""
            Extract ONLY genuine FAQ (Frequently Asked Questions) content from {url}.
            
            IGNORE navigation menus, product categories, and shopping links such as:
            - "SHOP FOR WOMEN", "DIY HAIR EXTENSIONS", "HAIR LOSS SOLUTION"
            - Product category listings or menu items
            
            LOOK FOR actual customer service questions about:
            - Product usage, care, and sizing
            - Shipping, returns, and exchanges
            - Account management and ordering
            - Payment and billing questions
            
            Content to analyze:
            {' '.join(faq_sections)}
            
            Only extract genuine question-answer pairs where:
            - Questions end with '?' and sound like customer inquiries
            - Answers provide helpful, informative responses
            
            Respond with JSON in this format:
            {{
                "faqs": [
                    {{"question": "How do I care for my hair extensions?", "answer": "Detailed care instructions..."}},
                    ...
                ]
            }}
            
            If no genuine FAQs found, return empty faqs array.
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=extraction_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            
            if response.text:
                faq_data = json.loads(response.text)
                faqs = []
                for faq_item in faq_data.get('faqs', []):
                    if faq_item.get('question') and faq_item.get('answer'):
                        faqs.append(FAQ(
                            question=faq_item['question'],
                            answer=faq_item['answer']
                        ))
                return faqs
            
        except Exception as e:
            logger.error(f"Error extracting FAQs from HTML: {e}")
        
        return None