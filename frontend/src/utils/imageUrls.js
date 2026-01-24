const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const API_ORIGIN = (() => {
    try {
        return new URL(API_URL).origin;
    } catch {
        return null;
    }
})();

const appendAuthToken = (resolvedUrl) => {
    const token = localStorage.getItem("token");
    if (!token) return resolvedUrl;

    try {
        const parsed = new URL(resolvedUrl, API_URL);
        if (API_ORIGIN && parsed.origin !== API_ORIGIN) {
            return resolvedUrl;
        }
        if (!parsed.pathname.startsWith("/images/")) {
            return resolvedUrl;
        }
        parsed.searchParams.set("token", token);
        return parsed.toString();
    } catch {
        return resolvedUrl;
    }
};

export const resolveImageUrl = (url) => {
    if (!url) return url;
    if (url.startsWith("http://") || url.startsWith("https://")) {
        return appendAuthToken(url);
    }
    if (url.startsWith("//")) {
        return appendAuthToken(`${window.location.protocol}${url}`);
    }
    if (url.startsWith("/")) {
        return appendAuthToken(`${API_URL}${url}`);
    }
    return appendAuthToken(`${API_URL}/${url}`);
};

export const resolveImageUrls = (urls = []) => urls.map(resolveImageUrl);
