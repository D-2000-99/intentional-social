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

    if (method === "POST" || method === "PUT") {
      headers["Content-Type"] = "application/json";
      config.body = JSON.stringify(body || {});
    } else if (body) {
      headers["Content-Type"] = "application/json";
      config.body = JSON.stringify(body);
    }

    try {
      const url = `${API_URL}${endpoint}`;
      const response = await fetch(url, config);
      const data = await response.json();

      if (!response.ok) {
        const errorMessage = typeof data.detail === 'string'
          ? data.detail
          : (data.detail?.message || JSON.stringify(data.detail) || `Server error (${response.status})`);
        throw new Error(errorMessage);
      }

      return data;
    } catch (error) {
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error(`Network error: Unable to reach the server at ${API_URL}${endpoint}`);
      }
      throw error;
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
};

