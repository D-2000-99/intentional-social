/**
 * Generate a pastel color from a string (tag name)
 * Uses a simple hash function to ensure consistent colors for the same string
 */
export function getPastelColorFromString(str) {
    // Simple hash function
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    
    // Generate pastel colors by keeping values in a lighter range
    // Pastel colors have high lightness and medium saturation
    const hue = Math.abs(hash) % 360; // Full color spectrum
    const saturation = 40 + (Math.abs(hash) % 30); // 40-70% saturation for pastel
    const lightness = 75 + (Math.abs(hash) % 15); // 75-90% lightness for pastel
    
    return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
}

/**
 * Generate a darker color for text that contrasts well with the pastel background
 */
export function getContrastingTextColor(pastelColor) {
    // Extract lightness from HSL
    const match = pastelColor.match(/hsl\((\d+),\s*(\d+)%,\s*(\d+)%\)/);
    if (!match) return '#1e293b'; // Fallback dark color
    
    const lightness = parseInt(match[3]);
    
    // If background is light (pastel), use dark text
    // If background is darker, use light text
    return lightness > 80 ? '#1e293b' : '#f8fafc';
}

