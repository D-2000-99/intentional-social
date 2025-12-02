"""
Seed Script for Intentional Social
----------------------------------
Generates:
- ~15 users
- 3–7 posts per user
- limited follow graph

Requires:
pip install faker requests
"""

import random
import time
import requests
from faker import Faker

fake = Faker()

BASE_URL = "http://localhost:8000"

USER_COUNT = 15
MIN_POSTS = 3
MAX_POSTS = 7

# -------------------------------
# API Helpers
# -------------------------------

def register_user(email, username, password):
    return requests.post(f"{BASE_URL}/auth/register", json={
        "email": email,
        "username": username,
        "password": password,
    })

def login(email, password):
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "username_or_email": email,
        "password": password,
    })
    if res.status_code != 200:
        print("Login failed:", res.text)
        return None
    return res.json()["access_token"]

def create_post(token, text):
    return requests.post(
        f"{BASE_URL}/posts",
        json={"content": text},
        headers={"Authorization": f"Bearer {token}"}
    )

def follow(token, user_id):
    return requests.post(
        f"{BASE_URL}/follows/{user_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

def get_users():
    res = requests.get(f"{BASE_URL}/auth/users")  # adjust if needed
    return res.json()

# -------------------------------
# Seed Logic
# -------------------------------

def create_seed_users():
    users = []
    for _ in range(USER_COUNT):
        username = fake.user_name()[:12]
        email = fake.unique.email()
        password = "pass123"

        reg = register_user(email, username, password)

        if reg.status_code == 201:
            print(f"Created user: {username}")
            users.append({
                "email": email,
                "username": username,
                "password": password
            })
        elif reg.status_code == 400:
            print(f"User {username} already exists, proceeding...")
            users.append({
                "email": email,
                "username": username,
                "password": password
            })
        else:
            print(f"Failed to create {username}: {reg.text}")

    return users

def attach_tokens(users):
    enriched = []
    for u in users:
        token = login(u["email"], u["password"])
        if token:
            enriched.append({**u, "token": token})
        else:
            print("Token fetch failed for", u["username"])
    return enriched

def seed_posts(users):
    for u in users:
        post_count = random.randint(MIN_POSTS, MAX_POSTS)
        for _ in range(post_count):
            text = fake.sentence(nb_words=random.randint(6, 14))
            res = create_post(u["token"], text)
            if res.status_code == 201:
                print(f"[POST] {u['username']} → OK")
            else:
                print(f"[POST FAILED] {u['username']}:", res.text)
            time.sleep(0.1)  # slight realism delay

def seed_follows(users):
    # Build sparse follow graph
    # Avg ~4 following per user, <100 limit anyway
    for u in users:
        follow_choices = random.sample(users, k=random.randint(2, 5))
        for target in follow_choices:
            if target["email"] == u["email"]:
                continue
            res = follow(u["token"], target["id"])
            if res.status_code in (200, 201):
                print(f"[FOLLOW] {u['username']} -> {target['username']}")
            else:
                pass # duplicates / rejects normal
            time.sleep(0.05)


def enrich_with_user_ids(users):
    # Requires a user-list endpoint that returns:
    # [{"id": , "username": , ...}]
    # Adjust path if needed
    all_users = requests.get(f"{BASE_URL}/auth/users").json()

    user_map = {u["username"]: u["id"] for u in all_users}

    enriched = []
    for u in users:
        if u["username"] in user_map:
            enriched.append({**u, "id": user_map[u["username"]]})
        else:
            print("Missing DB user:", u["username"])
    return enriched


if __name__ == "__main__":
    print("\n🌱 SEEDING DATABASE...\n")

    created = create_seed_users()
    with_tokens = attach_tokens(created)

    # fetch DB IDs from API
    final_users = enrich_with_user_ids(with_tokens)

    print("\n📝 Creating posts...")
    seed_posts(final_users)

    print("\n🔗 Creating follows...")
    seed_follows(final_users)

    print("\n🎉 DONE! Inspect your feed using any user token.\n")
