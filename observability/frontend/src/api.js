// Use environment variable for API URL, fallback to localhost for development
const API_URL = import.meta.env.VITE_OBSERVABILITY_API_URL || "http://localhost:8002";

export const api = {
  async request(endpoint, method = "GET", body = null, token = null) {
    const headers = {};

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const config = {
      method,
      headers,
    };

    // For POST/PUT requests, always send a body (even if empty) to avoid issues
    if (method === "POST" || method === "PUT") {
      headers["Content-Type"] = "application/json";
      config.body = JSON.stringify(body || {});
    } else if (body) {
      // For other methods, only set Content-Type if we have a body
      headers["Content-Type"] = "application/json";
      config.body = JSON.stringify(body);
    }

    try {
      const url = `${API_URL}${endpoint}`;
      const response = await fetch(url, config);

      // Parse response body as JSON (our API always returns JSON)
      // Clone response first so we can try both JSON and text if needed
      const clonedResponse = response.clone();
      let data;
      
      try {
        data = await response.json();
      } catch (jsonError) {
        // If JSON parsing fails, try to get text for better error message
        try {
          const text = await clonedResponse.text();
          throw new Error(`Invalid JSON response from ${url}. Server returned: ${text.substring(0, 200)}`);
        } catch (textError) {
          throw new Error(`Failed to parse response from ${url} as JSON`);
        }
      }

      // Handle error responses
      if (!response.ok) {
        const errorMessage = typeof data.detail === 'string'
          ? data.detail
          : (data.detail?.message || JSON.stringify(data.detail) || `Server error (${response.status})`);
        throw new Error(errorMessage);
      }

      return data;
    } catch (error) {
      // Handle network errors specifically (fetch fails before getting a response)
      if (error instanceof TypeError && (error.message.includes('fetch') || error.message.includes('Failed to fetch') || error.message.includes('NetworkError'))) {
        throw new Error(`Network error: Unable to reach the server at ${API_URL}${endpoint}. Please check that the backend is running and accessible. If using HTTPS frontend with HTTP backend, you may need to set up SSL on your backend.`);
      }
      
      // Handle JSON parsing errors
      if (error.message && error.message.includes('JSON')) {
        throw error;
      }
      
      // Ensure we always throw an Error with a string message
      if (error instanceof Error) {
        throw error;
      }
      throw new Error(String(error));
    }
  },

  // Auth
  initiateGoogleOAuth: () =>
    api.request("/auth/google/authorize", "GET"),

  googleOAuthCallback: (code, state, codeVerifier) =>
    api.request("/auth/google/callback", "POST", { code, state, code_verifier: codeVerifier }),

  getCurrentModerator: (token) =>
    api.request("/auth/me", "GET", null, token),

  // Moderation
  getReportedPosts: (token, skip = 0, limit = 50, unresolvedOnly = false) => {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
      unresolved_only: unresolvedOnly.toString(),
    });
    return api.request(`/moderation/reported-posts?${params}`, "GET", null, token);
  },

  resolveReport: (token, reportId) =>
    api.request(`/moderation/reported-posts/${reportId}/resolve`, "POST", null, token),

  getUsers: (token, skip = 0, limit = 50, search = null) => {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
    });
    if (search) {
      params.append("search", search);
    }
    return api.request(`/moderation/users?${params}`, "GET", null, token);
  },

  banUser: (token, userId) =>
    api.request(`/moderation/users/${userId}/ban`, "POST", null, token),

  unbanUser: (token, userId) =>
    api.request(`/moderation/users/${userId}/unban`, "POST", null, token),

  deleteUser: (token, userId) =>
    api.request(`/moderation/users/${userId}`, "DELETE", null, token),

  deletePost: (token, postId) =>
    api.request(`/moderation/posts/${postId}`, "DELETE", null, token),

  // MVP TEMPORARY: Registration Request Management - Remove when moving beyond MVP
  getRegistrationRequests: (token, skip = 0, limit = 50, statusFilter = null) => {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
    });
    if (statusFilter) {
      params.append("status_filter", statusFilter);
    }
    return api.request(`/moderation/registration-requests?${params}`, "GET", null, token);
  },

  approveRegistrationRequest: (token, requestId) =>
    api.request(`/moderation/registration-requests/${requestId}/approve`, "POST", null, token),

  denyRegistrationRequest: (token, requestId) =>
    api.request(`/moderation/registration-requests/${requestId}/deny`, "POST", null, token),
};

