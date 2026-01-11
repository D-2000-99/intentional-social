import secrets
import hashlib
import base64
import httpx
from typing import Optional, Dict, Tuple
from fastapi import HTTPException, status
from google.auth.transport import requests
from google.oauth2 import id_token

from app.config import settings


def generate_pkce_pair() -> Tuple[str, str]:
    """
    Generate PKCE code verifier and code challenge.
    Returns: (code_verifier, code_challenge)
    """
    # Generate a cryptographically random code verifier (43-128 characters)
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    
    # Generate code challenge using SHA256
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')
    
    return code_verifier, code_challenge


def generate_state() -> str:
    """Generate a cryptographically random state parameter for CSRF protection."""
    return secrets.token_urlsafe(32)


def get_google_authorization_url(state: str, code_challenge: str) -> str:
    """
    Generate Google OAuth authorization URL with PKCE.
    
    Args:
        state: CSRF protection state parameter
        code_challenge: PKCE code challenge
    
    Returns:
        Google OAuth authorization URL
    """
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",  # Request refresh token
        "prompt": "consent",  # Force consent screen to get refresh token
    }
    
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{base_url}?{query_string}"


async def exchange_code_for_tokens(
    code: str,
    code_verifier: str
) -> Dict[str, str]:
    """
    Exchange authorization code for access and ID tokens using PKCE.
    
    Args:
        code: Authorization code from Google
        code_verifier: PKCE code verifier
    
    Returns:
        Dictionary with access_token, id_token, and refresh_token
    """
    token_url = "https://oauth2.googleapis.com/token"
    
    data = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "code_verifier": code_verifier,
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            tokens = response.json()
            
            if "error" in tokens:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Token exchange failed: {tokens.get('error_description', tokens['error'])}"
                )
            
            return tokens
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to exchange code for tokens: {e.response.text}"
            )


def verify_google_id_token(id_token_str: str) -> Dict:
    """
    Verify Google ID token signature and extract user information.
    
    Args:
        id_token_str: Google ID token string
    
    Returns:
        Dictionary with verified user information (sub, email, name, picture, etc.)
    
    Raises:
        HTTPException if token is invalid
    """
    try:
        # Verify the token signature and claims
        idinfo = id_token.verify_oauth2_token(
            id_token_str,
            requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
        
        # Verify the token issuer
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token issuer"
            )
        
        # Verify the token audience
        if idinfo['aud'] != settings.GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token audience"
            )
        
        return idinfo
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google ID token: {str(e)}"
        )


async def get_google_user_info(access_token: str) -> Dict:
    """
    Fetch user information from Google API using access token.
    This is a fallback method if ID token doesn't contain all needed info.
    
    Args:
        access_token: Google access token
    
    Returns:
        Dictionary with user information
    """
    userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(userinfo_url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to fetch user info: {e.response.text}"
            )

