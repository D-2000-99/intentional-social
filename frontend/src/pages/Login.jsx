import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { api } from "../api";
import { useNavigate } from "react-router-dom";

export default function Login() {
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState("");
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [otpCode, setOtpCode] = useState("");
    const [otpSent, setOtpSent] = useState(false);
    const [error, setError] = useState("");
    const { login } = useAuth();
    const navigate = useNavigate();

    const handleSendOTP = async (e) => {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        setError("");
        if (!email) {
            setError("Email is required");
            return;
        }
        try {
            await api.sendRegistrationOTP(email);
            setOtpSent(true);
            setError("");
        } catch (err) {
            setError(err.message || "Failed to send verification code");
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");
        try {
            if (isLogin) {
                const data = await api.login(email || username, password);
                login(data.access_token);
                navigate("/");
            } else {
                if (!otpSent) {
                    await handleSendOTP(e);
                    return;
                }
                if (!otpCode) {
                    setError("Please enter the verification code");
                    return;
                }
                await api.register(email, username, password, otpCode);
                // Auto login after register
                const data = await api.login(username, password);
                login(data.access_token);
                navigate("/");
            }
        } catch (err) {
            setError(err.message || "Registration failed");
        }
    };

    return (
        <div className="auth-container">
            <h1>Intentional Social</h1>
            <p className="subtitle">A calm place for meaningful connections.</p>

            <form onSubmit={handleSubmit}>
                {!isLogin && (
                    <>
                        <div className="form-group">
                            <label>Email</label>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                disabled={otpSent}
                            />
                        </div>
                        {!otpSent && (
                            <button type="button" onClick={handleSendOTP} className="otp-button">
                                Send Verification Code
                            </button>
                        )}
                        {otpSent && (
                            <div className="form-group">
                                <label>Verification Code</label>
                                <input
                                    type="text"
                                    value={otpCode}
                                    onChange={(e) => setOtpCode(e.target.value)}
                                    placeholder="Enter 6-digit code"
                                    maxLength={6}
                                    required
                                />
                                <p className="otp-hint">
                                    Check your email for the verification code
                                </p>
                            </div>
                        )}
                    </>
                )}

                {(!isLogin && otpSent) && (
                    <>
                        <div className="form-group">
                            <label>Username</label>
                            <input
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                required
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
                    </>
                )}

                {isLogin && (
                    <>
                        <div className="form-group">
                            <label>Username or Email</label>
                            <input
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                required
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
                    </>
                )}

                {error && <p className="error">{error}</p>}

                <button type="submit">
                    {isLogin ? "Log In" : (otpSent ? "Sign Up" : "Send Verification Code")}
                </button>
            </form>

            <p className="switch-mode">
                {isLogin ? "New here?" : "Already have an account?"}{" "}
                <button 
                    className="text-btn" 
                    onClick={() => {
                        setIsLogin(!isLogin);
                        setOtpSent(false);
                        setOtpCode("");
                        setError("");
                    }}
                >
                    {isLogin ? "Create an account" : "Log in"}
                </button>
            </p>
        </div>
    );
}
