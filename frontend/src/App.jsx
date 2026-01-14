import { BrowserRouter as Router, Routes, Route, Navigate, useLocation, Link } from "react-router-dom";
import { useState, useEffect, useRef } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import Feed from "./pages/Feed";
import People from "./pages/People";
import Connections from "./pages/Connections";
import Profile from "./pages/Profile";
import { sanitizeText } from "./utils/security";
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
    const navRef = useRef(null);
    const mainRef = useRef(null);
    
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

    // Dynamically set main padding based on navbar height + extra spacing
    useEffect(() => {
        const updateMainPadding = () => {
            if (navRef.current && mainRef.current) {
                const navHeight = navRef.current.offsetHeight;
                const extraSpacing = window.innerWidth <= 600 ? 24 : 32; // More spacing on desktop
                mainRef.current.style.paddingTop = `${navHeight + extraSpacing}px`;
            }
        };

        // Update on mount and resize
        updateMainPadding();
        window.addEventListener('resize', updateMainPadding);
        
        // Also update after a short delay to account for any dynamic content
        const timeoutId = setTimeout(updateMainPadding, 100);

        return () => {
            window.removeEventListener('resize', updateMainPadding);
            clearTimeout(timeoutId);
        };
    }, [user]); // Recalculate when user data changes (affects navbar content)

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
            <nav ref={navRef} className={isNavbarVisible ? 'nav-visible' : 'nav-hidden'}>
                <div className="nav-content">
                    <Link to="/" className="nav-brand serif-font">Intentional Social</Link>
                    <div className="nav-links">
                        <Link to="/" className={isActive("/") ? "active" : ""}>Home</Link>
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
                                {sanitizeText(displayName).charAt(0).toUpperCase()}
                            </div>
                        </Link>
                    </div>
                </div>
            </nav>
            <main ref={mainRef}>{children}</main>
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
