/**
 * Text utility functions for processing and formatting text content.
 */

import { extractUrls } from './linkPreview';

/**
 * Convert URLs in text to clickable React link elements
 * @param {string} text - The text content
 * @returns {Array} - Array of parts (strings or link objects)
 */
export function linkifyText(text) {
    if (!text) return [];
    
    const urlPattern = /https?:\/\/[^\s<>"{}|\\^`\[\]]+/g;
    const parts = [];
    let lastIndex = 0;
    let match;
    
    // Reset regex lastIndex
    urlPattern.lastIndex = 0;
    
    while ((match = urlPattern.exec(text)) !== null) {
        const url = match[0];
        const index = match.index;
        
        // Add text before the URL
        if (index > lastIndex) {
            const textBefore = text.substring(lastIndex, index);
            if (textBefore) {
                parts.push(textBefore);
            }
        }
        
        // Add the URL as a link object
        parts.push({
            type: 'link',
            url,
            text: url
        });
        
        lastIndex = index + url.length;
    }
    
    // Add remaining text after the last URL
    if (lastIndex < text.length) {
        const textAfter = text.substring(lastIndex);
        if (textAfter) {
            parts.push(textAfter);
        }
    }
    
    // If no URLs were found, return the original text
    if (parts.length === 0) {
        return [text];
    }
    
    return parts;
}
