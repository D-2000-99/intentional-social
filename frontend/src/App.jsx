import { BrowserRouter as Router, Routes, Route, Navigate, useLocation, Link } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import Feed from "./pages/Feed";
import People from "./pages/People";
import Search from "./pages/Search";
import Requests from "./pages/Requests";
import Connections from "./pages/Connections";
import MyPosts from "./pages/MyPosts";
import "./index.css";

const PrivateRoute = ({ children }) => {
    const { token } = useAuth();
    return token ? children : <Navigate to="/login" />;
};

const Layout = ({ children }) => {
    const { logout, user } = useAuth();
    const location = useLocation();
    
    const isActive = (path) => location.pathname === path;
    
    return (
        <div className="app-layout">
            <nav>
                <div className="container nav-content">
                    <Link to="/" className="nav-brand serif-font">Intentional Social</Link>
                    <div className="nav-links">
                        <Link to="/" className={isActive("/") ? "active" : ""}>Feed</Link>
                        <Link to="/my-posts" className={isActive("/my-posts") ? "active" : ""}>My Posts</Link>
                        <Link to="/search" className={isActive("/search") ? "active" : ""}>Search</Link>
                        <Link to="/requests" className={isActive("/requests") ? "active" : ""}>Requests</Link>
                        <Link to="/connections" className={isActive("/connections") ? "active" : ""}>Connections</Link>
                        <div className="user-profile">
                            <span className="user-profile__name">
                                {user?.display_name?.split(' ')[0] || user?.full_name?.split(' ')[0] || user?.username}
                            </span>
                            <span className="user-profile__username">@{user?.username}</span>
                        </div>
                        <button onClick={logout} className="logout-btn">Logout</button>
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
                path="/my-posts"
                element={
                    <PrivateRoute>
                        <Layout>
                            <MyPosts />
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
