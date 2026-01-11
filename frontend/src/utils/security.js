import DOMPurify from 'dompurify';

/**
 * Sanitize HTML content to prevent XSS attacks
 * @param {string} dirty - The potentially unsafe HTML string
 * @returns {string} - Sanitized HTML string
 */
export function sanitizeHtml(dirty) {
    if (!dirty) return '';
    return DOMPurify.sanitize(dirty, {
        ALLOWED_TAGS: [], // No HTML tags allowed, strip everything
        ALLOWED_ATTR: [],
        KEEP_CONTENT: true, // Keep the text content
    });
}

/**
 * Sanitize plain text content (removes HTML tags and escapes special characters)
 * @param {string} text - The text to sanitize
 * @returns {string} - Sanitized plain text
 */
export function sanitizeText(text) {
    if (!text) return '';
    // First remove any HTML tags
    const stripped = DOMPurify.sanitize(text, {
        ALLOWED_TAGS: [],
        ALLOWED_ATTR: [],
        KEEP_CONTENT: true,
    });
    // Escape HTML entities
    return DOMPurify.sanitize(stripped, {
        ALLOWED_TAGS: [],
        ALLOWED_ATTR: [],
    });
}

/**
 * Validate and sanitize a username
 * @param {string} username - Username to validate
 * @returns {object} - { isValid: boolean, sanitized: string, error: string }
 */
export function validateUsername(username) {
    if (!username) {
        return { isValid: false, sanitized: '', error: 'Username is required' };
    }
    
    // Remove any whitespace
    const trimmed = username.trim();
    
    if (trimmed.length < 3) {
        return { isValid: false, sanitized: trimmed, error: 'Username must be at least 3 characters' };
    }
    
    if (trimmed.length > 50) {
        return { isValid: false, sanitized: trimmed, error: 'Username must be less than 50 characters' };
    }
    
    // Only allow alphanumeric, underscore, and hyphen
    const usernameRegex = /^[a-zA-Z0-9_-]+$/;
    if (!usernameRegex.test(trimmed)) {
        return { isValid: false, sanitized: trimmed, error: 'Username can only contain letters, numbers, underscores, and hyphens' };
    }
    
    // Additional security: check for common injection patterns
    const dangerousPatterns = [
        /<script/i,
        /javascript:/i,
        /on\w+\s*=/i, // onclick=, onerror=, etc.
        /data:text\/html/i,
        /vbscript:/i,
    ];
    
    for (const pattern of dangerousPatterns) {
        if (pattern.test(trimmed)) {
            return { isValid: false, sanitized: '', error: 'Username contains invalid characters' };
        }
    }
    
    return { isValid: true, sanitized: trimmed, error: null };
}

/**
 * Validate post or comment content
 * @param {string} content - Content to validate
 * @param {number} maxLength - Maximum length (default: 10000 for posts)
 * @returns {object} - { isValid: boolean, sanitized: string, error: string }
 */
export function validateContent(content, maxLength = 10000) {
    if (!content) {
        return { isValid: false, sanitized: '', error: 'Content cannot be empty' };
    }
    
    const trimmed = content.trim();
    
    if (trimmed.length === 0) {
        return { isValid: false, sanitized: '', error: 'Content cannot be empty' };
    }
    
    if (trimmed.length > maxLength) {
        return { isValid: false, sanitized: trimmed, error: `Content must be less than ${maxLength} characters` };
    }
    
    // Check for dangerous patterns
    const dangerousPatterns = [
        /<script/i,
        /javascript:/i,
        /on\w+\s*=/i,
        /data:text\/html/i,
        /vbscript:/i,
        /<iframe/i,
        /<object/i,
        /<embed/i,
    ];
    
    for (const pattern of dangerousPatterns) {
        if (pattern.test(trimmed)) {
            return { isValid: false, sanitized: sanitizeText(trimmed), error: 'Content contains invalid characters' };
        }
    }
    
    // Sanitize the content (removes HTML but keeps text)
    const sanitized = sanitizeText(trimmed);
    
    return { isValid: true, sanitized, error: null };
}

/**
 * Validate and sanitize search query
 * @param {string} query - Search query to validate
 * @returns {object} - { isValid: boolean, sanitized: string, error: string }
 */
export function validateSearchQuery(query) {
    if (!query) {
        return { isValid: false, sanitized: '', error: 'Search query cannot be empty' };
    }
    
    const trimmed = query.trim();
    
    if (trimmed.length === 0) {
        return { isValid: false, sanitized: '', error: 'Search query cannot be empty' };
    }
    
    if (trimmed.length > 255) {
        return { isValid: false, sanitized: trimmed.substring(0, 255), error: 'Search query is too long' };
    }
    
    // Sanitize the query
    const sanitized = sanitizeText(trimmed);
    
    return { isValid: true, sanitized, error: null };
}

/**
 * Validate a URL to prevent open redirect attacks
 * @param {string} url - URL to validate
 * @param {Array<string>} allowedDomains - Array of allowed domains (default: empty, means same origin only)
 * @returns {boolean} - Whether the URL is safe
 */
export function isValidUrl(url, allowedDomains = []) {
    if (!url || typeof url !== 'string') {
        return false;
    }
    
    try {
        const urlObj = new URL(url);
        
        // Only allow http and https protocols
        if (!['http:', 'https:'].includes(urlObj.protocol)) {
            return false;
        }
        
        // If allowedDomains is empty, only allow same origin
        if (allowedDomains.length === 0) {
            // Check if it's the same origin
            if (typeof window !== 'undefined') {
                const currentOrigin = window.location.origin;
                return urlObj.origin === currentOrigin;
            }
            return false;
        }
        
        // Check if domain is in allowed list
        return allowedDomains.some(domain => {
            // Allow exact match or subdomain
            return urlObj.hostname === domain || urlObj.hostname.endsWith('.' + domain);
        });
    } catch (e) {
        // Invalid URL format
        return false;
    }
}

/**
 * Validate OAuth authorization URL
 * @param {string} url - OAuth URL to validate
 * @param {Array<string>} allowedOAuthDomains - Allowed OAuth provider domains
 * @returns {boolean} - Whether the URL is safe
 */
export function isValidOAuthUrl(url, allowedOAuthDomains = ['accounts.google.com']) {
    return isValidUrl(url, allowedOAuthDomains);
}

/**
 * Escape special characters in a string for safe display
 * @param {string} text - Text to escape
 * @returns {string} - Escaped text
 */
export function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;',
    };
    return String(text).replace(/[&<>"']/g, (m) => map[m]);
}

/**
 * Validate bio content
 * @param {string} bio - Bio text to validate
 * @returns {object} - { isValid: boolean, sanitized: string, error: string }
 */
export function validateBio(bio, maxLength = 500) {
    // Bio can be empty
    if (!bio || bio.trim().length === 0) {
        return { isValid: true, sanitized: '', error: null };
    }
    
    return validateContent(bio, maxLength);
}

/**
 * Sanitize URL parameter (e.g., username from route params)
 * @param {string} param - URL parameter value
 * @returns {string} - Sanitized parameter
 */
export function sanitizeUrlParam(param) {
    if (!param) return '';
    // Remove any characters that could be used for injection
    return param.replace(/[<>"'`]/g, '').substring(0, 100);
}

