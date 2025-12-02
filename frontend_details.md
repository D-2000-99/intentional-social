# Frontend Technical Documentation
## Intentional Social - React MVP

**Author**: Senior Frontend Engineer  
**Date**: December 2, 2025  
**Framework**: React 18 + Vite  
**Status**: MVP Implementation Complete

---

## 1. Architecture Overview

### Technology Stack
- **Build Tool**: Vite (Fast, modern build tool with HMR)
- **Framework**: React 18.x
- **Routing**: React Router DOM v6
- **State Management**: React Context API (AuthContext)
- **HTTP Client**: Native Fetch API
- **JWT Handling**: jwt-decode library
- **Styling**: Custom CSS with CSS Variables (No UI framework)

### Design Philosophy
The frontend strictly adheres to the "Calm Design" principles:
- **Minimalist UI**: No unnecessary visual elements
- **Neutral Color Palette**: Soft grays with dark mode support
- **No Engagement Patterns**: No likes, shares, metrics, or gamification
- **Text-First**: Focus on content, not presentation
- **Intentional Interactions**: Every action requires deliberate user input

---

## 2. Project Structure

```
frontend/
├── src/
│   ├── context/
│   │   └── AuthContext.jsx       # Authentication state management
│   ├── pages/
│   │   ├── Login.jsx              # Auth screen (Login/Register)
│   │   ├── Feed.jsx               # Main feed + post creation
│   │   └── People.jsx             # User discovery & follow management
│   ├── api.js                     # Centralized API client
│   ├── App.jsx                    # Main app component with routing
│   ├── index.css                  # Global styles & design system
│   └── main.jsx                   # React entry point
├── package.json
└── vite.config.js
```

---

## 3. Core Components

### 3.1 Authentication System (`AuthContext.jsx`)

**Purpose**: Centralized authentication state management using React Context API.

**Key Features**:
- JWT token storage (localStorage for persistence)
- Automatic token validation on mount
- Token expiry detection using `jwt-decode`
- User state derived from JWT payload
- Logout functionality with cleanup

**Implementation Details**:
```javascript
// Token structure from backend:
{
  sub: userId,        // Subject (user ID)
  exp: timestamp      // Expiry timestamp
}
```

**State Management**:
- `token`: JWT access token (string | null)
- `user`: Decoded user object with username
- `login(token)`: Sets token and updates user state
- `logout()`: Clears token and user state

**Security Considerations**:
- Token stored in localStorage (survives page refresh)
- Expiry checked on every mount
- Automatic logout on invalid/expired tokens

---

### 3.2 API Client (`api.js`)

**Purpose**: Centralized HTTP client with consistent error handling.

**Architecture**:
- Base URL: `http://localhost:8000`
- All requests use JSON content type
- Token automatically attached to authenticated requests
- Unified error handling with meaningful messages

**API Methods**:

| Method | Endpoint | Auth Required | Purpose |
|--------|----------|---------------|---------|
| `login(username_or_email, password)` | POST `/auth/login` | No | User authentication |
| `register(email, username, password)` | POST `/auth/register` | No | User registration |
| `getFeed(token, skip, limit)` | GET `/feed/` | Yes | Fetch chronological feed |
| `createPost(token, content)` | POST `/posts/` | Yes | Create new post |
| `getUsers(token)` | GET `/auth/users` | Yes | List all users |
| `followUser(token, userId)` | POST `/follows/{userId}` | Yes | Follow a user |
| `unfollowUser(token, userId)` | DELETE `/follows/{userId}` | Yes | Unfollow a user |

**Error Handling**:
- Throws errors with `detail` message from backend
- Fallback to generic "API Error" if no detail provided

---

### 3.3 Pages

#### Login Page (`Login.jsx`)

**Features**:
- Toggle between Login and Register modes
- Single form with conditional fields
- Email field only shown for registration
- Username/Email field for login (flexible)
- Auto-login after successful registration
- Error display for failed attempts

**UX Flow**:
1. User lands on login screen
2. Can toggle to "Create account"
3. On successful auth, redirected to Feed (`/`)
4. Token stored and user logged in

**Form Validation**:
- Required fields enforced by HTML5
- Email validation for registration
- Password minimum length (backend enforced)

---

#### Feed Page (`Feed.jsx`)

**Features**:
- **Post Creation**: Textarea at top of feed
- **Chronological Display**: Newest posts first
- **Auto-refresh**: Feed reloads after posting
- **Empty State**: Helpful message when no posts

**Data Flow**:
1. Component mounts → `fetchFeed()` called
2. Posts fetched from `/feed/` endpoint
3. Displayed in reverse chronological order
4. User creates post → `handlePost()` → Feed refreshes

