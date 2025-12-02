import sys
import os
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add current directory to path so we can import app
sys.path.append(os.getcwd())

from app.db import Base, SQLALCHEMY_DATABASE_URL
from app.models.user import User
from app.models.connection import Connection
from app.models.connection_tag import ConnectionTag
from app.models.post import Post
from app.models.tag import Tag
from app.models.post_audience_tag import PostAudienceTag
from app.core.security import get_password_hash

# Setup DB connection
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

API_URL = "http://localhost:8000"

def setup_test_data():
    print("Setting up test data...")
    
    # Clean up existing test data
    db.query(PostAudienceTag).delete()
    db.query(ConnectionTag).delete()
    db.query(Post).delete()
    db.query(Tag).delete()
    db.query(Connection).delete()
    db.query(User).delete()
    db.commit()

    # Create main user
    main_user = User(
        email="tester@example.com",
        username="tester",
        hashed_password=get_password_hash("password123")
    )
    db.add(main_user)
    db.commit()
    db.refresh(main_user)
    print(f"Created main user: {main_user.id}")

    # Create 100 dummy users and connections
    connections = []
    for i in range(100):
        dummy = User(
            email=f"dummy_{i}@example.com",
            username=f"dummy_{i}",
            hashed_password=get_password_hash("password123")
        )
        db.add(dummy)
        db.commit() # Commit to get ID
        
        conn = Connection(
            requester_id=main_user.id,
            recipient_id=dummy.id,
            status="accepted"
        )
        connections.append(conn)
    
    db.add_all(connections)
    db.commit()
    print(f"Created 100 connections for user {main_user.id}")

    # Create one extra user for the failing request
    extra = User(
        email="extra@example.com",
        username="extra",
        hashed_password=get_password_hash("password123")
    )
    db.add(extra)
    db.commit()
    db.refresh(extra)
    print(f"Created extra user: {extra.id}")

    return main_user, extra

def login(username, password):
    response = requests.post(f"{API_URL}/auth/login", json={
        "username_or_email": username,
        "password": password
    })
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        sys.exit(1)
    return response.json()["access_token"]

def test_search(token):
    print("\nTesting Auth Search...")
    response = requests.get(
        f"{API_URL}/auth/users/search?q=dummy_0",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        results = response.json()
        if len(results) > 0 and results[0]["username"] == "dummy_0":
            print("✅ Auth search passed")
        else:
            print(f"❌ Auth search failed: Unexpected results {results}")
    else:
        print(f"❌ Auth search failed: {response.status_code} {response.text}")

def test_connection_limit(token, extra_user_id):
    print("\nTesting Connection Limit...")
    response = requests.post(
        f"{API_URL}/connections/request/{extra_user_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 400 and "maximum" in response.text:
        print("✅ Connection limit enforcement passed")
    else:
        print(f"❌ Connection limit enforcement failed: {response.status_code} {response.text}")

if __name__ == "__main__":
    try:
        main_user, extra_user = setup_test_data()
        token = login("tester", "password123")
        
        test_search(token)
        test_connection_limit(token, extra_user.id)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()
