"""
Link preview service for fetching rich metadata from music platforms and other URLs.
Supports Spotify, YouTube Music, Apple Music, and general Open Graph/oEmbed.
"""
import re
import logging
from typing import Optional, Dict, Any
import httpx
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class LinkPreviewService:
    """Service for fetching link previews from various platforms."""
    
    # Supported music platform domains
    SPOTIFY_DOMAINS = ['open.spotify.com', 'spotify.com']
    YOUTUBE_DOMAINS = ['youtube.com', 'youtu.be', 'music.youtube.com']
    APPLE_MUSIC_DOMAINS = ['music.apple.com', 'itunes.apple.com']
    
    @staticmethod
    def extract_urls(text: str) -> list[str]:
        """Extract URLs from text content."""
        # Regex pattern to match URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        return urls
    
    @staticmethod
    def is_music_platform_url(url: str) -> bool:
        """Check if URL is from a supported music platform."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove 'www.' prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            
            return (
                any(domain == d or domain.endswith('.' + d) for d in LinkPreviewService.SPOTIFY_DOMAINS) or
                any(domain == d or domain.endswith('.' + d) for d in LinkPreviewService.YOUTUBE_DOMAINS) or
                any(domain == d or domain.endswith('.' + d) for d in LinkPreviewService.APPLE_MUSIC_DOMAINS)
            )
        except Exception as e:
            logger.warning(f"Error parsing URL {url}: {e}")
            return False
    
    @staticmethod
    async def fetch_preview(url: str, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """
        Fetch link preview metadata for a given URL.
        Returns None if preview cannot be fetched.
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove 'www.' prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Spotify
            if any(domain == d or domain.endswith('.' + d) for d in LinkPreviewService.SPOTIFY_DOMAINS):
                return await LinkPreviewService._fetch_spotify_preview(url)
            
            # YouTube/YouTube Music
            if any(domain == d or domain.endswith('.' + d) for d in LinkPreviewService.YOUTUBE_DOMAINS):
                return await LinkPreviewService._fetch_youtube_preview(url)
            
            # Apple Music
            if any(domain == d or domain.endswith('.' + d) for d in LinkPreviewService.APPLE_MUSIC_DOMAINS):
                return await LinkPreviewService._fetch_apple_music_preview(url)
            
            # Fallback to Open Graph
            return await LinkPreviewService._fetch_opengraph_preview(url, timeout)
            
        except Exception as e:
            logger.error(f"Error fetching preview for {url}: {e}")
            return None
    
    @staticmethod
    async def _fetch_spotify_preview(url: str) -> Optional[Dict[str, Any]]:
        """Fetch preview from Spotify using oEmbed API."""
        try:
            # Spotify oEmbed endpoint
            oembed_url = "https://embed.spotify.com/oembed"
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    oembed_url,
                    params={"url": url}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "url": url,
                        "type": "spotify",
                        "title": data.get("title", ""),
                        "description": data.get("description", ""),
                        "thumbnail_url": data.get("thumbnail_url", ""),
                        "embed_html": data.get("html", ""),
                        "provider": "Spotify"
                    }
        except Exception as e:
            logger.warning(f"Failed to fetch Spotify preview: {e}")
        
        return None
    
    @staticmethod
    async def _fetch_youtube_preview(url: str) -> Optional[Dict[str, Any]]:
        """Fetch preview from YouTube/YouTube Music using oEmbed API."""
        try:
            # Extract video ID from various YouTube URL formats
            video_id = LinkPreviewService._extract_youtube_video_id(url)
            if not video_id:
                return None
            
            # YouTube oEmbed endpoint
            oembed_url = "https://www.youtube.com/oembed"
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    oembed_url,
                    params={
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "format": "json"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "url": url,
                        "type": "youtube",
                        "title": data.get("title", ""),
                        "author_name": data.get("author_name", ""),
                        "thumbnail_url": data.get("thumbnail_url", ""),
                        "thumbnail_width": data.get("thumbnail_width"),
                        "thumbnail_height": data.get("thumbnail_height"),
                        "embed_html": data.get("html", ""),
                        "provider": "YouTube Music" if "music.youtube.com" in url else "YouTube"
                    }
        except Exception as e:
            logger.warning(f"Failed to fetch YouTube preview: {e}")
        
        return None
    
    @staticmethod
    def _extract_youtube_video_id(url: str) -> Optional[str]:
        """Extract YouTube video ID from various URL formats."""
        try:
            parsed = urlparse(url)
            
            # Standard format: youtube.com/watch?v=VIDEO_ID
            if parsed.netloc in ['www.youtube.com', 'youtube.com', 'music.youtube.com']:
                if parsed.path == '/watch':
                    query_params = parse_qs(parsed.query)
                    return query_params.get('v', [None])[0]
                # Short format: youtube.com/VIDEO_ID
                elif parsed.path.startswith('/'):
                    return parsed.path[1:]
            
            # Short URL format: youtu.be/VIDEO_ID
            elif parsed.netloc == 'youtu.be':
                return parsed.path[1:] if parsed.path.startswith('/') else parsed.path
                
        except Exception as e:
            logger.warning(f"Error extracting YouTube video ID: {e}")
        
        return None
    
    @staticmethod
    async def _fetch_apple_music_preview(url: str) -> Optional[Dict[str, Any]]:
        """Fetch preview from Apple Music using Open Graph metadata."""
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                response = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; LinkPreviewBot/1.0)"
                })
                
                if response.status_code == 200:
                    html = response.text
                    return LinkPreviewService._parse_opengraph(html, url, "Apple Music")
        except Exception as e:
            logger.warning(f"Failed to fetch Apple Music preview: {e}")
        
        return None
    
    @staticmethod
    async def _fetch_opengraph_preview(url: str, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Fetch preview using Open Graph metadata."""
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; LinkPreviewBot/1.0)"
                })
                
                if response.status_code == 200:
                    html = response.text
                    parsed = urlparse(url)
                    provider = parsed.netloc.replace('www.', '')
                    return LinkPreviewService._parse_opengraph(html, url, provider)
        except Exception as e:
            logger.warning(f"Failed to fetch Open Graph preview: {e}")
        
        return None
    
    @staticmethod
    def _parse_opengraph(html: str, url: str, provider: str) -> Optional[Dict[str, Any]]:
        """Parse Open Graph metadata from HTML."""
        try:
            # Simple regex-based parsing (could be improved with BeautifulSoup)
            og_data = {}
            
            # Extract og:title
            title_match = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if title_match:
                og_data['title'] = title_match.group(1)
            
            # Extract og:description
            desc_match = re.search(r'<meta\s+property=["\']og:description["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if desc_match:
                og_data['description'] = desc_match.group(1)
            
            # Extract og:image
            image_match = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if image_match:
                og_data['thumbnail_url'] = image_match.group(1)
            
            # Extract og:type
            type_match = re.search(r'<meta\s+property=["\']og:type["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if type_match:
                og_data['type'] = type_match.group(1)
            
            # Fallback to title tag if og:title not found
            if 'title' not in og_data:
                title_tag_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
                if title_tag_match:
                    og_data['title'] = title_tag_match.group(1).strip()
            
            if og_data:
                return {
                    "url": url,
                    "type": og_data.get('type', 'website'),
                    "title": og_data.get('title', ''),
                    "description": og_data.get('description', ''),
                    "thumbnail_url": og_data.get('thumbnail_url', ''),
                    "provider": provider
                }
        except Exception as e:
            logger.warning(f"Error parsing Open Graph: {e}")
        
        return None
