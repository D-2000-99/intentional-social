// Use environment variable for API URL, fallback to localhost for development
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = {
  async request(endpoint, method = "GET", body = null, token = null) {
    const headers = {
      "Content-Type": "application/json",
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const config = {
      method,
      headers,
    };

    if (body) {
      config.body = JSON.stringify(body);
    }

    try {
      const response = await fetch(`${API_URL}${endpoint}`, config);
      const data = await response.json();

      if (!response.ok) {
        // Handle both string and object error details
        const errorMessage = typeof data.detail === 'string'
          ? data.detail
          : (data.detail?.message || JSON.stringify(data.detail) || "API Error");
        throw new Error(errorMessage);
      }

      return data;
    } catch (error) {
      // Ensure we always throw an Error with a string message
      if (error instanceof Error) {
        throw error;
      }
      throw new Error(String(error));
    }
  },

  login: (username_or_email, password) =>
    api.request("/auth/login", "POST", { username_or_email, password }),

  sendRegistrationOTP: (email) =>
    api.request("/auth/send-registration-otp", "POST", { email }),

  register: (email, username, password, otpCode) =>
    api.request("/auth/register", "POST", { email, username, password, otp_code: otpCode }),

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
};
