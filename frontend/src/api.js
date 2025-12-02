const API_URL = "http://localhost:8000";

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
        throw new Error(data.detail || "API Error");
      }

      return data;
    } catch (error) {
      throw error;
    }
  },

  login: (username_or_email, password) =>
    api.request("/auth/login", "POST", { username_or_email, password }),

  register: (email, username, password) =>
    api.request("/auth/register", "POST", { email, username, password }),

  getFeed: (token, skip = 0, limit = 20) =>
    api.request(`/feed/?skip=${skip}&limit=${limit}`, "GET", null, token),

  createPost: (token, content) =>
    api.request("/posts/", "POST", { content }, token),

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
};
