import logging
import re
from typing import List
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from models import SocialHandles

logger = logging.getLogger(__name__)

class SocialScraperService:
    """Service for scraping social media handles from Shopify stores"""
    
    def __init__(self, session: requests.Session):
        self.session = session
    
    async def get_social_handles(self, base_url: str) -> SocialHandles:
        """
        Extract social media handles
        
        Args:
            base_url: The base URL of the Shopify store
            
        Returns:
            SocialHandles: Social media information
        """
        social_handles = SocialHandles()
        
        try:
            response = self.session.get(base_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get all text content to search for handles
            page_text = soup.get_text()
            
            # Find all links
            all_links = soup.find_all('a', href=True)
            social_links = []
            
            for link in all_links:
                href = link.get('href', '')
                if self._is_social_link(href):
                    social_links.append(href)
            
            # Extract handles from links
            social_handles = self._extract_handles_from_links(social_links)
            
            # Also look for handles in text (like @username mentions)
            text_handles = self._extract_handles_from_text(page_text)
            
            # Merge results
            for platform, handle in text_handles.items():
                if not getattr(social_handles, platform) and handle:
                    setattr(social_handles, platform, handle)
            
            return social_handles
            
        except Exception as e:
            logger.error(f"Error extracting social handles: {e}")
            return social_handles
    
    def _is_social_link(self, url: str) -> bool:
        """Check if a URL is a social media link"""
        social_domains = [
            'instagram.com',
            'facebook.com',
            'tiktok.com',
            'twitter.com',
            'x.com',
            'youtube.com',
            'linkedin.com',
            'pinterest.com',
            'snapchat.com',
            'whatsapp.com'
        ]
        
        return any(domain in url.lower() for domain in social_domains)
    
    def _extract_handles_from_links(self, links: List[str]) -> SocialHandles:
        """Extract social media handles from links"""
        social_handles = SocialHandles()
        
        for link in links:
            link_lower = link.lower()
            
            # Instagram
            if 'instagram.com' in link_lower:
                handle = self._extract_handle_from_url(link, 'instagram.com')
                if handle:
                    social_handles.instagram = handle
            
            # Facebook
            elif 'facebook.com' in link_lower:
                handle = self._extract_handle_from_url(link, 'facebook.com')
                if handle:
                    social_handles.facebook = handle
            
            # TikTok
            elif 'tiktok.com' in link_lower:
                handle = self._extract_handle_from_url(link, 'tiktok.com')
                if handle:
                    social_handles.tiktok = handle
            
            # Twitter/X
            elif 'twitter.com' in link_lower or 'x.com' in link_lower:
                domain = 'twitter.com' if 'twitter.com' in link_lower else 'x.com'
                handle = self._extract_handle_from_url(link, domain)
                if handle:
                    social_handles.twitter = handle
            
            # YouTube
            elif 'youtube.com' in link_lower:
                handle = self._extract_youtube_handle(link)
                if handle:
                    social_handles.youtube = handle
            
            # LinkedIn
            elif 'linkedin.com' in link_lower:
                handle = self._extract_handle_from_url(link, 'linkedin.com')
                if handle:
                    social_handles.linkedin = handle
            
            # Pinterest
            elif 'pinterest.com' in link_lower:
                handle = self._extract_handle_from_url(link, 'pinterest.com')
                if handle:
                    social_handles.pinterest = handle
        
        return social_handles
    
    def _extract_handle_from_url(self, url: str, domain: str) -> str:
        """Extract handle from social media URL"""
        try:
            # Remove protocol and domain
            path = url.split(domain)[-1]
            
            # Remove leading slash
            path = path.lstrip('/')
            
            # Split by slash and take first part
            handle = path.split('/')[0]
            
            # Remove query parameters
            handle = handle.split('?')[0]
            
            # Clean up common prefixes/suffixes
            handle = handle.replace('@', '')
            
            # Validate handle (basic validation)
            if len(handle) > 2 and handle.isalnum() or '_' in handle or '.' in handle:
                return f"@{handle}"
            
        except Exception as e:
            logger.warning(f"Error extracting handle from {url}: {e}")
        
        return None
    
    def _extract_youtube_handle(self, url: str) -> str:
        """Extract YouTube handle/channel name"""
        try:
            if '/channel/' in url:
                channel_id = url.split('/channel/')[-1].split('?')[0].split('/')[0]
                return f"Channel ID: {channel_id}"
            elif '/user/' in url:
                username = url.split('/user/')[-1].split('?')[0].split('/')[0]
                return f"@{username}"
            elif '/c/' in url:
                channel_name = url.split('/c/')[-1].split('?')[0].split('/')[0]
                return f"@{channel_name}"
            elif '/@' in url:
                handle = url.split('/@')[-1].split('?')[0].split('/')[0]
                return f"@{handle}"
            
        except Exception as e:
            logger.warning(f"Error extracting YouTube handle from {url}: {e}")
        
        return None
    
    def _extract_handles_from_text(self, text: str) -> dict:
        """Extract social media handles mentioned in text"""
        handles = {}
        
        # Instagram handle pattern
        instagram_pattern = r'@([a-zA-Z0-9._]{1,30})'
        instagram_matches = re.findall(instagram_pattern, text)
        
        # Look for context clues
        text_lower = text.lower()
        
        for match in instagram_matches:
            # Check if it's likely an Instagram handle based on context
            if any(keyword in text_lower for keyword in ['instagram', 'insta', 'ig']):
                if not handles.get('instagram'):
                    handles['instagram'] = f"@{match}"
                break
        
        # Twitter handle pattern
        if any(keyword in text_lower for keyword in ['twitter', 'tweet']):
            for match in instagram_matches:  # Same pattern works for Twitter
                if not handles.get('twitter'):
                    handles['twitter'] = f"@{match}"
                    break
        
        return handles
