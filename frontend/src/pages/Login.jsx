import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { api } from "../api";
import { useNavigate } from "react-router-dom";

export default function Login() {
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState("");
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const { login } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");
        try {
            if (isLogin) {
                const data = await api.login(email || username, password); // Allow email or username for login
                login(data.access_token);
                navigate("/");
            } else {
                await api.register(email, username, password);
                // Auto login after register
                const data = await api.login(username, password);
                login(data.access_token);
                navigate("/");
            }
        } catch (err) {
            setError(err.message);
        }
    };

    return (
        <div className="auth-container">
            <h1>Intentional Social</h1>
            <p className="subtitle">A calm place for meaningful connections.</p>

            <form onSubmit={handleSubmit}>
                {!isLogin && (
                    <div className="form-group">
                        <label>Email</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>
                )}

                <div className="form-group">
                    <label>{isLogin ? "Username or Email" : "Username"}</label>
                    <input
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        required={!isLogin} // Username required for register, but for login we use the same field for username/email
                    />
                </div>

                <div className="form-group">
                    <label>Password</label>
                    <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                    />
                </div>

                {error && <p className="error">{error}</p>}

                <button type="submit">{isLogin ? "Log In" : "Sign Up"}</button>
            </form>

            <p className="switch-mode">
                {isLogin ? "New here?" : "Already have an account?"}{" "}
                <button className="text-btn" onClick={() => setIsLogin(!isLogin)}>
                    {isLogin ? "Create an account" : "Log in"}
                </button>
            </p>
        </div>
    );
}
