import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
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
    return (
        <div className="app-layout">
            <nav>
                <div className="nav-brand">Intentional Social</div>
                <div className="nav-links">
                    <a href="/">Feed</a>
                    <a href="/my-posts">My Posts</a>
                    <a href="/search">Search</a>
                    <a href="/requests">Requests</a>
                    <a href="/connections">Connections</a>
                    <span className="user-info">{user?.username}</span>
                    <button onClick={logout} className="logout-btn">Logout</button>
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
