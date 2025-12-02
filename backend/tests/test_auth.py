def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={"email": "test@example.com", "username": "testuser", "password": "password123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data

def test_login_user(client):
    # Register first
    client.post(
        "/auth/register",
        json={"email": "test@example.com", "username": "testuser", "password": "password123"},
    )
    
    # Login
    response = client.post(
        "/auth/login",
        json={"username_or_email": "testuser", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
