import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import { api } from "../api";
import { useNavigate, useSearchParams } from "react-router-dom";
import UsernameSelectionModal from "../components/UsernameSelectionModal";
import { isValidOAuthUrl, sanitizeText } from "../utils/security";

export default function Login() {
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const [processingCallback, setProcessingCallback] = useState(false);
    const [showUsernameModal, setShowUsernameModal] = useState(false);
    const [pendingUser, setPendingUser] = useState(null);
    const { login } = useAuth();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const hasProcessedCallback = useRef(false);

    const handleOAuthCallback = useCallback(async (code, state) => {
        setLoading(true);
        setError("");
        
        try {
            // Retrieve stored code_verifier and state
            const codeVerifier = sessionStorage.getItem("oauth_code_verifier");
            const storedState = sessionStorage.getItem("oauth_state");
            
            if (!codeVerifier) {
                throw new Error("Session expired. Please try signing in again.");
            }
            
            // Verify state matches (CSRF protection)
            if (state !== storedState) {
                throw new Error("Invalid state parameter. Please try again.");
            }
            
            // Clear stored values
            sessionStorage.removeItem("oauth_code_verifier");
            sessionStorage.removeItem("oauth_state");
            
            // Exchange code for tokens
            const response = await api.googleOAuthCallback(code, state, codeVerifier);
            
            // Store token
            login(response.access_token);
            
            // Check if user needs to select username
            if (response.needs_username) {
                setPendingUser(response.user);
                setShowUsernameModal(true);
                setLoading(false);
            } else {
                // Navigate to home
                navigate("/", { replace: true });
            }
        } catch (err) {
            console.error("OAuth callback error:", err);
            // Check if this is a registration request pending error
            if (err.response?.status === 403 && err.response?.data?.detail?.includes("registration request")) {
                // Show friendly message about pending approval
                setError("Your registration request has been submitted and is pending admin approval. You will be able to sign in once your request is approved.");
            } else {
                setError(err.message || "Authentication failed. Please try again.");
            }
            setLoading(false);
            setProcessingCallback(false);
            hasProcessedCallback.current = false;
            // Clear URL params
            navigate("/login", { replace: true });
        }
    }, [login, navigate]);

    // Handle OAuth callback from Google redirect
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
            // Get authorization URL and PKCE data from backend
            const data = await api.initiateGoogleOAuth();
            
            // Validate OAuth URL to prevent open redirect attacks
            if (!isValidOAuthUrl(data.authorization_url, ['accounts.google.com'])) {
                throw new Error("Invalid OAuth URL. Please try again.");
            }
            
            // Store code_verifier and state in sessionStorage (temporary, cleared after use)
            sessionStorage.setItem("oauth_code_verifier", data.code_verifier);
            sessionStorage.setItem("oauth_state", data.state);
            
            // Redirect to Google
            window.location.href = data.authorization_url;
        } catch (err) {
            setError(err.message || "Failed to initiate Google sign-in");
            setLoading(false);
        }
    };

    const handleUsernameSelected = async (username) => {
        try {
            const token = localStorage.getItem("token");
            await api.selectUsername(token, username);
            setShowUsernameModal(false);
            setPendingUser(null);
            navigate("/");
        } catch (err) {
            setError(err.message || "Failed to set username. Please try again.");
        }
    };

    return (
        <div className="auth-container">
            <h1 className="serif-font">Intentional Social</h1>
            <p className="subtitle">A calm place for meaningful connections.</p>

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
                                    d="M3.948 10.698c-.18-.54-.282-1.117-.282-1.698s.102-1.158.282-1.698V4.97H.957C.348 6.175 0 7.55 0 9s.348 2.825.957 4.03l2.991-2.332z"
                                />
                                <path
                                    fill="#EA4335"
                                    d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.582C13.463.891 11.426 0 9 0 5.482 0 2.438 2.017.957 4.97L3.948 7.302C4.66 5.167 6.65 3.58 9 3.58z"
                                />
                            </svg>
                            Sign in with Google
                        </>
                    )}
                </button>
            )}

            {showUsernameModal && pendingUser && (
                <UsernameSelectionModal
                    user={pendingUser}
                    onUsernameSelected={handleUsernameSelected}
                    onCancel={() => {
                        setShowUsernameModal(false);
                        // Logout if they cancel
                        localStorage.removeItem("token");
                        window.location.reload();
                    }}
                />
            )}
        </div>
    );
}
