import time

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

def test_feed_ordering(client):
    # User A follows User B
    token_a = get_auth_token(client, "a@example.com", "user_a")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
    token_b = get_auth_token(client, "b@example.com", "user_b")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    # Get User B's ID (should be 2)
    user_b_id = 2
    
    client.post(f"/follows/{user_b_id}", headers=headers_a)
    
    # User B posts 3 times
    client.post("/posts/", json={"content": "Post 1"}, headers=headers_b)
    time.sleep(0.1) # Ensure timestamp diff
    client.post("/posts/", json={"content": "Post 2"}, headers=headers_b)
    time.sleep(0.1)
    client.post("/posts/", json={"content": "Post 3"}, headers=headers_b)
    
    # User A checks feed
    response = client.get("/feed/", headers=headers_a)
    assert response.status_code == 200
    posts = response.json()
    
    assert len(posts) == 3
    assert posts[0]["content"] == "Post 3"
    assert posts[1]["content"] == "Post 2"
    assert posts[2]["content"] == "Post 1"
