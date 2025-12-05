import { BrowserRouter as Router, Routes, Route, Navigate, useLocation, Link } from "react-router-dom";
import { useState, useEffect } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import Feed from "./pages/Feed";
import People from "./pages/People";
import Search from "./pages/Search";
import Requests from "./pages/Requests";
import Connections from "./pages/Connections";
import Profile from "./pages/Profile";
import "./index.css";

const PrivateRoute = ({ children }) => {
    const { token } = useAuth();
    return token ? children : <Navigate to="/login" />;
};

const Layout = ({ children }) => {
    const { user } = useAuth();
    const location = useLocation();
    const [isNavbarVisible, setIsNavbarVisible] = useState(true);
    const [lastScrollY, setLastScrollY] = useState(0);
    
    const isActive = (path) => location.pathname === path;

    useEffect(() => {
        const handleScroll = () => {
            const currentScrollY = window.scrollY;
            
            // Show navbar when scrolling up, hide when scrolling down
            if (currentScrollY < lastScrollY) {
                // Scrolling up
                setIsNavbarVisible(true);
            } else if (currentScrollY > lastScrollY && currentScrollY > 100) {
                // Scrolling down and past 100px
                setIsNavbarVisible(false);
            }
            
            setLastScrollY(currentScrollY);
        };

        window.addEventListener('scroll', handleScroll, { passive: true });
        return () => window.removeEventListener('scroll', handleScroll);
    }, [lastScrollY]);

    // Get avatar URL
    const getAvatarUrl = () => {
        if (user?.avatar_url) {
            return user.avatar_url;
        }
        return user?.picture_url || null;
    };

    const avatarUrl = getAvatarUrl();
    const displayName = user?.display_name || user?.full_name || user?.username || "User";
    
    return (
        <div className="app-layout">
            <nav className={isNavbarVisible ? 'nav-visible' : 'nav-hidden'}>
                <div className="nav-content">
                    <Link to="/" className="nav-brand serif-font">Intentional Social</Link>
                    <div className="nav-links">
                        <Link to="/" className={isActive("/") ? "active" : ""}>Feed</Link>
                        <Link to="/search" className={isActive("/search") ? "active" : ""}>Search</Link>
                        <Link to="/requests" className={isActive("/requests") ? "active" : ""}>Requests</Link>
                        <Link to="/connections" className={isActive("/connections") ? "active" : ""}>Connections</Link>
                        <Link to="/profile" className="user-profile-link">
                            {avatarUrl ? (
                                <img 
                                    src={avatarUrl} 
                                    alt="Profile" 
                                    className="user-profile-avatar"
                                    onError={(e) => {
                                        e.target.style.display = 'none';
                                        e.target.nextSibling.style.display = 'flex';
                                    }}
                                />
                            ) : null}
                            <div 
                                className="user-profile-avatar-placeholder"
                                style={{ display: avatarUrl ? 'none' : 'flex' }}
                            >
                                {displayName.charAt(0).toUpperCase()}
                            </div>
                        </Link>
                    </div>
                </div>
            </nav>
            <main>{children}</main>
        </div>
    );
};

function AppRoutes() {
    return (
        <Routes>
            <Route path="/login" element={<Login />} />
            <Route
                path="/"
                element={
                    <PrivateRoute>
                        <Layout>
                            <Feed />
                        </Layout>
                    </PrivateRoute>
                }
            />
            <Route
                path="/search"
                element={
                    <PrivateRoute>
                        <Layout>
                            <Search />
                        </Layout>
                    </PrivateRoute>
                }
            />
            <Route
                path="/requests"
                element={
                    <PrivateRoute>
                        <Layout>
                            <Requests />
                        </Layout>
                    </PrivateRoute>
                }
            />
            <Route
                path="/connections"
                element={
                    <PrivateRoute>
                        <Layout>
                            <Connections />
                        </Layout>
                    </PrivateRoute>
                }
            />
            <Route
                path="/people"
                element={
                    <PrivateRoute>
                        <Layout>
                            <People />
                        </Layout>
                    </PrivateRoute>
                }
            />
            <Route
                path="/profile"
                element={
                    <PrivateRoute>
                        <Layout>
                            <Profile />
                        </Layout>
                    </PrivateRoute>
                }
            />
            <Route
                path="/profile/:username"
                element={
                    <PrivateRoute>
                        <Layout>
                            <Profile />
                        </Layout>
                    </PrivateRoute>
                }
            />
        </Routes>
    );
}

function App() {
    return (
        <AuthProvider>
            <Router>
                <AppRoutes />
            </Router>
        </AuthProvider>
    );
}

export default App;
