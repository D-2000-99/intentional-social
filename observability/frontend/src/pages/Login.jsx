import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import { api } from "../api";
import { useNavigate, useSearchParams } from "react-router-dom";

function isValidOAuthUrl(url, allowedHosts) {
  try {
    const urlObj = new URL(url);
    return allowedHosts.some(host => urlObj.hostname === host || urlObj.hostname.endsWith('.' + host));
  } catch {
    return false;
  }
}

export default function Login() {
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const [processingCallback, setProcessingCallback] = useState(false);
    const { login } = useAuth();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const hasProcessedCallback = useRef(false);

    const handleOAuthCallback = useCallback(async (code, state) => {
        setLoading(true);
        setError("");
        
        try {
            const codeVerifier = sessionStorage.getItem("oauth_code_verifier");
            const storedState = sessionStorage.getItem("oauth_state");
            
            if (!codeVerifier) {
                throw new Error("Session expired. Please try signing in again.");
            }
            
            if (state !== storedState) {
                throw new Error("Invalid state parameter. Please try again.");
            }
            
            sessionStorage.removeItem("oauth_code_verifier");
            sessionStorage.removeItem("oauth_state");
            
            const response = await api.googleOAuthCallback(code, state, codeVerifier);
            
            login(response.access_token);
            navigate("/", { replace: true });
        } catch (err) {
            console.error("OAuth callback error:", err);
            setError(err.message || "Authentication failed. Your email may not be authorized as a moderator.");
            setLoading(false);
            setProcessingCallback(false);
            hasProcessedCallback.current = false;
            navigate("/login", { replace: true });
        }
    }, [login, navigate]);

    useEffect(() => {
        const code = searchParams.get("code");
        const state = searchParams.get("state");
        
        if (code && state && !hasProcessedCallback.current) {
            hasProcessedCallback.current = true;
            setProcessingCallback(true);
            handleOAuthCallback(code, state);
        }
    }, [searchParams, handleOAuthCallback]);

    const handleGoogleOAuth = async () => {
        setError("");
        setLoading(true);
        
        try {
            const data = await api.initiateGoogleOAuth();
            
            if (!isValidOAuthUrl(data.authorization_url, ['accounts.google.com'])) {
                throw new Error("Invalid OAuth URL. Please try again.");
            }
            
            sessionStorage.setItem("oauth_code_verifier", data.code_verifier);
            sessionStorage.setItem("oauth_state", data.state);
            
            window.location.href = data.authorization_url;
        } catch (err) {
            setError(err.message || "Failed to initiate Google sign-in");
            setLoading(false);
        }
    };

    return (
        <div className="auth-container">
            <h1>Moderator Dashboard</h1>
            <p className="subtitle">Intentional Social</p>

            {processingCallback && (
                <div className="auth-loading">
                    <p>Completing sign-in...</p>
                </div>
            )}

            {error && <p className="error">{error}</p>}

            {!processingCallback && (
                <button
                    onClick={handleGoogleOAuth}
                    disabled={loading}
                    className="google-signin-button"
                    aria-label="Sign in with Google"
                >
                    {loading ? (
                        "Signing in..."
                    ) : (
                        <>
                            <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
                                <path
                                    fill="#4285F4"
                                    d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.616z"
                                />
                                <path
                                    fill="#34A853"
                                    d="M9 18c2.43 0 4.467-.806 5.96-2.184l-2.908-2.258c-.806.54-1.837.86-3.052.86-2.35 0-4.34-1.587-5.052-3.72H.957v2.332C2.438 15.983 5.482 18 9 18z"
                                />
                                <path
                                    fill="#FBBC05"
                                    d="M3.948 10.712c-.26-.767-.41-1.584-.41-2.412 0-.828.15-1.645.41-2.412V3.556H.957C.348 4.844 0 6.351 0 8s.348 3.156.957 4.444l2.991-1.732z"
                                />
                                <path
                                    fill="#EA4335"
                                    d="M9 3.576c1.326 0 2.515.455 3.451 1.345l2.588-2.588C13.467.891 11.43 0 9 0 5.482 0 2.438 2.017.957 5.556L3.948 7.288C4.66 5.153 6.65 3.576 9 3.576z"
                                />
                            </svg>
                            Sign in with Google
                        </>
                    )}
                </button>
            )}
        </div>
    );
}

