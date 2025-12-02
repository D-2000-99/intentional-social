from app.config import settings

def get_auth_token(client, email, username):
    client.post(
        "/auth/register",
        json={"email": email, "username": username, "password": "password123"},
    )
    response = client.post(
        "/auth/login",
        json={"username_or_email": username, "password": "password123"},
    )
    return response.json()["access_token"]

def test_follow_limit(client):
    # Create main user
    token = get_auth_token(client, "main@example.com", "mainuser")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create 101 users to follow
    # We need to register them first so they exist in DB
    for i in range(settings.MAX_FOLLOWS + 1):
        client.post(
            "/auth/register",
            json={"email": f"user{i}@example.com", "username": f"user{i}", "password": "password123"},
        )
        
        # Get their ID (assuming sequential IDs starting from 2, mainuser is 1)
        # Better: get user by username via endpoint if available, or just assume ID
        # Since we use a fresh DB per test, IDs should be deterministic.
        # mainuser=1, user0=2, user1=3 ...
        followee_id = i + 2
        
        response = client.post(f"/follows/{followee_id}", headers=headers)
        
        if i < settings.MAX_FOLLOWS:
            assert response.status_code == 201, f"Failed at follow {i+1}"
        else:
            # The 101st follow (index 100) should fail
            assert response.status_code == 400
            assert "maximum" in response.json()["detail"]