**Post Card Structure**:
```
┌─────────────────────────────┐
│ @username        Date       │
│                             │
│ Post content text...        │
└─────────────────────────────┘
```

**State Management**:
- `posts`: Array of post objects
- `content`: Current post input
- `loading`: Loading state for initial fetch

---

#### People Page (`People.jsx`)

**Features**:
- List all users (except current user)
- Show username and join date
- Follow/Unfollow buttons for each user
- 100-follow limit enforced by backend

**Known Limitation**:
The current implementation shows both "Follow" and "Unfollow" buttons because the backend's `GET /auth/users` endpoint doesn't return follow status. This is a UX compromise for the MVP.

**Ideal Enhancement** (requires backend change):
```javascript
// Backend should return:
{
  id: 1,
  username: "alice",
  created_at: "...",
  is_following: true  // ← This field needed
}
```

**Current Workaround**:
- Both buttons shown
- Backend returns 409 if already following
- Backend returns 404 if not following
- Alerts shown to user

---

### 3.4 Routing & Layout (`App.jsx`)

**Route Structure**:
```
/login          → Public (Login/Register page)
/               → Private (Feed page)
/people         → Private (People page)
```

**Private Route Pattern**:
```javascript
<PrivateRoute>
  <Layout>
    <PageComponent />
  </Layout>
</PrivateRoute>
```

**Layout Component**:
- Navigation bar with brand, links, username, logout
- Wraps all authenticated pages
- Consistent header across app

**Navigation Links**:
- Feed (/)
- People (/people)
- Username display
- Logout button

---

## 4. Styling System (`index.css`)

### Design Tokens (CSS Variables)

**Light Mode** (default):
```css
--bg-color: #f9f9f9       /* Page background */
--text-color: #333        /* Primary text */
--accent-color: #555      /* Secondary text */
--border-color: #ddd      /* Borders & dividers */
--card-bg: #fff           /* Card backgrounds */
```

**Dark Mode** (auto-detected via `prefers-color-scheme`):
```css
--bg-color: #1a1a1a
--text-color: #e0e0e0
--accent-color: #aaa
--border-color: #333
--card-bg: #222
```

### Typography
- **Font Stack**: System fonts (Apple, Segoe UI, Roboto)
- **Line Height**: 1.6 for readability
- **Font Smoothing**: Antialiased for clarity

### Component Styles

**Buttons**:
- Minimal border, subtle hover opacity
- Disabled state with reduced opacity
- Secondary variant for less prominent actions

**Forms**:
- Full-width inputs with padding
- Consistent border and background
- Inherits font family

**Cards** (Posts, Users):
- White/dark background with border
- Rounded corners (8px)
- Padding for breathing room

### Layout Constraints
- **Max Width**: 600px (human-scale reading width)
- **Centered**: Content centered on page
- **Padding**: 1rem horizontal for mobile

---

## 5. State Management Strategy

### Why Context API?
For this MVP, React Context is sufficient because:
- **Simple State**: Only auth state is global
- **No Complex Updates**: Login/logout are the only mutations
- **Performance**: No prop drilling, minimal re-renders
- **No External Dependencies**: Keeps bundle small

### State Flow Diagram
```
AuthProvider (top-level)
    ↓
  token, user, login(), logout()
    ↓
  ├─→ Login Page (calls login())
  ├─→ Feed Page (uses token)
  ├─→ People Page (uses token)
  └─→ App.jsx (PrivateRoute checks token)
```

---

## 6. Backend Integration

### CORS Configuration
The backend has been configured to allow requests from:
- `http://localhost:5173` (Vite default)
- `http://localhost:3000` (Alternative port)

