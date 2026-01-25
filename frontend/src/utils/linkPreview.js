/**
 * Link preview utility for fetching metadata from music platforms and other URLs.
 * Supports Spotify, YouTube Music, Apple Music, and general Open Graph.
 */

/**
 * Extract URLs from text content
 */
export function extractUrls(text) {
    if (!text) return [];
    // Regex pattern to match URLs
    const urlPattern = /https?:\/\/[^\s<>"{}|\\^`\[\]]+/g;
    return text.match(urlPattern) || [];
}

/**
 * Check if URL is from a supported music platform
 */
export function isMusicPlatformUrl(url) {
    try {
        const urlObj = new URL(url);
        const domain = urlObj.hostname.toLowerCase().replace(/^www\./, '');
        
        const spotifyDomains = ['open.spotify.com', 'spotify.com'];
        const youtubeDomains = ['youtube.com', 'youtu.be', 'music.youtube.com'];
        const appleMusicDomains = ['music.apple.com', 'itunes.apple.com'];
        
        return (
            spotifyDomains.some(d => domain === d || domain.endsWith('.' + d)) ||
            youtubeDomains.some(d => domain === d || domain.endsWith('.' + d)) ||
            appleMusicDomains.some(d => domain === d || domain.endsWith('.' + d))
        );
    } catch (e) {
        return false;
    }
}

/**
 * Extract YouTube video ID from various URL formats
 */
function extractYouTubeVideoId(url) {
    try {
        const urlObj = new URL(url);
        
        // Standard format: youtube.com/watch?v=VIDEO_ID
        if (['www.youtube.com', 'youtube.com', 'music.youtube.com'].includes(urlObj.hostname)) {
            if (urlObj.pathname === '/watch') {
                return urlObj.searchParams.get('v');
            }
            // Short format: youtube.com/VIDEO_ID
            if (urlObj.pathname.startsWith('/')) {
                return urlObj.pathname.slice(1);
            }
        }
        
        // Short URL format: youtu.be/VIDEO_ID
        if (urlObj.hostname === 'youtu.be') {
            return urlObj.pathname.slice(1);
        }
    } catch (e) {
        // Invalid URL
    }
    return null;
}

/**
 * Parse Open Graph metadata from HTML
 */
function parseOpenGraph(html, url, provider) {
    try {
        const ogData = {};
        
        // Extract og:title
        const titleMatch = html.match(/<meta\s+property=["']og:title["']\s+content=["']([^"']+)["']/i);
        if (titleMatch) {
            ogData.title = titleMatch[1];
        }
        
        // Extract og:description
        const descMatch = html.match(/<meta\s+property=["']og:description["']\s+content=["']([^"']+)["']/i);
        if (descMatch) {
            ogData.description = descMatch[1];
        }
        
        // Extract og:image
        const imageMatch = html.match(/<meta\s+property=["']og:image["']\s+content=["']([^"']+)["']/i);
        if (imageMatch) {
            ogData.thumbnail_url = imageMatch[1];
        }
        
        // Extract og:type
        const typeMatch = html.match(/<meta\s+property=["']og:type["']\s+content=["']([^"']+)["']/i);
        if (typeMatch) {
            ogData.type = typeMatch[1];
        }
        
        // Fallback to title tag if og:title not found
        if (!ogData.title) {
            const titleTagMatch = html.match(/<title>([^<]+)<\/title>/i);
            if (titleTagMatch) {
                ogData.title = titleTagMatch[1].trim();
            }
        }
        
        if (Object.keys(ogData).length > 0) {
            return {
                url,
                type: ogData.type || 'website',
                title: ogData.title || '',
                description: ogData.description || '',
                thumbnail_url: ogData.thumbnail_url || '',
                provider
            };
        }
    } catch (e) {
        console.warn('Error parsing Open Graph:', e);
    }
    return null;
}

/**
 * Fetch preview from Spotify using oEmbed API
 */
async function fetchSpotifyPreview(url) {
    try {
        const oembedUrl = `https://embed.spotify.com/oembed?url=${encodeURIComponent(url)}`;
        const response = await fetch(oembedUrl);
        
        if (response.ok) {
            const data = await response.json();
            return {
                url,
                type: 'spotify',
                title: data.title || '',
                description: data.description || '',
                thumbnail_url: data.thumbnail_url || '',
                embed_html: data.html || '',
                provider: 'Spotify'
            };
        }
    } catch (e) {
        console.warn('Failed to fetch Spotify preview:', e);
    }
    return null;
}

/**
 * Fetch preview from YouTube/YouTube Music using oEmbed API
 */
async function fetchYouTubePreview(url) {
    try {
        const videoId = extractYouTubeVideoId(url);
        if (!videoId) return null;
        
        const oembedUrl = `https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${videoId}&format=json`;
        const response = await fetch(oembedUrl);
        
        if (response.ok) {
            const data = await response.json();
            return {
                url,
                type: 'youtube',
                title: data.title || '',
                author_name: data.author_name || '',
                thumbnail_url: data.thumbnail_url || '',
                thumbnail_width: data.thumbnail_width,
                thumbnail_height: data.thumbnail_height,
                embed_html: data.html || '',
                provider: url.includes('music.youtube.com') ? 'YouTube Music' : 'YouTube'
            };
        }
    } catch (e) {
        console.warn('Failed to fetch YouTube preview:', e);
    }
    return null;
}

/**
 * Fetch preview from Apple Music using oEmbed API or Open Graph fallback
 */
async function fetchAppleMusicPreview(url) {
    // Try oEmbed first
    try {
        // Apple Music oEmbed endpoint - try different possible formats
        const oembedUrl = `https://embed.music.apple.com/oembed?url=${encodeURIComponent(url)}`;
        const response = await fetch(oembedUrl, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            return {
                url,
                type: 'apple_music',
                title: data.title || '',
                author_name: data.author_name || '',
                thumbnail_url: data.thumbnail_url || '',
                thumbnail_width: data.thumbnail_width,
                thumbnail_height: data.thumbnail_height,
                embed_html: data.html || '',
                provider: 'Apple Music'
            };
        }
    } catch (e) {
        console.warn('Apple Music oEmbed failed, trying Open Graph:', e);
    }
    
    // Fallback to Open Graph if oEmbed fails
    try {
        // Use a CORS proxy or try direct fetch
        // Note: Direct fetch may fail due to CORS, but some browsers/servers allow it
        const response = await fetch(url, {
            method: 'GET',
            mode: 'cors',
            headers: {
                'User-Agent': 'Mozilla/5.0 (compatible; LinkPreviewBot/1.0)'
            }
        });
        
        if (response.ok) {
            const html = await response.text();
            const preview = parseOpenGraph(html, url, 'Apple Music');
            if (preview) {
                return preview;
            }
        }
    } catch (e) {
        console.warn('Failed to fetch Apple Music preview via Open Graph:', e);
        // If CORS blocks us, try using a public CORS proxy as last resort
        try {
            const proxyUrl = `https://api.allorigins.win/get?url=${encodeURIComponent(url)}`;
            const proxyResponse = await fetch(proxyUrl);
            if (proxyResponse.ok) {
                const proxyData = await proxyResponse.json();
                const html = proxyData.contents;
                const preview = parseOpenGraph(html, url, 'Apple Music');
                if (preview) {
                    return preview;
                }
            }
        } catch (proxyError) {
            console.warn('Failed to fetch Apple Music preview via proxy:', proxyError);
        }
    }
    
    return null;
}

/**
 * Fetch preview using Open Graph metadata
 */
async function fetchOpenGraphPreview(url) {
    try {
        // Try direct fetch first
        const response = await fetch(url, {
            method: 'GET',
            mode: 'cors',
            headers: {
                'User-Agent': 'Mozilla/5.0 (compatible; LinkPreviewBot/1.0)'
            }
        });
        
        if (response.ok) {
            const html = await response.text();
            const urlObj = new URL(url);
            const provider = urlObj.hostname.replace('www.', '');
            const preview = parseOpenGraph(html, url, provider);
            if (preview) {
                return preview;
            }
        }
    } catch (e) {
        console.warn('Failed to fetch Open Graph preview directly, trying proxy:', e);
        // If CORS blocks us, try using a public CORS proxy
        try {
            const proxyUrl = `https://api.allorigins.win/get?url=${encodeURIComponent(url)}`;
            const proxyResponse = await fetch(proxyUrl);
            if (proxyResponse.ok) {
                const proxyData = await proxyResponse.json();
                const html = proxyData.contents;
                const urlObj = new URL(url);
                const provider = urlObj.hostname.replace('www.', '');
                return parseOpenGraph(html, url, provider);
            }
        } catch (proxyError) {
            console.warn('Failed to fetch Open Graph preview via proxy:', proxyError);
        }
    }
    return null;
}

/**
 * Fetch link preview metadata for a given URL
 * Returns null if preview cannot be fetched
 */
export async function fetchLinkPreview(url, timeout = 5000) {
    try {
        const urlObj = new URL(url);
        const domain = urlObj.hostname.toLowerCase().replace(/^www\./, '');
        
        // Spotify
        if (domain === 'open.spotify.com' || domain === 'spotify.com' || domain.endsWith('.spotify.com')) {
            return await fetchSpotifyPreview(url);
        }
        
        // YouTube/YouTube Music
        if (domain === 'youtube.com' || domain === 'youtu.be' || domain === 'music.youtube.com' || domain.endsWith('.youtube.com')) {
            return await fetchYouTubePreview(url);
        }
        
        // Apple Music
        if (domain === 'music.apple.com' || domain === 'itunes.apple.com' || domain.endsWith('.apple.com')) {
            return await fetchAppleMusicPreview(url);
        }
        
        // Fallback to Open Graph
        return await fetchOpenGraphPreview(url);
    } catch (e) {
        console.error('Error fetching link preview:', e);
        return null;
    }
}
