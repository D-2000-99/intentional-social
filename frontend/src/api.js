// Use environment variable for API URL, fallback to localhost for development
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

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

  // Google OAuth
  initiateGoogleOAuth: () =>
    api.request("/auth/google/authorize", "GET"),

  googleOAuthCallback: (code, state, codeVerifier) =>
    api.request("/auth/google/callback", "POST", { code, state, code_verifier: codeVerifier }),

  selectUsername: (token, username) =>
    api.request("/auth/username/select", "POST", { username }, token),

  getFeed: (token, skip = 0, limit = 20) =>
    api.request(`/feed/?skip=${skip}&limit=${limit}`, "GET", null, token),

  createPost: (token, content, audience_type = "all", audience_tag_ids = [], photos = []) => {
    // Always use multipart/form-data since backend expects Form parameters
    const formData = new FormData();
    formData.append("content", content);
    formData.append("audience_type", audience_type);
    if (audience_tag_ids.length > 0) {
      formData.append("audience_tag_ids", audience_tag_ids.join(","));
    }

    // Append client timestamp (ISO format from client's system time)
    // Use local time, not UTC - format as YYYY-MM-DDTHH:mm:ss.sss (no timezone)
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    const milliseconds = String(now.getMilliseconds()).padStart(3, '0');
    const clientTimestamp = `${year}-${month}-${day}T${hours}:${minutes}:${seconds}.${milliseconds}`;
    formData.append("client_timestamp", clientTimestamp);

    // Append each photo file if present
    if (photos && photos.length > 0) {
      photos.forEach((photo) => {
        formData.append("photos", photo);
      });
    }

    // Make request with FormData (don't set Content-Type header, browser will set it with boundary)
    const headers = {
      "Authorization": `Bearer ${token}`,
      // Don't set Content-Type - browser will set it with boundary for multipart/form-data
    };

    return fetch(`${API_URL}/posts/`, {
      method: "POST",
      headers,
      body: formData,
    })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) {
          const errorMessage = typeof data.detail === 'string'
            ? data.detail
            : (data.detail?.message || JSON.stringify(data.detail) || "API Error");
          throw new Error(errorMessage);
        }
        return data;
      });
  },

  getMyPosts: (token) =>
    api.request("/posts/me", "GET", null, token),

  deletePost: async (token, postId) => {
    const headers = {
      "Authorization": `Bearer ${token}`,
    };

    const response = await fetch(`${API_URL}/posts/${postId}`, {
      method: "DELETE",
      headers,
    });

    // Handle 204 No Content (successful deletion with no body)
    if (response.status === 204) {
      return null;
    }

    // Handle error responses
    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch (e) {
        errorData = { detail: `Server error (${response.status})` };
      }
      
      const errorMessage = typeof errorData.detail === 'string'
        ? errorData.detail
        : (errorData.detail?.message || JSON.stringify(errorData.detail) || `Server error (${response.status})`);
      throw new Error(errorMessage);
    }

    // Try to parse JSON for other status codes
    try {
      return await response.json();
    } catch (e) {
      return null;
    }
  },

  getUsers: (token) =>
    api.request("/auth/users", "GET", null, token),

  // Connection management
  sendConnectionRequest: (token, userId) =>
    api.request(`/connections/request/${userId}`, "POST", null, token),

  getIncomingRequests: (token) =>
    api.request("/connections/requests/incoming", "GET", null, token),

  getOutgoingRequests: (token) =>
    api.request("/connections/requests/outgoing", "GET", null, token),

  acceptRequest: (token, connectionId) =>
    api.request(`/connections/accept/${connectionId}`, "POST", null, token),

  rejectRequest: (token, connectionId) =>
    api.request(`/connections/reject/${connectionId}`, "DELETE", null, token),

  getConnections: (token) =>
    api.request("/connections", "GET", null, token),

  getConnectionInsights: (token) =>
    api.request("/insights/connections", "GET", null, token),

  disconnect: (token, connectionId) =>
    api.request(`/connections/${connectionId}`, "DELETE", null, token),

  searchUsers: (token, query) =>
    api.request(`/auth/users/search?q=${encodeURIComponent(query)}`, "GET", null, token),

  // Tag management
  getTags: (token) =>
    api.request("/tags", "GET", null, token),

  createTag: (token, name, colorScheme = "generic") =>
    api.request("/tags", "POST", { name, color_scheme: colorScheme }, token),

  updateTag: (token, tagId, data) =>
    api.request(`/tags/${tagId}`, "PUT", data, token),

  deleteTag: (token, tagId) =>
    api.request(`/tags/${tagId}`, "DELETE", null, token),

  // Connection tags
  getConnectionTags: (token, connectionId) =>
    api.request(`/connections/${connectionId}/tags`, "GET", null, token),

  addTagToConnection: (token, connectionId, tagId) =>
    api.request(`/connections/${connectionId}/tags`, "POST", { tag_id: tagId }, token),

  removeTagFromConnection: (token, connectionId, tagId) =>
    api.request(`/connections/${connectionId}/tags/${tagId}`, "DELETE", null, token),

  // User profile
  updateAvatar: async (token, avatarFile) => {
    const formData = new FormData();
    formData.append("avatar", avatarFile);

    const headers = {
      "Authorization": `Bearer ${token}`,
      // Don't set Content-Type - browser will set it with boundary for multipart/form-data
    };

    return fetch(`${API_URL}/auth/me/avatar`, {
      method: "PUT",
      headers,
      body: formData,
    })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) {
          const errorMessage = typeof data.detail === 'string'
            ? data.detail
            : (data.detail?.message || JSON.stringify(data.detail) || "API Error");
          throw new Error(errorMessage);
        }
        return data;
      });
  },

  updateBio: (token, bio) =>
    api.request("/auth/me/bio", "PUT", { bio }, token),

  getUserByUsername: (token, username) =>
    api.request(`/auth/user/${username}`, "GET", null, token),

  getUserPosts: (token, userId) =>
    api.request(`/posts/user/${userId}`, "GET", null, token),

  // Comments
  getPostComments: (token, postId) =>
    api.request(`/comments/posts/${postId}`, "GET", null, token),

  createComment: (token, postId, content) =>
    api.request("/comments/", "POST", { post_id: postId, content }, token),

  reportPost: (token, postId, reason = null) =>
    api.request(`/posts/${postId}/report`, "POST", { reason }, token),

  // Digest
  getDigest: (token, tagFilter = "all") => {
    // Send client timestamp (local time, not UTC) to determine the week
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    const milliseconds = String(now.getMilliseconds()).padStart(3, '0');
    const clientTimestamp = `${year}-${month}-${day}T${hours}:${minutes}:${seconds}.${milliseconds}`;
    
    return api.request(
      `/digest/?tag_filter=${encodeURIComponent(tagFilter)}&client_timestamp=${encodeURIComponent(clientTimestamp)}`,
      "GET",
      null,
      token
    );
  },
};