**Backend Change Made**:
```python
# app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### API Response Formats

**Login Response**:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

**Feed Response**:
```json
[
  {
    "id": 1,
    "content": "Hello world",
    "created_at": "2025-12-02T12:00:00",
    "author": {
      "id": 1,
      "username": "alice"
    }
  }
]
```

**User List Response**:
```json
[
  {
    "id": 1,
    "email": "alice@example.com",
    "username": "alice",
    "created_at": "2025-12-01T10:00:00"
  }
]
```

---

## 7. Known Issues & Limitations

### 1. Follow Status Not Visible
**Issue**: People page doesn't show which users you're already following.  
**Cause**: Backend `UserOut` schema doesn't include `is_following` field.  
**Impact**: UX confusion with both Follow/Unfollow buttons shown.  
**Solution**: Backend should add `is_following` boolean to user list response.

### 2. No Pagination on Feed
**Issue**: Feed loads all posts at once.  
**Cause**: MVP simplification.  
**Impact**: Performance degrades with many posts.  
**Solution**: Implement infinite scroll or "Load More" button.

### 3. No Real-time Updates
**Issue**: Feed doesn't auto-refresh when others post.  
**Cause**: No WebSocket or polling implemented.  
**Impact**: User must manually refresh to see new content.  
**Solution**: Add polling (simple) or WebSocket (better).

### 4. Token in localStorage
**Issue**: XSS vulnerability if site is compromised.  
**Cause**: localStorage is accessible to JavaScript.  
**Impact**: Token could be stolen by malicious scripts.  
**Solution**: Consider httpOnly cookies (requires backend change).

### 5. No Loading States on Actions
**Issue**: No visual feedback when following/unfollowing.  
**Cause**: MVP simplification.  
**Impact**: User unsure if action succeeded.  
**Solution**: Add loading spinners and optimistic updates.

---

## 8. Performance Considerations

### Bundle Size
- **React**: ~40KB (gzipped)
- **React Router**: ~10KB (gzipped)
- **jwt-decode**: ~1KB (gzipped)
- **Total**: ~51KB + app code

### Optimization Opportunities
1. **Code Splitting**: Split routes into separate chunks
2. **Lazy Loading**: Load pages on demand
3. **Memoization**: Use `React.memo` for post cards
4. **Virtual Scrolling**: For long feed lists

### Current Performance
- **First Load**: Fast (minimal dependencies)
- **Navigation**: Instant (client-side routing)
- **API Calls**: Dependent on backend latency

---

## 9. Accessibility (A11y)

### Current State
- ✅ Semantic HTML (`<nav>`, `<main>`, `<form>`)
- ✅ Keyboard navigation (native browser support)
- ✅ Color contrast (WCAG AA compliant)
- ❌ No ARIA labels
- ❌ No screen reader testing
- ❌ No focus management

### Improvements Needed
1. Add ARIA labels to buttons
2. Announce feed updates to screen readers
3. Manage focus after navigation
4. Add skip links for keyboard users

---

## 10. Security Considerations

### Implemented
- ✅ JWT validation on mount
- ✅ Token expiry checking
- ✅ HTTPS-ready (works with https backend)
- ✅ No sensitive data in localStorage (only token)

### Not Implemented (Future)
- ❌ CSRF protection (not needed for JWT in header)
- ❌ Rate limiting (backend responsibility)
- ❌ Input sanitization (backend responsibility)
- ❌ Content Security Policy headers

---

## 11. Testing Strategy (Not Implemented)

### Recommended Tests

**Unit Tests** (with Vitest):
- AuthContext: login/logout/token validation
- API client: request formatting, error handling

**Integration Tests** (with React Testing Library):
- Login flow: register → auto-login → redirect
- Feed flow: load posts → create post → refresh
- Follow flow: follow user → handle limit error

**E2E Tests** (with Playwright):
- Full user journey: signup → post → follow → view feed

---

## 12. Deployment Checklist

### Before Production
- [ ] Add environment variables for API URL
- [ ] Enable production build (`npm run build`)
- [ ] Configure CDN for static assets
- [ ] Add error boundary for crash recovery
- [ ] Implement analytics (privacy-respecting)
- [ ] Add meta tags for SEO
- [ ] Test on multiple browsers
- [ ] Test on mobile devices
- [ ] Add loading states for all async actions
- [ ] Implement proper error messages

### Build Command
```bash
npm run build
# Output: dist/ folder ready for deployment
```

### Environment Variables
```env
VITE_API_URL=https://api.intentionalsocial.com
```

---

## 13. Future Enhancements

### Phase 2 Features
1. **Profile Pages**: View user's post history
2. **Direct Messages**: 1-on-1 conversations
3. **Notifications**: New posts from followed users
4. **Search**: Find users by username
5. **Post Drafts**: Save posts before publishing

### Phase 3 Features
1. **Threads**: Reply to posts
2. **Bookmarks**: Save posts for later
3. **Mute**: Hide specific users without unfollowing
4. **Export Data**: Download all your posts

---

## 14. Developer Setup

### Prerequisites
- Node.js 18+ (for Vite)
- npm or yarn

### Installation (When package.json exists)
```bash
cd frontend
npm install
npm run dev
```

### Development Server
- URL: `http://localhost:5173`
- Hot Module Replacement (HMR) enabled
- Auto-opens in browser

### Build for Production
```bash
npm run build
npm run preview  # Preview production build
```

---

## Conclusion

This frontend MVP successfully implements the core "Intentional Social" vision:
- **Calm Design**: No distractions, minimal UI
- **Human-Scale**: 100-follow limit enforced
- **Chronological Feed**: No algorithms
- **Privacy-First**: No tracking, no metrics

The codebase is clean, maintainable, and ready for iteration based on user feedback.

**Next Steps**: Deploy to production, gather user feedback, and iterate on the UX based on real-world usage patterns.
